"""Prompt templates for the multi-agent email triage system."""

from .classifier_prompt import CLASSIFIER_SYSTEM_PROMPT, CLASSIFIER_FEW_SHOT
from .responder_prompt import RESPONDER_SYSTEM_PROMPT, RESPONDER_FEW_SHOT
from .router_prompt import ROUTER_SYSTEM_PROMPT, ROUTER_FEW_SHOT

__all__ = [
    "CLASSIFIER_SYSTEM_PROMPT", "CLASSIFIER_FEW_SHOT",
    "RESPONDER_SYSTEM_PROMPT", "RESPONDER_FEW_SHOT",
    "ROUTER_SYSTEM_PROMPT", "ROUTER_FEW_SHOT",
]
