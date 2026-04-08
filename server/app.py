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

try:
    from ..models import EmailAction, EmailObservation
    from .my_env_environment import MyEnvironment
except (ImportError, ValueError):
    try:
        from models import EmailAction, EmailObservation
        from server.my_env_environment import MyEnvironment
    except ImportError:
        import sys
        import os
        sys.path.append(os.getcwd())
        from models import EmailAction, EmailObservation
        from server.my_env_environment import MyEnvironment


# Create the app with web interface
app = create_app(
    MyEnvironment,
    EmailAction,
    EmailObservation,
    env_name="my_env",
    max_concurrent_envs=1,
)


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
