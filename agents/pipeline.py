"""
Multi-Agent Pipeline Orchestrator — Sequential agent processing with shared context.

Flow: Classifier → Responder → Router
Each agent receives the output of previous agents as additional context.
"""

import json
import time
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class AgentStepTrace:
    """Record of a single agent's processing for one email."""
    agent_name: str
    email_id: str
    reasoning: dict
    output: dict
    duration_ms: float
    confidence: float
    is_fallback: bool = False


@dataclass
class PipelineResult:
    """Complete result of processing one email through the multi-agent pipeline."""
    email_id: str
    classification: dict
    response: dict
    routing: dict
    traces: List[AgentStepTrace] = field(default_factory=list)
    total_duration_ms: float = 0.0
    
    # Computed action decisions
    action_move_to: Optional[str] = None
    action_reply_body: Optional[str] = None
    action_forward_to: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "email_id": self.email_id,
            "classification": self.classification,
            "response": self.response,
            "routing": self.routing,
            "traces": [
                {
                    "agent": t.agent_name,
                    "email_id": t.email_id,
                    "reasoning": t.reasoning,
                    "confidence": t.confidence,
                    "duration_ms": t.duration_ms,
                    "is_fallback": t.is_fallback,
                }
                for t in self.traces
            ],
            "total_duration_ms": self.total_duration_ms,
            "actions": {
                "move_to": self.action_move_to,
                "reply_body": self.action_reply_body,
                "forward_to": self.action_forward_to,
            }
        }


class MultiAgentPipeline:
    """
    Orchestrates the multi-agent email triage pipeline.
    
    Sequential processing: Classifier → Responder → Router
    
    Each agent produces structured reasoning that gets passed to the next,
    creating a visible chain-of-thought across the entire pipeline.
    """

    def __init__(self, llm_client, model_name: str, fallback_client=None, fallback_model_name=None):
        from agents.classifier import ClassifierAgent
        from agents.responder import ResponderAgent
        from agents.router import RouterAgent

        self.classifier = ClassifierAgent(llm_client, model_name, fallback_client, fallback_model_name)
        self.responder = ResponderAgent(llm_client, model_name, fallback_client, fallback_model_name)
        self.router = RouterAgent(llm_client, model_name, fallback_client, fallback_model_name)
        self.model_name = model_name
        
        # Store all pipeline results for analytics
        self.history: List[PipelineResult] = []

    async def process_email(self, email_id: str, sender: str, subject: str, body: str) -> PipelineResult:
        """
        Process a single email through the full multi-agent pipeline.
        
        Returns a PipelineResult with all agent traces and final action decisions.
        """
        pipeline_start = time.time()
        traces = []

        # ═══════════════════════════════════════════
        # STAGE 1: Classification
        # ═══════════════════════════════════════════
        print(f"\n  🔍 [Classifier] Analyzing email {email_id}...", flush=True)
        t0 = time.time()
        classification = await self.classifier.classify(email_id, sender, subject, body)
        t1 = time.time()
        
        traces.append(AgentStepTrace(
            agent_name="Classifier",
            email_id=email_id,
            reasoning=classification.get("reasoning", {}),
            output=classification.get("classification", {}),
            duration_ms=(t1 - t0) * 1000,
            confidence=classification.get("classification", {}).get("confidence", 0.5),
            is_fallback=classification.get("_fallback", False),
        ))
        
        category = classification.get("classification", {}).get("category", "unknown")
        confidence = classification.get("classification", {}).get("confidence", 0.0)
        print(f"  ✅ [Classifier] → {category} (confidence: {confidence:.2f})", flush=True)

        # ═══════════════════════════════════════════
        # STAGE 2: Response Generation
        # ═══════════════════════════════════════════
        print(f"  💬 [Responder] Generating response for {email_id}...", flush=True)
        t0 = time.time()
        response = await self.responder.generate_response(
            email_id, sender, subject, body, classification
        )
        t1 = time.time()
        
        traces.append(AgentStepTrace(
            agent_name="Responder",
            email_id=email_id,
            reasoning=response.get("reasoning", {}),
            output=response.get("response", {}),
            duration_ms=(t1 - t0) * 1000,
            confidence=response.get("response", {}).get("confidence", 0.5),
            is_fallback=response.get("_fallback", False),
        ))
        
        should_reply = response.get("response", {}).get("should_reply", False)
        print(f"  ✅ [Responder] → reply={'yes' if should_reply else 'no'}", flush=True)

        # ═══════════════════════════════════════════
        # STAGE 3: Routing
        # ═══════════════════════════════════════════
        print(f"  📤 [Router] Deciding routing for {email_id}...", flush=True)
        t0 = time.time()
        routing = await self.router.route(
            email_id, sender, subject, body, classification, response
        )
        t1 = time.time()
        
        traces.append(AgentStepTrace(
            agent_name="Router",
            email_id=email_id,
            reasoning=routing.get("reasoning", {}),
            output=routing.get("routing", {}),
            duration_ms=(t1 - t0) * 1000,
            confidence=routing.get("routing", {}).get("confidence", 0.5),
            is_fallback=routing.get("_fallback", False),
        ))
        
        folder = routing.get("routing", {}).get("move_to_folder", "INBOX")
        forward = routing.get("routing", {}).get("forward_to")
        print(f"  ✅ [Router] → folder={folder}, forward={forward or 'none'}", flush=True)

        # ═══════════════════════════════════════════
        # COMPILE RESULT
        # ═══════════════════════════════════════════
        pipeline_end = time.time()
        
        result = PipelineResult(
            email_id=email_id,
            classification=classification,
            response=response,
            routing=routing,
            traces=traces,
            total_duration_ms=(pipeline_end - pipeline_start) * 1000,
            action_move_to=folder,
            action_reply_body=response.get("response", {}).get("reply_body") if should_reply else None,
            action_forward_to=forward if routing.get("routing", {}).get("should_forward") else None,
        )
        
        self.history.append(result)
        return result

    async def process_inbox(self, emails: List[dict]) -> List[PipelineResult]:
        """
        Process all emails in an inbox through the pipeline.
        
        Args:
            emails: List of dicts with keys: id, sender, subject, body
            
        Returns:
            List of PipelineResult objects
        """
        results = []
        for email in emails:
            print(f"\n{'='*60}", flush=True)
            print(f"📧 Processing: {email['subject']} (from: {email['sender']})", flush=True)
            print(f"{'='*60}", flush=True)
            
            result = await self.process_email(
                email_id=email["id"],
                sender=email["sender"],
                subject=email["subject"],
                body=email.get("body", ""),
            )
            results.append(result)
        
        return results

    def get_reasoning_summary(self) -> List[dict]:
        """Get a summary of all reasoning traces for display in the dashboard."""
        return [r.to_dict() for r in self.history]

    def clear_history(self):
        """Clear pipeline history."""
        self.history.clear()
