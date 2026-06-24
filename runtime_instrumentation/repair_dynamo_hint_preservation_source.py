#!/usr/bin/env python3
"""Repair Dynamo source so hint/observability fields survive to worker runtime.

This is intentionally idempotent. Use it when the tracked Rust patch no longer
applies cleanly to fresh upstream clones, but the current source layout is still
close enough that a narrow textual repair is safer than retrying a stale patch.
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


def repair_nvext() -> None:
    path = SOURCE_DIR / "lib/llm/src/protocols/openai/nvext.rs"
    text = path.read_text()

    nvext_extra_marker = "pub extra: std::collections::HashMap<String, serde_json::Value>,"
    if nvext_extra_marker not in text:
        marker = "    pub session_control: Option<SessionControl>,\n"
        insertion = """

    /// Experiment/observability extension fields supplied under `nvext`.
    ///
    /// Keeping these fields lets the preprocessor forward local observability
    /// metadata, such as AgentBench request context, without making it part of
    /// Dynamo's stable public API.
    #[builder(default)]
    #[serde(flatten)]
    pub extra: std::collections::HashMap<String, serde_json::Value>,
"""
        if marker not in text:
            raise SystemExit(f"Could not find session_control marker in {path}")
        text = text.replace(marker, marker + insertion, 1)

    expected_output_marker = "    pub expected_output_tokens: Option<u32>,\n"
    if expected_output_marker not in text:
        marker = "    pub osl: Option<u32>,\n"
        insertion = """

    /// AgentBench-friendly alias for expected output length.
    #[builder(default, setter(strip_option))]
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub expected_output_tokens: Option<u32>,
"""
        if marker not in text:
            raise SystemExit(f"Could not find osl marker in {path}")
        text = text.replace(marker, marker + insertion, 1)

    hint_extra_comment = "    /// Experiment/observability hint fields supplied by local harnesses.\n"
    if hint_extra_comment not in text:
        marker = "    pub latency_sensitivity: Option<f64>,\n"
        insertion = """

    /// Experiment/observability hint fields supplied by local harnesses.
    ///
    /// This preserves keys like `hint_probe_id`, `program_id`, `agent_phase`,
    /// and `context_type` so they can be forwarded to runtime logs.
    #[builder(default)]
    #[serde(flatten)]
    pub extra: std::collections::HashMap<String, serde_json::Value>,
"""
        if marker not in text:
            raise SystemExit(f"Could not find latency_sensitivity marker in {path}")
        text = text.replace(marker, marker + insertion, 1)

    write_if_changed(path, text)


def repair_preprocessor() -> None:
    path = SOURCE_DIR / "lib/llm/src/preprocessor.rs"
    text = path.read_text()

    old_import = "        nvext::NvExtProvider,\n"
    new_import = "        nvext::{NvExt, NvExtProvider},\n"
    if old_import in text and new_import not in text:
        text = text.replace(old_import, new_import, 1)

    runtime_fn_marker = "    fn runtime_observability_extra_args_from_nvext(nvext: &NvExt) -> Option<serde_json::Value> {"
    if runtime_fn_marker not in text:
        anchor = "    pub fn new_with_parts(\n"
        insertion = """
    fn runtime_observability_extra_args_from_nvext(nvext: &NvExt) -> Option<serde_json::Value> {
        let mut runtime_observability = serde_json::Map::new();
        let mut nested_nvext = serde_json::Map::new();

        if let Some(agent_hints) = nvext.agent_hints.as_ref()
            && let Ok(agent_hints_value) = serde_json::to_value(agent_hints)
            && agent_hints_value
                .as_object()
                .is_some_and(|agent_hints| !agent_hints.is_empty())
        {
            let agent_hints_keys = agent_hints_value
                .as_object()
                .map(|agent_hints| {
                    let mut keys = agent_hints.keys().cloned().collect::<Vec<_>>();
                    keys.sort();
                    keys
                })
                .unwrap_or_default();

            if let Some(hint_probe_id) = agent_hints_value
                .get("hint_probe_id")
                .and_then(serde_json::Value::as_str)
            {
                runtime_observability.insert(
                    "hint_probe_id".to_string(),
                    serde_json::Value::String(hint_probe_id.to_string()),
                );
            }

            runtime_observability.insert("agent_hints".to_string(), agent_hints_value.clone());
            runtime_observability.insert(
                "agent_hints_source".to_string(),
                serde_json::Value::String("nvext.agent_hints".to_string()),
            );
            runtime_observability.insert(
                "agent_hints_keys".to_string(),
                serde_json::json!(agent_hints_keys),
            );
            nested_nvext.insert("agent_hints".to_string(), agent_hints_value);
        }

        if let Some(request_context) = nvext.extra.get("request_context") {
            runtime_observability.insert("request_context".to_string(), request_context.clone());
            nested_nvext.insert("request_context".to_string(), request_context.clone());
        }

        if let Some(cache_control) = nvext.extra.get("cache_control") {
            runtime_observability.insert("cache_control".to_string(), cache_control.clone());
            runtime_observability.insert(
                "cache_control_source".to_string(),
                serde_json::Value::String("nvext.cache_control".to_string()),
            );
            nested_nvext.insert("cache_control".to_string(), cache_control.clone());
        }

        if runtime_observability.is_empty() {
            return None;
        }

        if !nested_nvext.is_empty() {
            runtime_observability.insert(
                "nvext".to_string(),
                serde_json::Value::Object(nested_nvext),
            );
        }

        Some(serde_json::json!({
            "runtime_observability": runtime_observability
        }))
    }

