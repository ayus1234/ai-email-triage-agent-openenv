"""
Reasoning Engine — Wraps LLM calls with structured chain-of-thought output.
Collects and stores reasoning traces for dashboard display.
"""

import json
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class ReasoningStep:
    """A single reasoning step in the chain-of-thought."""
    step_number: int
    agent_name: str
    email_id: str
    reasoning: dict
    action_taken: str
    confidence: float
    duration_ms: float
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return {
            "step": self.step_number,
            "agent": self.agent_name,
            "email_id": self.email_id,
            "reasoning": self.reasoning,
            "action": self.action_taken,
            "confidence": self.confidence,
            "duration_ms": round(self.duration_ms, 2),
            "timestamp": self.timestamp,
        }


@dataclass
class EpisodeTrace:
    """Complete reasoning trace for one episode (task run)."""
    episode_id: str
    task_name: str
    steps: List[ReasoningStep] = field(default_factory=list)
    total_reward: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0
    emails_processed: int = 0

    def to_dict(self) -> dict:
        return {
            "episode_id": self.episode_id,
            "task_name": self.task_name,
            "steps": [s.to_dict() for s in self.steps],
            "total_reward": self.total_reward,
            "duration_ms": round((self.end_time - self.start_time) * 1000, 2),
            "emails_processed": self.emails_processed,
        }


class ReasoningEngine:
    """
    Centralized reasoning trace collector.
    
    Captures chain-of-thought from all agents across all episodes,
    making the AI's decision-making process fully transparent.
    """

    def __init__(self):
        self.episodes: Dict[str, EpisodeTrace] = {}
        self._current_episode: Optional[str] = None
        self._step_counter = 0

    def start_episode(self, episode_id: str, task_name: str):
        """Begin tracking a new episode."""
        self._current_episode = episode_id
        self._step_counter = 0
        self.episodes[episode_id] = EpisodeTrace(
            episode_id=episode_id,
            task_name=task_name,
            start_time=time.time(),
        )

    def record_step(self, agent_name: str, email_id: str, reasoning: dict,
                    action: str, confidence: float, duration_ms: float):
        """Record a reasoning step from an agent."""
        if not self._current_episode:
            return
        
        self._step_counter += 1
        step = ReasoningStep(
            step_number=self._step_counter,
            agent_name=agent_name,
            email_id=email_id,
            reasoning=reasoning,
            action_taken=action,
            confidence=confidence,
            duration_ms=duration_ms,
            timestamp=time.time(),
        )
        self.episodes[self._current_episode].steps.append(step)

    def end_episode(self, reward: float, emails_processed: int):
        """End the current episode with final metrics."""
        if self._current_episode and self._current_episode in self.episodes:
            ep = self.episodes[self._current_episode]
            ep.total_reward = reward
            ep.end_time = time.time()
            ep.emails_processed = emails_processed
        self._current_episode = None

    def get_episode_trace(self, episode_id: str) -> Optional[dict]:
        """Get the full reasoning trace for an episode."""
        if episode_id in self.episodes:
            return self.episodes[episode_id].to_dict()
        return None

    def get_all_traces(self) -> List[dict]:
        """Get all episode traces."""
        return [ep.to_dict() for ep in self.episodes.values()]

    def get_latest_trace(self) -> Optional[dict]:
        """Get the most recent episode trace."""
        if not self.episodes:
            return None
        latest_id = list(self.episodes.keys())[-1]
        return self.episodes[latest_id].to_dict()


# Global singleton instance
reasoning_engine = ReasoningEngine()
