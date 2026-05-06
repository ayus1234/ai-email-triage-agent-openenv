"""
Responder Agent — Contextual reply generation with tone adaptation.
"""

import json
import sys
import os
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from prompts.responder_prompt import RESPONDER_SYSTEM_PROMPT, RESPONDER_FEW_SHOT


class ResponderAgent:
    """
    Agent 2: Email Responder
    
    Takes classification output from the Classifier Agent and generates
    contextual, tone-appropriate replies with reasoning trace.
    """

    def __init__(self, llm_client, model_name: str, fallback_client=None, fallback_model_name=None):
        self.client = llm_client
        self.model_name = model_name
        self.fallback_client = fallback_client
        self.fallback_model_name = fallback_model_name
        self.agent_name = "Responder"

    async def generate_response(self, email_id: str, sender: str, subject: str,
                                 body: str, classification: dict) -> dict:
        """
        Generate a reply for an email based on its classification.
        
        Args:
            email_id: The email identifier
            sender: Email sender address
            subject: Email subject line
            body: Email body content
            classification: Output from ClassifierAgent
            
        Returns:
            dict with keys: email_id, reasoning, response
        """
        classification_summary = json.dumps({
            "category": classification.get("classification", {}).get("category", "unknown"),
            "confidence": classification.get("classification", {}).get("confidence", 0.5),
            "sentiment": classification.get("reasoning", {}).get("sentiment", "neutral"),
            "urgency": classification.get("reasoning", {}).get("urgency", "medium"),
        })

        user_prompt = f"""Generate reply for this email:
ID: {email_id}
From: {sender}
Subject: {subject}
Body: {body}

Classification: {classification_summary}"""

        messages = [
            {"role": "system", "content": RESPONDER_SYSTEM_PROMPT},
            *RESPONDER_FEW_SHOT,
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.3,
            )
            raw_response = response.choices[0].message.content.strip()
            
            result = self._parse_response(raw_response, email_id, classification)
            result["_raw_response"] = raw_response
            result["_agent"] = self.agent_name
            return result
            
        except Exception as e:
            print(f"[{self.agent_name}] LLM Error: {e}", flush=True)
            if self.fallback_client:
                print(f"[{self.agent_name}] Retrying with fallback Groq API...", flush=True)
                try:
                    response = await self.fallback_client.chat.completions.create(
                        model=self.fallback_model_name,
                        messages=messages,
                        temperature=0.3,
                    )
                    raw_response = response.choices[0].message.content.strip()
                    result = self._parse_response(raw_response, email_id, classification)
                    result["_raw_response"] = raw_response
                    result["_agent"] = f"{self.agent_name} (Groq Fallback)"
                    return result
                except Exception as e2:
                    print(f"[{self.agent_name}] Fallback LLM also failed: {e2}", flush=True)

            print(f"[{self.agent_name}] Using rule-based fallback.", flush=True)
            return self._fallback_response(email_id, sender, subject, body, classification)

    def _parse_response(self, raw: str, email_id: str, classification: dict) -> dict:
        """Parse LLM JSON response."""
        try:
            start = raw.find('{')
            end = raw.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
        except json.JSONDecodeError:
            pass
        
        return self._fallback_response(email_id, "", "", "", classification)

    def _fallback_response(self, email_id: str, sender: str, subject: str,
                           body: str, classification: dict) -> dict:
        """Template-based fallback when LLM fails."""
        category = classification.get("classification", {}).get("category", "unknown")
        
        if category == "spam":
            return {
                "email_id": email_id,
                "reasoning": {
                    "response_needed": False,
                    "response_type": "none",
                    "tone": "formal",
                    "key_points_to_address": [],
                    "template_used": "none"
                },
                "response": {
                    "should_reply": False,
                    "reply_body": None,
                    "confidence": 0.95
                },
                "_agent": self.agent_name,
                "_fallback": True
            }
        elif category == "support":
            reply = (
                f"Dear Customer,\n\n"
                f"Thank you for reaching out regarding your concern. "
                f"We have received your request and our team is reviewing it.\n\n"
                f"We will process your request promptly and get back to you "
                f"within 1-2 business days.\n\n"
                f"Best regards,\nCustomer Support Team"
            )
            return {
                "email_id": email_id,
                "reasoning": {
                    "response_needed": True,
                    "response_type": "acknowledgment",
                    "tone": "empathetic",
                    "key_points_to_address": ["acknowledge issue", "provide timeline"],
                    "template_used": "general_reply"
                },
                "response": {
                    "should_reply": True,
                    "reply_body": reply,
                    "confidence": 0.75
                },
                "_agent": self.agent_name,
                "_fallback": True
            }
        else:
            return {
                "email_id": email_id,
                "reasoning": {
                    "response_needed": False,
                    "response_type": "none",
                    "tone": "formal",
                    "key_points_to_address": [],
                    "template_used": "none"
                },
                "response": {
                    "should_reply": False,
                    "reply_body": None,
                    "confidence": 0.70
                },
                "_agent": self.agent_name,
                "_fallback": True
            }
