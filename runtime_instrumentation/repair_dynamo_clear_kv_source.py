#!/usr/bin/env python3
"""Repair Dynamo source so precise runtimes expose clear_kv_blocks end to end.

This keeps the fix small and idempotent:
- export the frontend `clear_kv_blocks` route module
- merge the frontend `/clear_kv_blocks` route into the live HTTP router
- make the frontend HTTP state carry the distributed runtime
- pass the distributed runtime into the HTTP builder
- expose saved model-card instance keys from ModelManager
- rewrite the frontend flush route to match the pinned Dynamo API
- register/serve `clear_kv_blocks` in SGLang init paths
- add `clear_kv_blocks()` handler that calls `flush_cache()`
- register the engine route so frontend clear_kv_blocks can reach workers
"""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = Path(os.environ.get("SOURCE_DIR", ROOT / "upstream" / "dynamo"))


def write_if_changed(path: Path, text: str) -> None:
    old = path.read_text()
    if old == text:
        print(f"unchanged: {path}")
        return
    path.write_text(text)
    print(f"updated: {path}")


def repair_http_service_module() -> None:
    path = SOURCE_DIR / "lib/llm/src/http/service.rs"
    text = path.read_text()

    line = "pub mod clear_kv_blocks;\n"
    if line not in text:
        anchor = "pub mod busy_threshold;\n"
        if anchor not in text:
            raise SystemExit(f"Could not find busy_threshold module anchor in {path}")
        text = text.replace(anchor, line + anchor, 1)

    write_if_changed(path, text)


def repair_model_manager() -> None:
    path = SOURCE_DIR / "lib/llm/src/discovery/model_manager.rs"
    text = path.read_text()

    method = """
    pub fn get_model_card_keys(&self) -> Vec<String> {
        self.cards.iter().map(|r| r.key().clone()).collect()
    }

"""
    if "pub fn get_model_card_keys(&self) -> Vec<String>" not in text:
        anchor = """    pub fn get_model_cards(&self) -> Vec<ModelDeploymentCard> {
        self.cards.iter().map(|r| r.value().clone()).collect()
    }
"""
        if anchor not in text:
            raise SystemExit(f"Could not find get_model_cards anchor in {path}")
        text = text.replace(anchor, anchor + method, 1)

    write_if_changed(path, text)


def repair_http_service_v2() -> None:
    path = SOURCE_DIR / "lib/llm/src/http/service/service_v2.rs"
    text = path.read_text()

    import_line = "use dynamo_runtime::DistributedRuntime;\n"
    if import_line not in text:
        anchor = "use derive_builder::Builder;\n"
        if anchor not in text:
            raise SystemExit(f"Could not find derive_builder import anchor in {path}")
        text = text.replace(anchor, anchor + import_line, 1)

    state_field = "    runtime: Option<DistributedRuntime>,\n"
    if state_field not in text:
        anchor = "    discovery_client: Arc<dyn Discovery>,\n"
        if anchor not in text:
            raise SystemExit(f"Could not find State discovery_client field anchor in {path}")
        text = text.replace(anchor, anchor + state_field, 1)

    old_sig = """    pub fn new(
        manager: Arc<ModelManager>,
        discovery_client: Arc<dyn Discovery>,
        cancel_token: CancellationToken,
    ) -> Self {
"""
    new_sig = """    pub fn new(
        manager: Arc<ModelManager>,
        discovery_client: Arc<dyn Discovery>,
        runtime: Option<DistributedRuntime>,
        cancel_token: CancellationToken,
    ) -> Self {
"""
    if new_sig not in text:
        if old_sig not in text:
            raise SystemExit(f"Could not find State::new signature anchor in {path}")
        text = text.replace(old_sig, new_sig, 1)

    init_anchor = "            discovery_client,\n"
    if "            runtime,\n" not in text:
        idx = text.find(init_anchor)
        if idx < 0:
            raise SystemExit(f"Could not find State::new init anchor in {path}")
        idx += len(init_anchor)
        text = text[:idx] + "            runtime,\n" + text[idx:]

    runtime_method = """
    pub fn runtime(&self) -> Option<&DistributedRuntime> {
        self.runtime.as_ref()
    }

"""
    if "pub fn runtime(&self) -> Option<&DistributedRuntime>" not in text:
        anchor = """    pub fn discovery(&self) -> Arc<dyn Discovery> {
        self.discovery_client.clone()
    }
"""
        if anchor not in text:
            raise SystemExit(f"Could not find State::discovery anchor in {path}")
        text = text.replace(anchor, anchor + runtime_method, 1)

    route_line = "            super::clear_kv_blocks::clear_kv_blocks_router(state.clone(), None),\n"
    if route_line not in text:
        anchor = "            super::busy_threshold::busy_threshold_router(state.clone(), None),\n"
        if anchor not in text:
            raise SystemExit(f"Could not find busy_threshold router anchor in {path}")
        text = text.replace(anchor, anchor + route_line, 1)

    config_field = """
    #[builder(default = "None")]
    distributed_runtime: Option<DistributedRuntime>,
"""
    if "distributed_runtime: Option<DistributedRuntime>" not in text:
        anchor = """    /// When set (e.g. DRT discovery), router metrics (dynamo_router_* with router_id label)
    /// are registered using discovery.instance_id() and exposed on /metrics.
    #[builder(default = "None")]
    drt_discovery: Option<Arc<dyn Discovery>>,
"""
        if anchor not in text:
            raise SystemExit(f"Could not find HttpServiceConfig drt_discovery anchor in {path}")
        text = text.replace(anchor, anchor + "\n" + config_field, 1)

    old_state_init = "        let state = Arc::new(State::new(model_manager, discovery_client, cancel_token));\n"
    new_state_init = """        let state = Arc::new(State::new(
            model_manager,
            discovery_client,
            config.distributed_runtime,
            cancel_token,
        ));
"""
    if new_state_init not in text:
        if old_state_init not in text:
            raise SystemExit(f"Could not find State::new build call anchor in {path}")
        text = text.replace(old_state_init, new_state_init, 1)

    write_if_changed(path, text)


