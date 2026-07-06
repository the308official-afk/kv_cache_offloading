#!/usr/bin/env python3
"""Patch isolated cache-pinning Dynamo source with direct decision-path logs."""

from __future__ import annotations

import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = Path(
    os.environ.get("SOURCE_DIR", ROOT / "upstream" / "dynamo_cache_pinning")
)


def write_if_changed(path: Path, text: str) -> None:
    old = path.read_text()
    if old == text:
        print(f"unchanged: {path}")
        return
    path.write_text(text)
    print(f"updated: {path}")


def ensure_cache_control_endpoint_block(text: str, path: Path) -> str:
    if "cache_control_endpoint = runtime.endpoint(" in text:
        return text
    anchor = "    shutdown_endpoints[:] = [generate_endpoint]"
    insert = """    cache_control_endpoint = runtime.endpoint(
        f"{dynamo_args.namespace}.{dynamo_args.component}.cache_control"
    )

"""
    idx = text.find(anchor)
    if idx < 0:
        raise SystemExit(f"Could not find shutdown_endpoints anchor in {path}")
    return text[:idx] + insert + text[idx:]


def ensure_cache_control_shutdown_tracking(text: str, path: Path) -> str:
    old = "    shutdown_endpoints[:] = [generate_endpoint]\n"
    new = "    shutdown_endpoints[:] = [generate_endpoint, cache_control_endpoint]\n"
    if old not in text:
        raise SystemExit(f"Could not find shutdown_endpoints block in {path}")
    return text.replace(old, new)


def ensure_cache_control_serve_endpoint(text: str, path: Path) -> str:
    if "cache_control_endpoint.serve_endpoint(" in text:
        return text
    anchor = """            register_model_with_readiness_gate(
"""
    insert = """            cache_control_endpoint.serve_endpoint(
                handler.cache_control,
                metrics_labels=metrics_labels,
            ),
"""
    idx = text.find(anchor)
    if idx < 0:
        raise SystemExit(f"Could not find register_model_with_readiness_gate anchor in {path}")
    return text[:idx] + insert + text[idx:]


def repair_push_router() -> None:
    path = SOURCE_DIR / "lib/llm/src/kv_router/push_router.rs"
    text = path.read_text()

    if "[CACHE_PINNING_JSON]" in text:
        print(f"unchanged: {path}")
        return

    old = """        // Extract pin state: lazily init cache_control client on first PIN request
        let pin_state: Option<PinState> = async {
            let ttl = request.routing.as_ref().and_then(|r| r.cache_control_ttl)?;
            let cell = self.cache_control_cell.as_ref()?;
            let component = self.chooser.client().endpoint.component().clone();
            let client = cell
                .get_or_try_init(|| create_cache_control_client(&component))
                .await
                .inspect_err(|e| tracing::warn!(\"Failed to create cache_control client: {e}\"))
                .ok()?
                .clone();
            Some(PinState {
                token_ids: request.token_ids.clone(),
                cc_client: client,
                instance_id,
                ttl_seconds: ttl,
            })
        }
        .await;
"""
    new = """        // Extract pin state: lazily init cache_control client on first PIN request
        let cache_control_ttl = request.routing.as_ref().and_then(|r| r.cache_control_ttl);
        tracing::info!(
            "[CACHE_PINNING_JSON] {}",
            json!({
                "event_type": "router.cache_control_seen",
                "request_id": context_id,
                "cache_control_ttl": cache_control_ttl,
                "cache_control_enabled": self.cache_control_cell.is_some(),
                "prompt_tokens": request.token_ids.len(),
            })
        );
        let pin_state: Option<PinState> = async {
            let ttl = cache_control_ttl?;
            let cell = self.cache_control_cell.as_ref()?;
            let component = self.chooser.client().endpoint.component().clone();
            let client = cell
                .get_or_try_init(|| create_cache_control_client(&component))
                .await
                .inspect_err(|e| tracing::warn!(\"Failed to create cache_control client: {e}\"))
                .ok()?
                .clone();
            Some(PinState {
                token_ids: request.token_ids.clone(),
                cc_client: client,
                instance_id,
                ttl_seconds: ttl,
            })
        }
        .await;
        match &pin_state {
            Some(pin) => {
                tracing::info!(
                    "[CACHE_PINNING_JSON] {}",
                    json!({
                        "event_type": "router.pin_state_created",
                        "request_id": context_id,
                        "cache_control_ttl": pin.ttl_seconds,
                        "worker_id": pin.instance_id,
                        "prompt_tokens": pin.token_ids.len(),
                    })
                );
            }
            None => {
                let reason = if cache_control_ttl.is_none() {
                    "cache_control_ttl_missing"
                } else if self.cache_control_cell.is_none() {
                    "cache_control_disabled"
                } else {
                    "cache_control_client_unavailable"
                };
                tracing::info!(
                    "[CACHE_PINNING_JSON] {}",
                    json!({
                        "event_type": "router.pin_state_skipped",
                        "request_id": context_id,
                        "cache_control_ttl": cache_control_ttl,
                        "reason": reason,
                        "prompt_tokens": request.token_ids.len(),
                    })
                );
            }
        }
"""
    if old not in text:
        raise SystemExit(f"Could not find pin-state block in {path}")
    text = text.replace(old, new, 1)

    old = """        if let Some(ref pin) = self.pin_state {
            spawn_pin_prefix(
                Some(&pin.cc_client),
                &pin.token_ids,
                pin.instance_id,
                &self.context_id,
                pin.ttl_seconds,
            );
        }
"""
    new = """        if let Some(ref pin) = self.pin_state {
            tracing::info!(
                "[CACHE_PINNING_JSON] {}",
                json!({
                    "event_type": "router.pin_prefix_spawned",
                    "request_id": self.context_id,
                    "worker_id": pin.instance_id,
                    "ttl_seconds": pin.ttl_seconds,
                    "prompt_tokens": pin.token_ids.len(),
                })
            );
            spawn_pin_prefix(
                Some(&pin.cc_client),
                &pin.token_ids,
                pin.instance_id,
                &self.context_id,
                pin.ttl_seconds,
            );
        }
"""
    if old not in text:
        raise SystemExit(f"Could not find pin-prefix spawn block in {path}")
    text = text.replace(old, new, 1)
    write_if_changed(path, text)


