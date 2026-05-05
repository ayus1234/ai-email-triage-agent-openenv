"""
Router Agent — Email routing and forwarding decisions.
"""

import json
import sys
import os
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from prompts.router_prompt import ROUTER_SYSTEM_PROMPT, ROUTER_FEW_SHOT


class RouterAgent:
    """
    Agent 3: Email Router
    
    Takes classification and response outputs from previous agents,
    decides on final routing (folder placement + forwarding).
    """

    def __init__(self, llm_client, model_name: str):
        self.client = llm_client
        self.model_name = model_name
        self.agent_name = "Router"

    async def route(self, email_id: str, sender: str, subject: str, body: str,
                    classification: dict, response: dict) -> dict:
        """
        Decide routing for an email based on classification and response.
        
        Args:
            email_id: The email identifier
            sender: Email sender address
            subject: Email subject line
            body: Email body content
            classification: Output from ClassifierAgent
            response: Output from ResponderAgent
            
        Returns:
            dict with keys: email_id, reasoning, routing
        """
        classification_summary = json.dumps({
            "category": classification.get("classification", {}).get("category", "unknown"),
            "confidence": classification.get("classification", {}).get("confidence", 0.5),
        })
        response_summary = json.dumps({
            "should_reply": response.get("response", {}).get("should_reply", False),
        })

        user_prompt = f"""Route this email:
ID: {email_id}
From: {sender}
Subject: {subject}
Body: {body}

Classification: {classification_summary}
Response: {response_summary}"""

        messages = [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            *ROUTER_FEW_SHOT,
            {"role": "user", "content": user_prompt}
        ]

        try:
            llm_response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1,
            )
            raw_response = llm_response.choices[0].message.content.strip()
            
            result = self._parse_response(raw_response, email_id, classification)
            result["_raw_response"] = raw_response
            result["_agent"] = self.agent_name
            return result
            
        except Exception as e:
            print(f"[RouterAgent] Error routing {email_id}: {e}", flush=True)
            return self._fallback_routing(email_id, classification)

    def _parse_response(self, raw: str, email_id: str, classification: dict) -> dict:
        """Parse LLM JSON response."""
        try:
            start = raw.find('{')
            end = raw.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
        except json.JSONDecodeError:
            pass
        
        return self._fallback_routing(email_id, classification)

    def _fallback_routing(self, email_id: str, classification: dict) -> dict:
        """Rule-based fallback routing when LLM fails."""
        category = classification.get("classification", {}).get("category", "unknown")
        
        routing_rules = {
            "spam": {
                "move_to_folder": "SPAM",
                "should_forward": False,
                "forward_to": None,
                "priority": "low",
            },
            "invoice": {
                "move_to_folder": "INBOX",
                "should_forward": True,
                "forward_to": "finance@company.com",
                "priority": "medium",
            },
            "support": {
                "move_to_folder": "INBOX",
                "should_forward": False,
                "forward_to": None,
                "priority": "high",
            },
            "internal": {
                "move_to_folder": "INBOX",
                "should_forward": False,
                "forward_to": None,
                "priority": "medium",
            },
            "urgent": {
                "move_to_folder": "IMPORTANT",
                "should_forward": True,
                "forward_to": "management@company.com",
                "priority": "critical",
            },
        }
        
        rule = routing_rules.get(category, routing_rules["internal"])
        
        return {
            "email_id": email_id,
            "reasoning": {
                "routing_logic": f"Rule-based routing for category '{category}'",
                "department_match": "Finance" if category == "invoice" else "General",
                "escalation_needed": category == "urgent",
                "forward_rationale": f"Category '{category}' matches routing rule" if rule["should_forward"] else "N/A"
            },
            "routing": {
                **rule,
                "confidence": 0.80,
            },
            "_agent": self.agent_name,
            "_fallback": True
        }
