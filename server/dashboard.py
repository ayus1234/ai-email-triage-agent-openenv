"""
Dashboard API routes — serves analytics data and reasoning traces.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse

from analytics_store import analytics_store
from reasoning_engine import reasoning_engine
from inference import main as run_inference_pipeline

router = APIRouter()

@router.post("/api/start-agent")
async def start_agent():
    """Trigger the inference pipeline in the background."""
    import os
    os.environ["QUIET_MODE"] = "1"
    asyncio.create_task(run_inference_pipeline())
    return JSONResponse(content={"status": "started", "message": "Agent pipeline started"})


@router.get("/api/analytics")
async def get_analytics():
    """Return aggregated analytics data."""
    return JSONResponse(content=analytics_store.get_summary())


@router.get("/api/reasoning")
async def get_all_reasoning():
    """Return all reasoning traces."""
    return JSONResponse(content=reasoning_engine.get_all_traces())


@router.get("/api/reasoning/latest")
async def get_latest_reasoning():
    """Return the most recent reasoning trace."""
    trace = reasoning_engine.get_latest_trace()
    return JSONResponse(content=trace or {"error": "No traces yet"})


@router.get("/api/reasoning/{episode_id}")
async def get_reasoning_trace(episode_id: str):
    """Return reasoning trace for a specific episode."""
    trace = reasoning_engine.get_episode_trace(episode_id)
    if trace:
        return JSONResponse(content=trace)
    return JSONResponse(content={"error": "Episode not found"}, status_code=404)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    """Serve the premium analytics dashboard."""
    html_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Dashboard HTML not found</h1>", status_code=500)


@router.get("/dashboard.css")
async def dashboard_css():
    """Serve the external CSS file for the dashboard."""
    from fastapi.responses import Response
    css_path = os.path.join(os.path.dirname(__file__), "dashboard.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            return Response(content=f.read(), media_type="text/css")
    return Response(content="", media_type="text/css", status_code=404)
