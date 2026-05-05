"""
Email Triage Inference — Multi-Agent Pipeline with Reasoning Traces.

Replaces the single-agent approach with a Classifier → Responder → Router pipeline.
Each agent produces visible reasoning traces stored in the analytics dashboard.
"""

import os
import sys
import json
import asyncio
import time

from typing import List, Optional
from openai import AsyncOpenAI
import httpx

from client import MyEnv
from models import EmailAction, ActionType
from reasoning_engine import reasoning_engine
from analytics_store import analytics_store, EmailMetric
from agents.pipeline import MultiAgentPipeline

# Use environment variable for server URL if available, fallback to localhost:7860
ENV_URL = os.environ.get("ENV_URL", "http://localhost:7860")

BENCHMARK = "email_triage"

def log_start(task: str, env: str, model: str):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str] = None):
    print(f"[STEP] step={step} action={action} reward={reward} done={done} error={error}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]):
    print(f"[END] success={success} steps={steps} score={score} rewards={rewards}", flush=True)


async def wait_for_server(url: str, timeout: int = 30):
    start_time = time.time()
    async with httpx.AsyncClient() as client:
        while time.time() - start_time < timeout:
            try:
                response = await client.get(f"{url}/health", timeout=1.0)
                if response.status_code == 200:
                    return True
            except (httpx.ConnectError, httpx.TimeoutException):
                pass
            await asyncio.sleep(1.0)
    return False


async def run_task(task_name: str, client: AsyncOpenAI, url: str, model_name: str, fallback_client: Optional[AsyncOpenAI] = None, fallback_model_name: Optional[str] = None):
    log_start(task=task_name, env=BENCHMARK, model=model_name)
    
    env = MyEnv(url)
    rewards = []
    steps_taken = 0
    score = 0.01
    success = False
    done = False
    
    # Initialize the multi-agent pipeline
    pipeline = MultiAgentPipeline(client, model_name, fallback_client, fallback_model_name)
    
    try:
        result = await env.reset(task_name=task_name)
        
        # Start reasoning trace for this episode
        episode_id = f"{task_name}_{int(time.time())}"
        reasoning_engine.start_episode(episode_id, task_name)
        
        print(f"\n{'='*70}", flush=True)
        print(f"🚀 TASK: {task_name.upper()} — Multi-Agent Pipeline Active", flush=True)
        print(f"{'='*70}", flush=True)
        
        # Phase 1: Read all emails to get their content
        emails_data = []
        for email_summary in result.observation.inbox_summary:
            steps_taken += 1
            read_action = EmailAction(action_type=ActionType.READ, email_id=email_summary.id)
            result = await env.step(read_action)
            
            reward = result.reward if result.reward is not None else 0.01
            reward = max(0.001, min(reward, 0.999))
            rewards.append(reward)
            
            log_step(step=steps_taken, action=f"READ {email_summary.id}", reward=reward, done=result.done)
            
            emails_data.append({
                "id": email_summary.id,
                "sender": email_summary.sender,
                "subject": email_summary.subject,
                "body": result.observation.read_email_content or "",
            })
            
            if result.done:
                done = True
                break
        
        if not done:
            # Phase 2: Process all emails through multi-agent pipeline
            pipeline_results = await pipeline.process_inbox(emails_data)
            
            # Phase 3: Execute actions based on pipeline decisions
            for pr in pipeline_results:
                # Record reasoning traces
                for trace in pr.traces:
                    reasoning_engine.record_step(
                        agent_name=trace.agent_name,
                        email_id=trace.email_id,
                        reasoning=trace.reasoning,
                        action=str(trace.output),
                        confidence=trace.confidence,
                        duration_ms=trace.duration_ms,
                    )
                
                # Execute MOVE action
                if pr.action_move_to:
                    steps_taken += 1
                    move_action = EmailAction(
                        action_type=ActionType.MOVE,
                        email_id=pr.email_id,
                        target_folder=pr.action_move_to
                    )
                    result = await env.step(move_action)
                    reward = max(0.001, min(result.reward or 0.01, 0.999))
                    rewards.append(reward)
                    log_step(step=steps_taken, action=f"MOVE {pr.email_id} {pr.action_move_to}", reward=reward, done=result.done)
                    if result.done:
                        done = True
                        break
                
                # Execute REPLY action
                if pr.action_reply_body and not done:
                    steps_taken += 1
                    reply_action = EmailAction(
                        action_type=ActionType.REPLY,
                        email_id=pr.email_id,
                        body=pr.action_reply_body
                    )
                    result = await env.step(reply_action)
                    reward = max(0.001, min(result.reward or 0.01, 0.999))
                    rewards.append(reward)
                    log_step(step=steps_taken, action=f"REPLY {pr.email_id}", reward=reward, done=result.done)
                    if result.done:
                        done = True
                        break
                
                # Execute FORWARD action
                if pr.action_forward_to and not done:
                    steps_taken += 1
                    forward_action = EmailAction(
                        action_type=ActionType.FORWARD,
                        email_id=pr.email_id,
                        to_address=pr.action_forward_to
                    )
                    result = await env.step(forward_action)
                    reward = max(0.001, min(result.reward or 0.01, 0.999))
                    rewards.append(reward)
                    log_step(step=steps_taken, action=f"FORWARD {pr.email_id} {pr.action_forward_to}", reward=reward, done=result.done)
                    if result.done:
                        done = True
                        break
                
                # Record analytics
                classification = pr.classification.get("classification", {})
                analytics_store.record_email(EmailMetric(
                    email_id=pr.email_id,
                    task_name=task_name,
                    category=classification.get("category", "unknown"),
                    was_spam=classification.get("category") == "spam",
                    reply_sent=pr.action_reply_body is not None,
                    forwarded=pr.action_forward_to is not None,
                    forward_to=pr.action_forward_to,
                    classification_confidence=classification.get("confidence", 0.5),
                    response_confidence=pr.response.get("response", {}).get("confidence", 0.5),
                    routing_confidence=pr.routing.get("routing", {}).get("confidence", 0.5),
                    processing_time_ms=pr.total_duration_ms,
                    reward=reward,
                    timestamp=time.time(),
                ))
        
        # Phase 4: Submit for grading
        if not done:
            try:
                result = await env.step(EmailAction(action_type=ActionType.SUBMIT))
                reward = result.reward if result.reward is not None else 0.01
                reward = max(0.001, min(reward, 0.999))
                score = reward
                rewards.append(reward)
                done = True
            except Exception as e:
                print(f"[SUBMIT ERROR] {e}", flush=True)
                try:
                    result = await env.step(EmailAction(action_type=ActionType.SUBMIT))
                    reward = max(0.001, min(result.reward or 0.01, 0.999))
                    score = reward
                    rewards.append(score)
                    done = True
                except Exception as e2:
                    print(f"[SUBMIT RETRY FAILED] {e2}", flush=True)

        score = max(0.001, min(score, 0.999))
        success = score >= 0.99
        steps_taken = max(1, steps_taken)
        if len(rewards) == 0:
            rewards.append(score)
        
        # End reasoning trace and record task score
        reasoning_engine.end_episode(score, len(emails_data))
        analytics_store.record_task_score(task_name, score)
        
        print(f"\n🏆 Task '{task_name}' completed — Score: {score:.3f}", flush=True)
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)
        
    except Exception as e:
        print(f"CRITICAL ERROR in run_task: {e}", flush=True)
        steps_taken = max(1, steps_taken)
        if len(rewards) == 0:
            rewards.append(0.01)
        log_end(success=False, steps=steps_taken, score=0.01, rewards=rewards)
    finally:
        try:
            await env.close()
        except Exception:
            pass