def repair_http_entrypoint() -> None:
    path = SOURCE_DIR / "lib/llm/src/entrypoint/input/http.rs"
    text = path.read_text()

    builder_line = """    http_service_builder =
        http_service_builder.distributed_runtime(Some(distributed_runtime.clone()));
"""
    if "http_service_builder.distributed_runtime(Some(distributed_runtime.clone()))" not in text:
        anchor = """    http_service_builder =
        http_service_builder.with_request_template(engine_config.local_model().request_template());
"""
        if anchor not in text:
            raise SystemExit(f"Could not find request_template builder anchor in {path}")
        text = text.replace(anchor, anchor + builder_line, 1)

    write_if_changed(path, text)


def repair_clear_kv_route() -> None:
    path = SOURCE_DIR / "lib/llm/src/http/service/clear_kv_blocks.rs"
    text = """// SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

use super::{RouteDoc, service_v2};
use axum::{Json, http::Method, response::IntoResponse, routing::post};
use dynamo_runtime::{
    pipeline::{PushRouter, RouterMode, SingleIn},
    protocols::annotated::Annotated,
};
use futures::StreamExt;
use serde_json::{Value, json};
use std::collections::{BTreeMap, BTreeSet};
use std::sync::Arc;

pub const CLEAR_KV_ENDPOINT: &str = "clear_kv_blocks";

type ClearKvClient = PushRouter<Value, Annotated<Value>>;

pub fn clear_kv_blocks_router(
    state: Arc<service_v2::State>,
    path: Option<String>,
) -> (Vec<RouteDoc>, axum::Router) {
    let path = path.unwrap_or_else(|| "/clear_kv_blocks".to_string());

    let docs = vec![RouteDoc::new(Method::POST, &path)];
    let router = axum::Router::new()
        .route(&path, post(clear_kv_blocks_handler))
        .with_state(state);

    (docs, router)
}

fn parse_instance_key(key: &str) -> Option<(String, String, u64)> {
    let mut parts = key.split('/');
    let namespace = parts.next()?.to_string();
    let component = parts.next()?.to_string();
    let _endpoint = parts.next()?;
    let instance_hex = parts.next()?;
    let instance_id = u64::from_str_radix(instance_hex, 16).ok()?;
    Some((namespace, component, instance_id))
}

async fn clear_kv_blocks_handler(
    axum::extract::State(state): axum::extract::State<Arc<service_v2::State>>,
) -> impl IntoResponse {
    let runtime = match state.runtime() {
        Some(runtime) => runtime,
        None => {
            return Json(json!({
                "message": "Distributed runtime is unavailable"
            }));
        }
    };

    let card_keys = state.manager().get_model_card_keys();
    if card_keys.is_empty() {
        return Json(json!({
            "message": "No active worker groups found"
        }));
    }

    let mut targets: BTreeMap<(String, String), BTreeSet<u64>> = BTreeMap::new();
    for key in card_keys {
        if let Some((namespace, component, instance_id)) = parse_instance_key(&key) {
            targets
                .entry((namespace, component))
                .or_default()
                .insert(instance_id);
        }
    }

    if targets.is_empty() {
        return Json(json!({
            "message": "No active worker groups found"
        }));
    }

    let mut cleared_workers = Vec::new();
    let mut failed_workers = Vec::new();

    let mut add_worker_result = |success: bool,
                                 name: String,
                                 status: &str,
                                 ns: &str,
                                 comp: &str,
                                 payload: Option<Value>| {
        let mut result = json!({
            "name": name,
            "endpoint": format!("{}/{}/{}", ns, comp, CLEAR_KV_ENDPOINT),
            "status": status,
        });
        if success {
            if let Some(v) = payload {
                result["response"] = v;
            }
            cleared_workers.push(result);
        } else {
            if let Some(v) = payload {
                result["error"] = v;
            }
            failed_workers.push(result);
        }
    };

    for ((namespace, component), instance_ids) in targets {
        let component_obj = match runtime
            .namespace(&namespace)
            .and_then(|ns| ns.component(&component))
        {
            Ok(component_obj) => component_obj,
            Err(e) => {
                add_worker_result(
                    false,
                    format!("{namespace}/{component}"),
                    "Failed to resolve component",
                    &namespace,
                    &component,
                    Some(json!(e.to_string())),
                );
                continue;
            }
        };

        let endpoint = component_obj.endpoint(CLEAR_KV_ENDPOINT);
        let client = match endpoint.client().await {
            Ok(client) => client,
            Err(e) => {
                add_worker_result(
                    false,
                    format!("{namespace}/{component}"),
                    "Failed to get clear_kv_blocks client",
                    &namespace,
                    &component,
                    Some(json!(e.to_string())),
                );
                continue;
            }
        };

        if let Err(e) = client.wait_for_instances().await {
            add_worker_result(
                false,
                format!("{namespace}/{component}"),
                "No clear_kv_blocks workers registered",
                &namespace,
                &component,
                Some(json!(e.to_string())),
            );
            continue;
        }

        let router = match ClearKvClient::from_client_no_fault_detection(client, RouterMode::RoundRobin).await
        {
            Ok(router) => router,
            Err(e) => {
                add_worker_result(
                    false,
                    format!("{namespace}/{component}"),
                    "Failed to create clear_kv_blocks router",
                    &namespace,
                    &component,
                    Some(json!(e.to_string())),
                );
                continue;
            }
        };

        for instance_id in instance_ids {
            let instance_name = format!("{namespace}/{component}-instance-{instance_id}");
            match router.direct(SingleIn::new(json!({})), instance_id).await {
                Ok(mut stream) => {
                    let first = stream.next().await;
                    while stream.next().await.is_some() {}

                    match first {
                        Some(response) if !response.is_error() => {
                            let body = response.data.clone().unwrap_or_else(|| json!({"status": "ok"}));
                            add_worker_result(
                                true,
                                instance_name,
                                "Successfully cleared kv blocks for instance",
                                &namespace,
                                &component,
                                Some(body),
                            );
                        }
                        Some(response) => {
                            let body = response.data.clone().unwrap_or_else(|| json!({"status": "error"}));
                            add_worker_result(
                                false,
                                instance_name,
                                "clear_kv_blocks returned error",
                                &namespace,
                                &component,
                                Some(body),
                            );
                        }
                        None => {
                            add_worker_result(
                                false,
                                instance_name,
                                "No response from instance",
                                &namespace,
                                &component,
                                None,
                            );
                        }
                    }
                }
                Err(e) => {
                    add_worker_result(
                        false,
                        instance_name,
                        "Failed to send clear_kv_blocks request",
                        &namespace,
                        &component,
                        Some(json!(e.to_string())),
                    );
                }
            }
        }
    }

    Json(json!({
        "cleared_workers": cleared_workers,
        "failed_workers": failed_workers
    }))
}
"""
    if path.exists() and path.read_text() == text:
        print(f"unchanged: {path}")
        return
    path.write_text(text)
    print(f"updated: {path}")


