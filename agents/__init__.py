"""
Multi-agent email triage system.

Architecture:
  Agent 1 (Classifier) → Agent 2 (Responder) → Agent 3 (Router)
  
Each agent is specialized with its own prompt and reasoning trace.
The Pipeline orchestrator manages the flow between agents.
"""

from .classifier import ClassifierAgent
from .responder import ResponderAgent
from .router import RouterAgent
from .pipeline import MultiAgentPipeline

__all__ = [
    "ClassifierAgent",
    "ResponderAgent",
    "RouterAgent",
    "MultiAgentPipeline",
]
