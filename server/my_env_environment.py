# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Email Triage Environment Implementation.
"""

import copy
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import ActionType, EmailAction, EmailObservation, EmailSummary
except (ImportError, ValueError):
    from models import ActionType, EmailAction, EmailObservation, EmailSummary

TASKS_DATA = {
    "easy": {
        "emails": [
            {"id": "e1", "sender": "boss@company.com", "subject": "Project update", "body": "Please send the latest report.", "folder": "INBOX"},
            {"id": "e2", "sender": "scam@spam.com", "subject": "You won a lottery!", "body": "Click here to claim $1M.", "folder": "INBOX"},
            {"id": "e3", "sender": "colleague@company.com", "subject": "Lunch?", "body": "Are we still on for lunch?", "folder": "INBOX"},
        ],
        "expected_state": {
            "e1": "INBOX",
            "e2": "SPAM",
            "e3": "INBOX"
        }
    },
    "medium": {
        "emails": [
            {"id": "e1", "sender": "scam@spam.com", "subject": "Cheap meds", "body": "Buy now.", "folder": "INBOX"},
            {"id": "e2", "sender": "customer@gmail.com", "subject": "Refund request", "body": "Hi, I would like a refund for order #123.", "folder": "INBOX"},
        ],
        "expected_state": {
            "e1": "SPAM",
            "e2": "INBOX"
        },
        "expected_replies": [
            {"email_id": "e2", "contains": ["refund"]}
        ]
    },
    "hard": {
        "emails": [
            {"id": "e1", "sender": "scam@spam.com", "subject": "Cheap meds", "body": "Buy now.", "folder": "INBOX"},
            {"id": "e2", "sender": "customer@gmail.com", "subject": "Refund request", "body": "Hi, I would like a refund for order #456.", "folder": "INBOX"},
            {"id": "e3", "sender": "vendor@outside.com", "subject": "Invoice #789", "body": "Attached is invoice #789 for $500.", "folder": "INBOX"},
        ],
        "expected_state": {
            "e1": "SPAM",
            "e2": "INBOX",
            "e3": "INBOX"
        },
        "expected_replies": [
            {"email_id": "e2", "contains": ["refund"]}
        ],
        "expected_forwards": [
            {"email_id": "e3", "to_address": "finance@company.com"}
        ]
    }
}

class MyEnvironment(Environment):
    """
    Email Triage Environment.
    The agent manages an inbox, processes emails, and executes actions.
    """
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self.task_name = "easy"
        self.emails = {}
        self.replies_sent = []
        self.forwards_sent = []
        self._reset_count = 0

    def reset(self, **kwargs) -> EmailObservation:
        self._state = State(episode_id=str(uuid4()), step_count=0)
        
        # Cycle through tasks if not specified
        task_names = ["easy", "medium", "hard"]
        self.task_name = kwargs.get("task_name", task_names[self._reset_count % 3])
        self._reset_count += 1
        
        if self.task_name not in TASKS_DATA:
            self.task_name = "easy"
            
        task_data = copy.deepcopy(TASKS_DATA[self.task_name])
        self.emails = {e["id"]: e for e in task_data["emails"]}
        self.replies_sent = []
        self.forwards_sent = []
        
        return self._get_observation("Environment reset. Task loaded: " + self.task_name, done=False, reward=0.0)

    def _get_observation(self, system_message: str, done: bool, reward: float, read_content: str = None) -> EmailObservation:
        summary = [
            EmailSummary(id=e["id"], sender=e["sender"], subject=e["subject"], folder=e["folder"])
            for e in self.emails.values()
        ]
        # In this implementation, reward and done are part of the Observation because the client structure expects it
        obs = EmailObservation(
            system_message=system_message,
            inbox_summary=summary,
            read_email_content=read_content
        )
        # Note: reward/done are actually handled by the server wrapper in some OpenEnv versions,
        # but here we ensure they are available however the protocol expects.
        return obs

    def step(self, action: EmailAction) -> EmailObservation:  # type: ignore[override]
        self._state.step_count += 1
        reward = 0.05  # Small step reward to encourage interaction
        done = False
        message = ""
        read_content = None

        if action.action_type == ActionType.READ:
            if action.email_id in self.emails:
                read_content = self.emails[action.email_id]["body"]
                message = f"Read email {action.email_id}"
                reward = 0.01
            else:
                message = "Error: Invalid email ID"
                reward = -0.01

        elif action.action_type == ActionType.MOVE:
            if action.email_id in self.emails and action.target_folder:
                self.emails[action.email_id]["folder"] = action.target_folder
                message = f"Moved email {action.email_id} to {action.target_folder}"
                reward = 0.05
            else:
                message = "Error: Invalid email ID or missing folder"
                reward = -0.01

        elif action.action_type == ActionType.REPLY:
            if action.email_id in self.emails and action.body:
                self.replies_sent.append({"email_id": action.email_id, "body": action.body})
                message = f"Replied to email {action.email_id}"
                reward = 0.05
            else:
                message = "Error: Invalid email ID or missing body"
                reward = -0.01
                
        elif action.action_type == ActionType.FORWARD:
            if action.email_id in self.emails and action.to_address:
                self.forwards_sent.append({"email_id": action.email_id, "to_address": action.to_address, "body": action.body or ""})
                message = f"Forwarded email {action.email_id} to {action.to_address}"
                reward = 0.05
            else:
                message = "Error: Invalid email ID or missing address"
                reward = -0.01

        elif action.action_type == ActionType.SUBMIT:
            done = True
            score = self.grade_task()
            reward = score
            message = f"Task completed with score {score}"

        # We set these on the observation object if it supports them, or the server will extract them
        obs = self._get_observation(message, done, reward, read_content)
        # Important: OpenEnv core expects reward/done to be returned or available on state
        # In many create_app versions, it expects a signature of Observation or tuple.
        return obs

    def grade_task(self) -> float:
        task_data = TASKS_DATA[self.task_name]
        total_checks = 0
        passed_checks = 0
        
        expected_state = task_data.get("expected_state", {})
        for eid, folder in expected_state.items():
            total_checks += 1
            if self.emails.get(eid, {}).get("folder") == folder:
                passed_checks += 1
                
        expected_replies = task_data.get("expected_replies", [])
        for req in expected_replies:
            total_checks += 1
            found = False
            for rep in self.replies_sent:
                if rep["email_id"] == req["email_id"]:
                    if any(t.lower() in rep["body"].lower() for t in req["contains"]):
                        found = True
                        break
            if found:
                passed_checks += 1
                
        expected_forwards = task_data.get("expected_forwards", [])
        for req in expected_forwards:
            total_checks += 1
            found = False
            for fwd in self.forwards_sent:
                if fwd["email_id"] == req["email_id"] and fwd["to_address"] == req["to_address"]:
                    found = True
                    break
            if found:
                passed_checks += 1
                
        if total_checks == 0:
            return 1.0
            
        return float(passed_checks) / float(total_checks)

    @property
    def state(self) -> State:
        return self._state
