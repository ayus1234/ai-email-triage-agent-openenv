---
title: Email Triage OpenEnv
emoji: 📧
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# Email Triage OpenEnv Environment

An RL environment that tests an AI agent's ability to act as an automated administrative assistant by managing an email inbox. The environment issues multiple tasks testing reading, moving, forwarding and replying to emails.

## Domain Motivation (Real-world Utility)
Triage and management of inboxes is an exceptionally common real-world task. Virtual assistants must deal with partial requests, contextually reply to customers (e.g. processing refunds), forward invoices to appropriate departments, and filter spam.

## Observation Space
`EmailObservation` contains:
- `system_message` (str): Feedback from the last action.
- `inbox_summary` (List[EmailSummary]): A list of all emails containing id, sender, subject, and current folder.
- `read_email_content` (str): Full text of the recently read email.
- `done` (bool): True if task complete.
- `reward` (float): Current score.

## Action Space
`EmailAction` contains:
- `action_type` (ActionType): READ, MOVE, REPLY, FORWARD or SUBMIT.
- `email_id` (str): ID of the target email.
- `target_folder` (str): Target folder for MOVE.
- `body` (str): Response body for REPLY.
- `to_address` (str): Address for FORWARD.

## Tasks and Grader
The environment has 3 tasks with increasing difficulty (easy, medium, hard).
1. **Easy**: Single spam email filtering.
2. **Medium**: Filtering plus dynamically replying to a refund request.
3. **Hard**: Filtering, replying, and forwarding an invoice.
The score is strictly graded (0.0 to 1.0) and provided upon the agent issuing `SUBMIT` action.

## Setup Instructions
```bash
# Build the environment
docker build -t email_triage-env:latest server/
# Ensure openenv interface is ready
openenv validate
# Run inference reproduction
python inference.py
```
## 👥 Team OpenAgents

Built as part of the OpenEnv Hackathon.

### Contributors:
- **Ayush Nathani** – Lead, core implementation  
- **Amrit Sugandh** – Team member  
- **Rajababu Kumar** – Team member