async def main():
    url = ENV_URL
    try:
        if not await wait_for_server(url):
            print(f"Server at {url} not reachable. Proceeding with caution...", flush=True)
    except Exception as e:
        print(f"Error during wait_for_server: {e}", flush=True)

    try:
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        # Fallbacks for local testing but populating directly into os.environ
        if "API_BASE_URL" not in os.environ:
            os.environ["API_BASE_URL"] = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if "API_KEY" not in os.environ:
            os.environ["API_KEY"] = os.environ.get("OPENAI_API_KEY", "dummy_key")
        
        # Explicitly configure exactly as demanded by the hackathon platform's instructions
        client = AsyncOpenAI(
            base_url=os.environ["API_BASE_URL"],
            api_key=os.environ["API_KEY"]
        )
        
        fallback_client = None
        fallback_model_name = None
        if "GROQ_API_KEY" in os.environ:
            fallback_client = AsyncOpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=os.environ["GROQ_API_KEY"]
            )
            fallback_model_name = "llama-3.3-70b-versatile"
        
        model_name = os.environ.get("MODEL_NAME", "gpt-4o-mini")
        print(f"\n{'='*70}", flush=True)
        print(f"📧 Email Triage AI — Multi-Agent Inference Engine", flush=True)
        print(f"   Model: {model_name}", flush=True)
        print(f"   Server: {url}", flush=True)
        print(f"   Pipeline: Classifier → Responder → Router", flush=True)
        print(f"{'='*70}\n", flush=True)

        try:
            print("[LLM PROXY TEST] Making initial call...", flush=True)
            test_response = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": "Hello"}
                ],
                temperature=0.01
            )
            print("[LLM PROXY SUCCESS]", test_response.choices[0].message.content, flush=True)
        except Exception as e:
            print("[LLM PROXY ERROR]", e, flush=True)

        # We test all 3 tasks sequentially
        for task in ["easy", "medium", "hard"]:
            try:
                await run_task(task, client, url, model_name, fallback_client, fallback_model_name)
            except Exception as task_error:
                print(f"Error running task {task}: {task_error}", flush=True)
        
        # Print final analytics summary
        summary = analytics_store.get_summary()
        print(f"\n{'='*70}", flush=True)
        print(f"📊 ANALYTICS SUMMARY", flush=True)
        print(f"   Emails Processed: {summary['overview']['total_emails']}", flush=True)
        print(f"   Spam Blocked: {summary['overview']['spam_detected']}", flush=True)
        print(f"   Replies Sent: {summary['overview']['replies_sent']}", flush=True)
        print(f"   Avg Reward: {summary['performance']['avg_reward']:.3f}", flush=True)
        print(f"   Task Scores: {summary['performance']['task_scores']}", flush=True)
        print(f"{'='*70}\n", flush=True)
        
    except Exception as e:
        print(f"Unhandled exception in main: {e}", flush=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"FATAL ERROR: {e}", flush=True)
        sys.exit(1) # We still exit non-zero if it's truly fatal, but we logged it
