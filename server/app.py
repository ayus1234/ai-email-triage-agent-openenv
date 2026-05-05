# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
FastAPI application for the My Env Environment.
"""

try:
    from openenv.core.env_server.http_server import create_app
except ImportError as e:
    raise ImportError(
        "openenv is required for the web interface. Install dependencies with '\n    uv sync\n'"
    ) from e

import os

from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

try:
    from ..models import EmailAction, EmailObservation
    from .my_env_environment import MyEnvironment
    from .dashboard import router as dashboard_router
except (ImportError, ValueError):
    try:
        from models import EmailAction, EmailObservation
        from server.my_env_environment import MyEnvironment
        from server.dashboard import router as dashboard_router
    except ImportError:
        import sys
        sys.path.append(os.getcwd())
        from models import EmailAction, EmailObservation
        from server.my_env_environment import MyEnvironment
        from server.dashboard import router as dashboard_router


# Create the app with web interface
app = create_app(
    MyEnvironment,
    EmailAction,
    EmailObservation,
    env_name="my_env",
    max_concurrent_envs=1,
)

# Mount the dashboard and analytics API routes
app.include_router(dashboard_router)

# Serve static files (CSS, JS, images) from the server/ directory
_server_dir = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=_server_dir), name="static")

@app.middleware("http")
async def force_redirect_root_to_dashboard(request, call_next):
    """
    Middleware to ensure the root URL ALWAYS redirects to the premium dashboard,
    bypassing any default routes set by the openenv create_app logic.
    """
    if request.url.path == "/":
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/dashboard", status_code=307)
    return await call_next(request)


def main(host: str = "0.0.0.0", port: int = 7860):
    """
    Entry point for direct execution via uv run or python -m.
    """
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    main(port=args.port) # main()
