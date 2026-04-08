# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Client for the My Env Environment.
"""

from typing import Any, Dict
from openenv.core.env_client import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

try:
    from .models import EmailAction, EmailObservation, EmailSummary
except (ImportError, ValueError):
    try:
        from models import EmailAction, EmailObservation, EmailSummary
    except ImportError:
        import sys
        import os
        sys.path.append(os.getcwd())
        from models import EmailAction, EmailObservation, EmailSummary


class MyEnv(
    EnvClient[EmailAction, EmailObservation, State],
):
    """
    Client for the Email Triage environment.
    """

    def __init__(self, url: str):
        super().__init__(
            base_url=url,
        )

    def _step_payload(self, action: EmailAction) -> Dict[str, Any]:
        """Convert an EmailAction object to JSON."""
        return action.model_dump()

    def _parse_result(self, payload: Dict[str, Any]) -> StepResult[EmailObservation]:
        """Convert a JSON response to StepResult[EmailObservation]."""
        # The payload from the server's /step or WebSocket usually looks like:
        # {"observation": {...}, "reward": 0.0, "done": false}
        observation_data = payload.get("observation", {})
        observation = EmailObservation.model_validate(observation_data)
        
        return StepResult(
            observation=observation,
            reward=float(payload.get("reward", 0.0)),
            done=bool(payload.get("done", False)),
        )

    def _parse_state(self, payload: Dict[str, Any]) -> State:
        """Convert a JSON response to a State object."""
        return State.model_validate(payload)
