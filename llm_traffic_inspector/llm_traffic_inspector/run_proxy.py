from __future__ import annotations

import uvicorn

from .config import ProxyConfig
from .proxy_app import create_app


def main() -> None:
    config = ProxyConfig.from_env()
    app = create_app(config)
    print("Local LLM Traffic Inspector")
    print(f"Provider: {config.provider}")
    print(f"Upstream: {config.upstream_base_url}")
    print(f"Capture mode: {config.capture_mode}")
    print(f"Logs: {config.log_directory}")
    print(f"Listening: http://{config.bind_host}:{config.port}")
    uvicorn.run(app, host=config.bind_host, port=config.port, log_level="info")


if __name__ == "__main__":
    main()

