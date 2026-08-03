from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


VALID_CAPTURE_MODES = {"safe", "full"}
VALID_AUTH_MODES = {"openai", "anthropic", "bearer", "x_api_key", "pass_through", "none"}


class ConfigError(ValueError):
    """Raised when proxy configuration is invalid."""


@dataclass(frozen=True)
class ProxyConfig:
    provider: str
    upstream_base_url: str
    capture_mode: str
    log_directory: Path
    bind_host: str = "127.0.0.1"
    port: int = 8787
    upstream_auth_mode: str = "none"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    upstream_api_key: str | None = None
    request_timeout_seconds: float = 300.0
    connect_timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "ProxyConfig":
        provider = os.environ.get("LLM_PROXY_PROVIDER", "custom").strip().lower()
        upstream_base_url = os.environ.get("LLM_PROXY_UPSTREAM_BASE_URL", "").strip()
        if not upstream_base_url:
            raise ConfigError("LLM_PROXY_UPSTREAM_BASE_URL is required.")

        capture_mode = os.environ.get("LLM_PROXY_CAPTURE_MODE", "safe").strip().lower()
        if capture_mode not in VALID_CAPTURE_MODES:
            raise ConfigError("LLM_PROXY_CAPTURE_MODE must be 'safe' or 'full'.")

        bind_host = os.environ.get("LLM_PROXY_BIND_HOST", "127.0.0.1").strip()
        if bind_host != "127.0.0.1":
            raise ConfigError("For safety, LLM_PROXY_BIND_HOST must be 127.0.0.1.")

        port_text = os.environ.get("LLM_PROXY_PORT", "8787")
        try:
            port = int(port_text)
        except ValueError as exc:
            raise ConfigError("LLM_PROXY_PORT must be an integer.") from exc

        log_directory = Path(os.environ.get("LLM_PROXY_LOG_DIRECTORY", "./logs")).expanduser()

        upstream_auth_mode = os.environ.get("LLM_PROXY_UPSTREAM_AUTH_MODE", "").strip().lower()
        if not upstream_auth_mode:
            upstream_auth_mode = default_auth_mode(provider)
        if upstream_auth_mode not in VALID_AUTH_MODES:
            raise ConfigError(
                "LLM_PROXY_UPSTREAM_AUTH_MODE must be one of: "
                + ", ".join(sorted(VALID_AUTH_MODES))
            )

        validate_upstream_url(upstream_base_url)

        return cls(
            provider=provider,
            upstream_base_url=upstream_base_url,
            capture_mode=capture_mode,
            log_directory=log_directory,
            bind_host=bind_host,
            port=port,
            upstream_auth_mode=upstream_auth_mode,
            openai_api_key=os.environ.get("LLM_PROXY_OPENAI_API_KEY"),
            anthropic_api_key=os.environ.get("LLM_PROXY_ANTHROPIC_API_KEY"),
            upstream_api_key=os.environ.get("LLM_PROXY_UPSTREAM_API_KEY"),
            request_timeout_seconds=float(os.environ.get("LLM_PROXY_REQUEST_TIMEOUT_SECONDS", "300")),
            connect_timeout_seconds=float(os.environ.get("LLM_PROXY_CONNECT_TIMEOUT_SECONDS", "30")),
        )

    def auth_key_for_mode(self) -> str | None:
        if self.upstream_auth_mode == "openai":
            return self.openai_api_key or self.upstream_api_key
        if self.upstream_auth_mode == "anthropic":
            return self.anthropic_api_key or self.upstream_api_key
        if self.upstream_auth_mode in {"bearer", "x_api_key"}:
            return self.upstream_api_key
        return None


def default_auth_mode(provider: str) -> str:
    if provider == "openai":
        return "openai"
    if provider == "anthropic":
        return "anthropic"
    if provider == "openai_compatible":
        return "bearer"
    return "none"


def validate_upstream_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConfigError("LLM_PROXY_UPSTREAM_BASE_URL must be an http(s) URL.")


def build_upstream_url(base_url: str, path: str, query_string: bytes) -> str:
    base = base_url.rstrip("/")
    clean_path = "/" + path.lstrip("/")
    url = base + clean_path
    if query_string:
        url += "?" + query_string.decode("utf-8", errors="replace")
    return url

