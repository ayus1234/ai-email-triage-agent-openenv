# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Data models for the Email Triage Environment.
"""

from enum import Enum
from typing import List, Optional

from openenv.core.env_server.types import Action, Observation
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    READ = "READ"
    MOVE = "MOVE"
    REPLY = "REPLY"
    FORWARD = "FORWARD"
    SUBMIT = "SUBMIT"


class EmailAction(Action):
    """Action for the Email Triage environment."""

    action_type: ActionType = Field(..., description="Type of action: READ, MOVE, REPLY, FORWARD, SUBMIT")
    email_id: Optional[str] = Field(None, description="ID of the email to operate on")
    target_folder: Optional[str] = Field(None, description="Folder to move the email to (e.g., SPAM, ARCHIVE)")
    body: Optional[str] = Field(None, description="Body text for reply or forward")
    to_address: Optional[str] = Field(None, description="Email address to forward to")


class EmailSummary(BaseModel):
    id: str = Field(..., description="Email ID")
    sender: str = Field(..., description="Sender address")
    subject: str = Field(..., description="Email subject")
    folder: str = Field(..., description="Current folder (INBOX, SPAM, ARCHIVE)")


class EmailObservation(Observation):
    """Observation from the Email Triage environment."""

    system_message: str = Field(..., description="Feedback from the last action")
    inbox_summary: List[EmailSummary] = Field(..., description="List of emails and their current folders")
    read_email_content: Optional[str] = Field(None, description="Content of the email if READ action was successful")
