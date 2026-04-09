---
title: Email Triage OpenEnv
emoji: 📧
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# 📧 Email Triage AI Environment (OpenEnv)

> 🚀 A real-world simulation where an AI agent learns to act as an **autonomous email assistant** — reading, classifying, replying, and routing emails intelligently.

---

## 🌟 Overview

Modern inboxes are chaotic.

From spam filtering to handling refunds and forwarding invoices — email management is repetitive, time-consuming, and error-prone.

This project creates a **reinforcement learning environment** that trains and evaluates AI agents to handle these workflows **end-to-end**, just like a human assistant.

---

## 🎯 Problem Statement

Organizations deal with thousands of emails daily:

- ❌ Manual sorting wastes time  
- ❌ Incorrect routing causes delays  
- ❌ Poor responses affect user experience  

👉 **Goal:** Build an AI agent that can autonomously manage an inbox with accuracy and reasoning.

---

## 💡 Solution

We designed a structured OpenEnv environment where an agent must:

- 📖 Understand email intent  
- 🗂 Classify messages correctly  
- 💬 Generate contextual replies  
- 📤 Route emails to appropriate recipients  
- ✅ Submit final decisions for evaluation  

---

## 🧠 Agent Capabilities

The agent operates like a real assistant:

| Capability | Description |
|----------|------------|
| 📖 Read | Understand email content |
| 🗂 Classify | Identify spam vs important |
| 💬 Respond | Generate meaningful replies |
| 📤 Forward | Route emails correctly |
| ✅ Submit | Finalize task for scoring |

---

## ⚙️ Environment Design

### 📥 Observation Space (`EmailObservation`)
- `system_message` → Feedback from last action  
- `inbox_summary` → List of emails (id, sender, subject, folder)  
- `read_email_content` → Full email content  
- `done` → Task completion flag  
- `reward` → Current evaluation score  

---

### 🎯 Action Space (`EmailAction`)
- `READ` → Open an email  
- `MOVE` → Move email to folder  
- `REPLY` → Respond to sender  
- `FORWARD` → Send to another address  
- `SUBMIT` → Final evaluation trigger  

---

## 🧩 Task Design (Progressive Difficulty)

### 🟢 Easy — Spam Filtering
- Identify and move spam email  

---

### 🟡 Medium — Customer Support
- Filter emails  
- Reply to refund request  

---

### 🔴 Hard — Multi-step Workflow
- Filter spam  
- Respond to customer  
- Forward invoice to finance  

---

## 🎯 Reward System

- Scores strictly within **(0, 1)**  
- Final score assigned only on **`SUBMIT`**  
- Based on:
  - ✔ Correct classification  
  - ✔ Accurate responses  
  - ✔ Proper routing  

---

## 🔄 Example Workflow

1. **READ** email  
2. → Understand intent  
3. → **MOVE** (spam / important)  
4. → **REPLY** (if needed)  
5. → **FORWARD** (if required)  
6. → **SUBMIT** for final grading  

---

## 🧪 Playground Interaction

You can test the agent via the OpenEnv interface:

### Example Steps:
1. Click **Reset**
2. Perform actions:
   - READ → inspect email  
   - MOVE → classify  
   - REPLY / FORWARD → act  
3. Click **SUBMIT**

---

## 🛠️ Setup & Run

```bash
# Build environment
docker build -t email_triage-env:latest server/

# Validate OpenEnv setup
openenv validate

# Run agent
python inference.py
```

### 🏗️ Architecture Overview
User Input / Task  
&nbsp;&nbsp;&nbsp;&nbsp;↓  
OpenEnv Environment  
&nbsp;&nbsp;&nbsp;&nbsp;↓  
LLM Agent (Decision Making)  
&nbsp;&nbsp;&nbsp;&nbsp;↓  
Actions (READ / MOVE / REPLY / FORWARD)  
&nbsp;&nbsp;&nbsp;&nbsp;↓  
SUBMIT → Grader → Reward Score  

---

## 🔥 Key Highlights
- 🧠 Real-world inspired environment  
- ⚙️ Multi-step reasoning tasks  
- 🎯 Robust and consistent reward system  
- 🤖 Designed for LLM-based agents  
- 🔍 Clear evaluation pipeline  
- 🚀 Scalable for future automation use cases  

---

## 🌍 Real-World Applications
- 📧 Automated email assistants  
- 🛎 Customer support automation  
- 🏢 Enterprise workflow management  
- 💼 Finance & invoice routing systems  

---

## 👥 Team OpenAgents

Built for the Meta PyTorch Hackathon x Scaler School of Technology 🚀

**Contributors:**
- **Ayush Nathani** – Lead, core implementation  
- **Amrit Sugandh** – Team member  
- **Rajababu Kumar** – Team member  

---

## 🏁 Final Note

This project demonstrates how AI agents can move beyond simple Q&A and execute real-world workflows autonomously.

👉 From understanding intent → to taking action → to completing tasks —
this is a step toward truly agentic AI systems.