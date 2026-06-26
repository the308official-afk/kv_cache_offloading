#!/usr/bin/env python3
"""Repair Dynamo speculative-prefill source for direct runtime attribution.

This keeps the pinned/fresh Dynamo clone aligned with the local experiment
workflow by adding structured runtime JSON events to the real
`speculative_prefill` decision path.
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


def ensure_imports(text: str, path: Path) -> str:
    old = "use std::pin::Pin;\nuse std::sync::Arc;\n"
    new = "use std::pin::Pin;\nuse std::sync::{Arc, OnceLock};\n"
    if old in text and new not in text:
        text = text.replace(old, new, 1)

    old = "use minijinja::value::Value;\n"
    new = "use minijinja::value::Value;\nuse serde_json::{Map as JsonMap, Value as JsonValue, json};\n"
    if old in text and "Map as JsonMap" not in text:
        text = text.replace(old, new, 1)
    return text


def ensure_helper_block(text: str, path: Path) -> str:
    marker = "fn runtime_json_logs_enabled() -> bool {"
    if marker in text:
        return text
    anchor = "/// A minimal `OAIChatLikeRequest` for speculative next-turn prefill.\n"
    helper_block = """fn runtime_json_logs_enabled() -> bool {
    static ENABLED: OnceLock<bool> = OnceLock::new();
    *ENABLED.get_or_init(|| {
        std::env::var(\"DYN_RUNTIME_JSON_LOGS\")
            .map(|value| {
                let lowered = value.to_ascii_lowercase();
                !matches!(lowered.as_str(), \"\" | \"0\" | \"false\")
            })
            .unwrap_or(false)
    })
}

#[derive(Clone, Debug, Default)]
struct SpeculativePrefillMetadata {
    request_id: Option<String>,
    parent_run_id: Option<String>,
    phase: Option<String>,
    step_title: Option<String>,
    hint_probe_id: Option<String>,
    target_request_id: Option<String>,
    target_hint_probe_id: Option<String>,
    speculative_prefill: bool,
}

impl SpeculativePrefillMetadata {
    fn from_request(request: &NvCreateChatCompletionRequest, speculative_prefill: bool) -> Self {
        let request_context = request
            .nvext
            .as_ref()
            .and_then(|nvext| nvext.extra.get(\"request_context\"))
            .and_then(JsonValue::as_object);
        let hint_probe_id = request
            .nvext
            .as_ref()
            .and_then(|nvext| nvext.agent_hints.as_ref())
            .and_then(|hints| hints.extra.get(\"hint_probe_id\"))
            .and_then(JsonValue::as_str)
            .map(str::to_string);
        let target_request_id = request
            .nvext
            .as_ref()
            .and_then(|nvext| nvext.agent_hints.as_ref())
            .and_then(|hints| hints.extra.get(\"spec_prefill_target_request_id\"))
            .and_then(JsonValue::as_str)
            .map(str::to_string);
        let target_hint_probe_id = request
            .nvext
            .as_ref()
            .and_then(|nvext| nvext.agent_hints.as_ref())
            .and_then(|hints| hints.extra.get(\"spec_prefill_target_hint_probe_id\"))
            .and_then(JsonValue::as_str)
            .map(str::to_string);

        Self {
            request_id: request_context
                .and_then(|context| context.get(\"request_id\"))
                .and_then(JsonValue::as_str)
                .map(str::to_string),
            parent_run_id: request_context
                .and_then(|context| context.get(\"parent_run_id\"))
                .and_then(JsonValue::as_str)
                .map(str::to_string),
            phase: request_context
                .and_then(|context| context.get(\"phase\"))
                .and_then(JsonValue::as_str)
                .map(str::to_string),
            step_title: request_context
                .and_then(|context| context.get(\"step_title\"))
                .and_then(JsonValue::as_str)
                .map(str::to_string),
            hint_probe_id,
            target_request_id,
            target_hint_probe_id,
            speculative_prefill,
        }
    }
}

fn emit_spec_prefill_event(
    event_type: &str,
    metadata: &SpeculativePrefillMetadata,
    extra: JsonMap<String, JsonValue>,
) {
    if !runtime_json_logs_enabled() {
        return;
    }

    let mut event = json!({
        \"event_type\": event_type,
        \"component\": \"preprocessor.speculative_prefill\",
        \"request_id\": metadata.request_id,
        \"parent_run_id\": metadata.parent_run_id,
        \"phase\": metadata.phase,
        \"step_title\": metadata.step_title,
        \"hint_probe_id\": metadata.hint_probe_id,
        \"spec_prefill_target_request_id\": metadata.target_request_id,
        \"spec_prefill_target_hint_probe_id\": metadata.target_hint_probe_id,
        \"speculative_prefill\": metadata.speculative_prefill,
    });

    if let Some(object) = event.as_object_mut() {
        for (key, value) in extra {
            object.insert(key, value);
        }
    }

    tracing::info!(\"[RUNTIME_JSON] {}\", event);
}

"""
    if anchor not in text:
        raise SystemExit(f"Could not find speculative-prefill helper anchor in {path}")
    return text.replace(anchor, helper_block + anchor, 1)


def ensure_wrap_instrumentation(text: str, path: Path) -> str:
    old = """    let enabled = request
        .nvext
        .as_ref()
        .and_then(|ext| ext.agent_hints.as_ref())
        .and_then(|hints| hints.speculative_prefill)
        .unwrap_or(false);

    if !enabled {
        return stream;
    }

    let (tx, rx) = tokio::sync::oneshot::channel::<String>();

    let next = next.clone();
    let formatter = formatter.clone();
    let tokenizer = tokenizer.clone();
    let messages = request.inner.messages.clone();
    tokio::spawn(async move {
        let Ok(response_text) = rx.await else {
            return;
        };
        if let Err(e) = prefill_task(next, formatter, tokenizer, messages, response_text).await {
            tracing::warn!(error = %e, \"Speculative prefill failed\");
        }
    });

    let mut accumulated_text = String::new();
    let mut prefill_tx = Some(tx);
    Box::pin(stream.map(move |item| {
"""
    new = """    let enabled = request
        .nvext
        .as_ref()
        .and_then(|ext| ext.agent_hints.as_ref())
        .and_then(|hints| hints.speculative_prefill)
        .unwrap_or(false);
    let metadata = SpeculativePrefillMetadata::from_request(request, enabled);
    emit_spec_prefill_event(
        \"worker.spec_prefill.wrap_checked\",
        &metadata,
        JsonMap::from_iter([(\"enabled\".to_string(), JsonValue::Bool(enabled))]),
    );

    if !enabled {
        return stream;
    }

    let (tx, rx) = tokio::sync::oneshot::channel::<String>();

    let next = next.clone();
    let formatter = formatter.clone();
    let tokenizer = tokenizer.clone();
    let messages = request.inner.messages.clone();
    let task_metadata = metadata.clone();
    emit_spec_prefill_event(
        \"worker.spec_prefill.task_spawned\",
        &task_metadata,
        JsonMap::new(),
    );
    tokio::spawn(async move {
        let Ok(response_text) = rx.await else {
            emit_spec_prefill_event(
                \"worker.spec_prefill.prefill_skipped\",
                &task_metadata,
                JsonMap::from_iter([(
                    \"reason\".to_string(),
                    JsonValue::String(\"response_channel_closed\".to_string()),
                )]),
            );
            return;
        };
        if let Err(e) = prefill_task(
            next,
            formatter,
            tokenizer,
            messages,
            response_text,
            task_metadata.clone(),
        )
        .await
        {
            emit_spec_prefill_event(
                \"worker.spec_prefill.prefill_failed\",
                &task_metadata,
                JsonMap::from_iter([(
                    \"error\".to_string(),
                    JsonValue::String(e.to_string()),
                )]),
            );
            tracing::warn!(error = %e, \"Speculative prefill failed\");
        }
    });

    let mut accumulated_text = String::new();
    let mut prefill_tx = Some(tx);
    let map_metadata = metadata.clone();
    Box::pin(stream.map(move |item| {
"""
    if old in text and "worker.spec_prefill.wrap_checked" not in text:
        text = text.replace(old, new, 1)

    old = """                if choice.finish_reason.is_some()
                    && let Some(tx) = prefill_tx.take()
                {
                    let _ = tx.send(accumulated_text.clone());
                }
"""
    new = """                if choice.finish_reason.is_some()
                    && let Some(tx) = prefill_tx.take()
                {
                    emit_spec_prefill_event(
                        \"worker.spec_prefill.response_complete\",
                        &map_metadata,
                        JsonMap::from_iter([(
                            \"response_chars\".to_string(),
                            JsonValue::from(accumulated_text.chars().count() as u64),
                        )]),
                    );
                    let _ = tx.send(accumulated_text.clone());
                }
"""
    if old in text and "worker.spec_prefill.response_complete" not in text:
        text = text.replace(old, new, 1)
    return text


def ensure_prefill_task_instrumentation(text: str, path: Path) -> str:
    old_sig = """async fn prefill_task(
    next: Arc<
        dyn AsyncEngine<SingleIn<PreprocessedRequest>, ManyOut<Annotated<BackendOutput>>, Error>,
    >,
    formatter: Arc<dyn OAIPromptFormatter>,
    tokenizer: Arc<dyn Tokenizer>,
    original_messages: Vec<ChatCompletionRequestMessage>,
    response_text: String,
) -> Result<()> {
"""
    new_sig = """async fn prefill_task(
    next: Arc<
        dyn AsyncEngine<SingleIn<PreprocessedRequest>, ManyOut<Annotated<BackendOutput>>, Error>,
    >,
    formatter: Arc<dyn OAIPromptFormatter>,
    tokenizer: Arc<dyn Tokenizer>,
    original_messages: Vec<ChatCompletionRequestMessage>,
    response_text: String,
    metadata: SpeculativePrefillMetadata,
) -> Result<()> {
"""
    if old_sig in text and "metadata: SpeculativePrefillMetadata" not in text:
        text = text.replace(old_sig, new_sig, 1)

    old = """    let formatted_prompt = formatter.render(&prefill_request)?;
    let encoding = tokenizer.encode(&formatted_prompt)?;
    let token_ids = encoding.token_ids().to_vec();

    tracing::info!(
        num_tokens = token_ids.len(),
        \"Speculative prefill: sending next-turn prefix\"
    );
"""
    new = """    let formatted_prompt = formatter.render(&prefill_request)?;
    let encoding = tokenizer.encode(&formatted_prompt)?;
    let token_ids = encoding.token_ids().to_vec();
    let token_count = token_ids.len();
    let prefill_request_id = metadata
        .request_id
        .as_ref()
        .map(|request_id| format!(\"{request_id}::spec_prefill\"))
        .unwrap_or_else(|| format!(\"spec_prefill::{}\", uuid::Uuid::new_v4()));

    tracing::info!(
        num_tokens = token_count,
        \"Speculative prefill: sending next-turn prefix\"
    );
    emit_spec_prefill_event(
        \"worker.spec_prefill.prefill_rendered\",
        &metadata,
        JsonMap::from_iter([
            (
                \"prefill_request_id\".to_string(),
                JsonValue::String(prefill_request_id.clone()),
            ),
            (
                \"prefill_prompt_tokens\".to_string(),
                JsonValue::from(token_count as u64),
            ),
        ]),
    );
"""
    if old in text and "worker.spec_prefill.prefill_rendered" not in text:
        text = text.replace(old, new, 1)

    old = """    let context = PipelineContext::with_id(preprocessed, uuid::Uuid::new_v4().to_string());
    // Drain the stream so the KV router's RequestGuard runs its full lifecycle
    // (mark_prefill_completed, block tracking, free) instead of relying on drop.
    if let Ok(mut stream) = next.generate(context).await {
        while stream.next().await.is_some() {}
    }
"""
    new = """    let context = PipelineContext::with_id(preprocessed, prefill_request_id.clone());
    emit_spec_prefill_event(
        \"worker.spec_prefill.prefill_sent\",
        &metadata,
        JsonMap::from_iter([
            (
                \"prefill_request_id\".to_string(),
                JsonValue::String(prefill_request_id.clone()),
            ),
            (
                \"prefill_prompt_tokens\".to_string(),
                JsonValue::from(token_count as u64),
            ),
        ]),
    );
    // Drain the stream so the KV router's RequestGuard runs its full lifecycle
    // (mark_prefill_completed, block tracking, free) instead of relying on drop.
    let mut stream = next.generate(context).await?;
    while stream.next().await.is_some() {}
    emit_spec_prefill_event(
        \"worker.spec_prefill.prefill_completed\",
        &metadata,
        JsonMap::from_iter([(
            \"prefill_request_id\".to_string(),
            JsonValue::String(prefill_request_id),
        )]),
    );
"""
    if old in text and "worker.spec_prefill.prefill_sent" not in text:
        text = text.replace(old, new, 1)

    return text


def repair_speculative_prefill() -> None:
    path = SOURCE_DIR / "lib/llm/src/preprocessor/speculative_prefill.rs"
    text = path.read_text()
    text = ensure_imports(text, path)
    text = ensure_helper_block(text, path)
    text = ensure_wrap_instrumentation(text, path)
    text = ensure_prefill_task_instrumentation(text, path)
    write_if_changed(path, text)


def main() -> None:
    repair_speculative_prefill()
    print("Speculative-prefill source repair complete.")


if __name__ == "__main__":
    main()