"""
        if anchor not in text:
            raise SystemExit(f"Could not find insertion anchor in {path}")
        text = text.replace(anchor, insertion + anchor, 1)
    elif 'runtime_observability.insert("cache_control".to_string(), cache_control.clone());' not in text:
        old_block = """        if let Some(request_context) = nvext.extra.get("request_context") {
            runtime_observability.insert("request_context".to_string(), request_context.clone());
            nested_nvext.insert("request_context".to_string(), request_context.clone());
        }

        if runtime_observability.is_empty() {
"""
        new_block = """        if let Some(request_context) = nvext.extra.get("request_context") {
            runtime_observability.insert("request_context".to_string(), request_context.clone());
            nested_nvext.insert("request_context".to_string(), request_context.clone());
        }

        if let Some(cache_control) = nvext.extra.get("cache_control") {
            runtime_observability.insert("cache_control".to_string(), cache_control.clone());
            runtime_observability.insert(
                "cache_control_source".to_string(),
                serde_json::Value::String("nvext.cache_control".to_string()),
            );
            nested_nvext.insert("cache_control".to_string(), cache_control.clone());
        }

        if runtime_observability.is_empty() {
"""
        if old_block not in text:
            raise SystemExit(f"Could not add cache_control preservation block in {path}")
        text = text.replace(old_block, new_block, 1)

    old_builder = "            let hints = nvext.agent_hints.as_ref();\n"
    new_builder = """            let hints = nvext.agent_hints.as_ref();
            if let Some(extra_args) = Self::runtime_observability_extra_args_from_nvext(nvext) {
                builder.extra_args(Some(extra_args));
            }
"""
    if old_builder in text and "builder.extra_args(Some(extra_args));" not in text:
        text = text.replace(old_builder, new_builder, 1)

    old_expected = "                expected_output_tokens: hints.and_then(|h| h.osl),\n"
    new_expected = "                expected_output_tokens: hints.and_then(|h| h.osl.or(h.expected_output_tokens)),\n"
    if old_expected in text:
        text = text.replace(old_expected, new_expected, 1)

    old_sig = "    pub async fn gather_multi_modal_data<R: OAIChatLikeRequest>(\n"
    new_sig = "    pub async fn gather_multi_modal_data<R: OAIChatLikeRequest + NvExtProvider>(\n"
    if old_sig in text:
        text = text.replace(old_sig, new_sig, 1)

    old_extra_args = """            let messages_json = serde_json::to_value(request.messages())?;
            let mut extra_args = serde_json::json!({
                "messages": messages_json
            });
"""
    new_extra_args = """            let messages_json = serde_json::to_value(request.messages())?;
            let mut extra_args = request
                .nvext()
                .and_then(Self::runtime_observability_extra_args_from_nvext)
                .unwrap_or_else(|| serde_json::json!({}));
            extra_args["messages"] = messages_json;
"""
    if old_extra_args in text:
        text = text.replace(old_extra_args, new_extra_args, 1)

    write_if_changed(path, text)


def main() -> None:
    repair_nvext()
    repair_preprocessor()
    print("Hint-preservation source repair complete.")


if __name__ == "__main__":
    main()
