"""
Analytics Store — In-memory metrics collection for the dashboard.
No external database required.
"""

import time
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class EmailMetric:
    """Metrics for a single processed email."""
    email_id: str
    task_name: str
    category: str
    was_spam: bool
    reply_sent: bool
    forwarded: bool
    forward_to: Optional[str]
    classification_confidence: float
    response_confidence: float
    routing_confidence: float
    processing_time_ms: float
    reward: float
    timestamp: float


class AnalyticsStore:
    """
    In-memory analytics for email triage metrics.
    Provides aggregated data for dashboard charts.
    """

    def __init__(self):
        self.metrics: List[EmailMetric] = []
        self.task_scores: Dict[str, List[float]] = defaultdict(list)
        self.episode_count = 0
        self.total_emails = 0
        self.is_running = False
        self._start_time = time.time()

    def record_email(self, metric: EmailMetric):
        """Record metrics for a processed email."""
        self.metrics.append(metric)
        self.total_emails += 1

    def record_task_score(self, task_name: str, score: float):
        """Record the final score for a task."""
        self.task_scores[task_name].append(score)
        self.episode_count += 1

    def get_summary(self) -> dict:
        """Get aggregated analytics summary."""
        if not self.metrics:
            return self._empty_summary()

        total = len(self.metrics)
        spam_count = sum(1 for m in self.metrics if m.was_spam)
        replies = sum(1 for m in self.metrics if m.reply_sent)
        forwards = sum(1 for m in self.metrics if m.forwarded)
        avg_conf = sum(m.classification_confidence for m in self.metrics) / total
        avg_reward = sum(m.reward for m in self.metrics) / total if self.metrics else 0
        avg_time = sum(m.processing_time_ms for m in self.metrics) / total

        # Category distribution
        categories = defaultdict(int)
        for m in self.metrics:
            categories[m.category] += 1

        # Task score averages
        task_avgs = {}
        for task, scores in self.task_scores.items():
            task_avgs[task] = sum(scores) / len(scores) if scores else 0

        # Confidence distribution (buckets)
        conf_buckets = {"0.0-0.5": 0, "0.5-0.7": 0, "0.7-0.9": 0, "0.9-1.0": 0}
        for m in self.metrics:
            c = m.classification_confidence
            if c < 0.5:
                conf_buckets["0.0-0.5"] += 1
            elif c < 0.7:
                conf_buckets["0.5-0.7"] += 1
            elif c < 0.9:
                conf_buckets["0.7-0.9"] += 1
            else:
                conf_buckets["0.9-1.0"] += 1

        return {
            "overview": {
                "total_emails": total,
                "total_episodes": self.episode_count,
                "is_running": self.is_running,
                "spam_detected": spam_count,
                "replies_sent": replies,
                "forwards_sent": forwards,
                "uptime_seconds": round(time.time() - self._start_time, 1),
            },
            "performance": {
                "avg_classification_confidence": round(avg_conf, 3),
                "avg_reward": round(avg_reward, 3),
                "avg_processing_time_ms": round(avg_time, 1),
                "task_scores": task_avgs,
            },
            "distribution": {
                "categories": dict(categories),
                "confidence_buckets": conf_buckets,
            },
            "recent": [
                {
                    "email_id": m.email_id,
                    "category": m.category,
                    "confidence": m.classification_confidence,
                    "reward": m.reward,
                    "time_ms": round(m.processing_time_ms, 1),
                }
                for m in self.metrics[-10:]  # Last 10
            ],
        }

    def _empty_summary(self) -> dict:
        return {
            "overview": {
                "total_emails": 0, "total_episodes": 0,
                "is_running": self.is_running,
                "spam_detected": 0, "replies_sent": 0, "forwards_sent": 0,
                "uptime_seconds": round(time.time() - self._start_time, 1),
            },
            "performance": {
                "avg_classification_confidence": 0,
                "avg_reward": 0, "avg_processing_time_ms": 0,
                "task_scores": {},
            },
            "distribution": {"categories": {}, "confidence_buckets": {}},
            "recent": [],
        }


# Global singleton
analytics_store = AnalyticsStore()