def repair_init_llm() -> None:
    path = SOURCE_DIR / "components/src/dynamo/sglang/init_llm.py"
    text = path.read_text()

    endpoint_block = """    clear_kv_blocks_endpoint = runtime.endpoint(
        f"{dynamo_args.namespace}.{dynamo_args.component}.clear_kv_blocks"
    )

"""
    if "clear_kv_blocks_endpoint = runtime.endpoint(" not in text:
        anchor = "    shutdown_endpoints[:] = [generate_endpoint]"
        idx = text.find(anchor)
        if idx < 0:
            anchor = """    publisher, metrics_task, metrics_labels = await setup_sgl_metrics(
"""
            idx = text.find(anchor)
            if idx < 0:
                raise SystemExit(
                    f"Could not find shutdown_endpoints/publisher anchor in {path}"
                )
        text = text[:idx] + endpoint_block + text[idx:]

    simple_shutdown = "    shutdown_endpoints[:] = [generate_endpoint]\n"
    extended_shutdown = (
        "    shutdown_endpoints[:] = [generate_endpoint, clear_kv_blocks_endpoint]\n"
    )
    if extended_shutdown not in text:
        if simple_shutdown in text:
            text = text.replace(simple_shutdown, extended_shutdown, 1)
        else:
            anchor = """    publisher, metrics_task, metrics_labels = await setup_sgl_metrics(
"""
            idx = text.find(anchor)
            if idx < 0:
                raise SystemExit(
                    f"Could not find publisher anchor for shutdown_endpoints block in {path}"
                )
            text = text[:idx] + extended_shutdown + text[idx:]

    serve_block = """            clear_kv_blocks_endpoint.serve_endpoint(
                handler.clear_kv_blocks,
                metrics_labels=metrics_labels,
            ),
"""
    if "clear_kv_blocks_endpoint.serve_endpoint(" not in text:
        anchor = """            unload_lora_endpoint.serve_endpoint(
"""
        idx = text.find(anchor)
        if idx < 0:
            anchor = """            register_model_with_readiness_gate(
"""
            idx = text.find(anchor)
            if idx < 0:
                raise SystemExit(
                    f"Could not find serve_endpoint/register_model anchor in {path}"
                )
        text = text[:idx] + serve_block + text[idx:]

    write_if_changed(path, text)


