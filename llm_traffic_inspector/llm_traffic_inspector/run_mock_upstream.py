from __future__ import annotations

import os

import uvicorn

from .mock_upstream import create_mock_app


def main() -> None:
    host = "127.0.0.1"
    port = int(os.environ.get("LLM_PROXY_MOCK_PORT", "8799"))
    print(f"Mock upstream listening: http://{host}:{port}")
    uvicorn.run(create_mock_app(), host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()