def repair_init_llm() -> None:
    path = SOURCE_DIR / "components/src/dynamo/sglang/init_llm.py"
    text = path.read_text()

    text = ensure_cache_control_endpoint_block(text, path)

    # init_llm.py contains both init_decode and init_prefill. Replace all
    # matching startup blocks so both paths expose the cache_control endpoint.
    text = ensure_cache_control_shutdown_tracking(text, path)
    text = ensure_cache_control_serve_endpoint(text, path)

    write_if_changed(path, text)


def repair_dynamo_base_template() -> None:
    path = SOURCE_DIR / "container/templates/dynamo_base.Dockerfile"
    text = path.read_text()

    start = text.find("# Install NATS server\n")
    end = text.find("# Install etcd\n", start)
    if start < 0 or end < 0:
        raise SystemExit(f"Could not find NATS install block in {path}")

    replacement = """# Install NATS server
ARG NATS_VERSION
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \\
    NATS_ARCH="${TARGETARCH:-${ARCH:-}}" && \\
    NATS_ARCH="${NATS_ARCH#linux/}" && \\
    if [ "$NATS_ARCH" = "aarch64" ]; then NATS_ARCH="arm64"; fi && \\
    if [ "$NATS_ARCH" != "amd64" ] && [ "$NATS_ARCH" != "arm64" ]; then \\
        echo "Unsupported NATS arch: $NATS_ARCH" >&2; exit 1; \\
    fi && \\
    wget --tries=3 --waitretry=5 https://github.com/nats-io/nats-server/releases/download/${NATS_VERSION}/nats-server-${NATS_VERSION}-${NATS_ARCH}.deb && \\
    dpkg -i nats-server-${NATS_VERSION}-${NATS_ARCH}.deb && rm nats-server-${NATS_VERSION}-${NATS_ARCH}.deb

"""
    updated = text[:start] + replacement + text[end:]

    # Keep the change idempotent even if an older broken block used ${ARCH}
    # while a newer source used ${TARGETARCH}.
    updated = re.sub(
        r'nats-server-\$\{NATS_VERSION\}-\$\{(?:TARGETARCH|ARCH)\}\.deb',
        'nats-server-${NATS_VERSION}-${NATS_ARCH}.deb',
        updated,
    )

    write_if_changed(path, updated)


def repair_etcd_install_block() -> None:
    path = SOURCE_DIR / "container/templates/dynamo_base.Dockerfile"
    text = path.read_text()

    start = text.find("# Install etcd\n")
    end = text.find("ENV PATH=/usr/local/bin/etcd/:$PATH\n", start)
    if start < 0 or end < 0:
        raise SystemExit(f"Could not find etcd install block in {path}")
    end += len("ENV PATH=/usr/local/bin/etcd/:$PATH\n")

    replacement = """# Install etcd
ARG ETCD_VERSION
RUN ETCD_ARCH="${TARGETARCH:-${ARCH:-}}" && \\
    ETCD_ARCH="${ETCD_ARCH#linux/}" && \\
    if [ "$ETCD_ARCH" = "aarch64" ]; then ETCD_ARCH="arm64"; fi && \\
    if [ "$ETCD_ARCH" != "amd64" ] && [ "$ETCD_ARCH" != "arm64" ]; then \\
        echo "Unsupported ETCD arch: $ETCD_ARCH" >&2; exit 1; \\
    fi && \\
    wget --tries=3 --waitretry=5 https://github.com/etcd-io/etcd/releases/download/$ETCD_VERSION/etcd-$ETCD_VERSION-linux-${ETCD_ARCH}.tar.gz -O /tmp/etcd.tar.gz && \\
    mkdir -p /usr/local/bin/etcd && \\
    tar -xvf /tmp/etcd.tar.gz -C /usr/local/bin/etcd --strip-components=1 && \\
    rm /tmp/etcd.tar.gz
ENV PATH=/usr/local/bin/etcd/:$PATH
"""
    updated = text[:start] + replacement + text[end:]
    updated = re.sub(
        r'etcd-\$ETCD_VERSION-linux-\$\{(?:TARGETARCH|ARCH)\}\.tar\.gz',
        'etcd-$ETCD_VERSION-linux-${ETCD_ARCH}.tar.gz',
        updated,
    )

    write_if_changed(path, updated)


def main() -> None:
    repair_push_router()
    repair_init_llm()
    repair_dynamo_base_template()
    repair_etcd_install_block()
    print("Cache-pinning Dynamo source repair complete.")


if __name__ == "__main__":
    main()
