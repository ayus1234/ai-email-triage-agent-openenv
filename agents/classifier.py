"""
Classifier Agent — Specialized email classification with structured reasoning.
"""

import json
import sys
import os
from typing import Optional

# Handle imports for both package and standalone execution
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from prompts.classifier_prompt import CLASSIFIER_SYSTEM_PROMPT, CLASSIFIER_FEW_SHOT


class ClassifierAgent:
    """
    Agent 1: Email Classifier
    
    Analyzes email content and produces structured classification with
    reasoning trace showing the AI's decision-making process.
    """

    def __init__(self, llm_client, model_name: str, fallback_client=None, fallback_model_name=None):
        self.client = llm_client
        self.model_name = model_name
        self.fallback_client = fallback_client
        self.fallback_model_name = fallback_model_name
        self.agent_name = "Classifier"

    async def classify(self, email_id: str, sender: str, subject: str, body: str) -> dict:
        """
        Classify a single email and return structured reasoning + classification.
        
        Returns:
            dict with keys: email_id, reasoning, classification
        """
        user_prompt = f"""Classify this email:
ID: {email_id}
From: {sender}
Subject: {subject}
Body: {body}"""

        messages = [
            {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
            *CLASSIFIER_FEW_SHOT,
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1,
            )
            raw_response = response.choices[0].message.content.strip()
            
            # Parse the JSON response
            result = self._parse_response(raw_response, email_id)
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
                        temperature=0.1,
                    )
                    raw_response = response.choices[0].message.content.strip()
                    result = self._parse_response(raw_response, email_id)
                    result["_raw_response"] = raw_response
                    result["_agent"] = f"{self.agent_name} (Groq Fallback)"
                    return result
                except Exception as e2:
                    print(f"[{self.agent_name}] Fallback LLM also failed: {e2}", flush=True)

            print(f"[{self.agent_name}] Using rule-based fallback.", flush=True)
            return self._fallback_classification(email_id, sender, subject, body)

    def _parse_response(self, raw: str, email_id: str) -> dict:
        """Parse LLM JSON response, with fallback for malformed output."""
        try:
            # Try to extract JSON from the response
            start = raw.find('{')
            end = raw.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
        except json.JSONDecodeError:
            pass
        
        return self._fallback_classification(email_id, "", "", "")

    def _fallback_classification(self, email_id: str, sender: str, subject: str, body: str) -> dict:
        """Rule-based fallback when LLM fails."""
        # Simple heuristic-based classification
        spam_keywords = ["spam", "lottery", "winner", "click here", "cheap", "buy now", "free", "act now", "limited offer"]
        combined = f"{sender} {subject} {body}".lower()
        
        is_spam = any(kw in combined for kw in spam_keywords) or "spam" in sender.lower()
        
        if is_spam:
            category = "spam"
            folder = "SPAM"
            confidence = 0.85
        elif any(kw in combined for kw in ["refund", "return", "complaint", "issue", "problem", "help"]):
            category = "support"
            folder = "INBOX"
            confidence = 0.80
        elif any(kw in combined for kw in ["invoice", "payment", "billing", "due"]):
            category = "invoice"
            folder = "INBOX"
            confidence = 0.82
        else:
            category = "internal"
            folder = "INBOX"
            confidence = 0.70

        return {
            "email_id": email_id,
            "reasoning": {
                "content_analysis": f"Fallback rule-based analysis of '{subject}'",
                "sender_trust": "suspicious" if is_spam else "trusted",
                "spam_indicators": [kw for kw in spam_keywords if kw in combined] if is_spam else [],
                "intent": "spam" if is_spam else "legitimate communication",
                "urgency": "low" if is_spam else "medium",
                "sentiment": "neutral"
            },
            "classification": {
                "category": category,
                "confidence": confidence,
                "suggested_folder": folder
            },
            "_agent": self.agent_name,
            "_fallback": True
        }