CLEAR_KV_METHOD = """
    async def clear_kv_blocks(self, request=None, context=None):
        \"\"\"Clear the SGLang worker KV cache via tokenizer_manager.flush_cache().\"\"\"
        try:
            result = await self.call_tokenizer_manager({\"method\": \"flush_cache\"})
            if not isinstance(result, dict):
                result = {\"result\": result}
            result.setdefault(\"status\", \"success\")
            result.setdefault(\"message\", \"KV cache cleared\")
            yield result
        except Exception as e:
            logging.error(f\"Failed to clear KV cache: {e}\")
            yield {\"status\": \"error\", \"message\": str(e)}

"""


def repair_handler_base() -> None:
    path = SOURCE_DIR / "components/src/dynamo/sglang/request_handlers/handler_base.py"
    text = path.read_text()

    if "async def clear_kv_blocks(self, request=None, context=None):" not in text:
        anchor = """    def register_engine_routes(self, runtime: DistributedRuntime) -> None:
"""
        idx = text.find(anchor)
        if idx < 0:
            raise SystemExit(f"Could not find register_engine_routes anchor in {path}")
        text = text[:idx] + CLEAR_KV_METHOD + text[idx:]

    route_line = '        runtime.register_engine_route("clear_kv_blocks", self.clear_kv_blocks)\n'
    if route_line not in text:
        anchor = """        if getattr(self.config, "dynamo_args", None) and getattr(
"""
        idx = text.find(anchor)
        if idx < 0:
            raise SystemExit(
                f'Could not find RL-route anchor for clear_kv_blocks registration in {path}'
            )
        text = text[:idx] + route_line + text[idx:]

    write_if_changed(path, text)


def main() -> None:
    repair_model_manager()
    repair_http_service_module()
    repair_http_service_v2()
    repair_http_entrypoint()
    repair_clear_kv_route()
    repair_init_llm()
    repair_handler_base()
    print("Dynamo clear_kv_blocks source repair complete.")


if __name__ == "__main__":
    main()
