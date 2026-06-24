#!/usr/bin/env python3
"""Repair Dynamo source logging so worker events expose hint proof fields.

This is intentionally small and idempotent. Use it when the broader runtime JSON
patch is already partly present, but the source still logs only `agent_hints`
instead of `agent_hints_source`, `agent_hints_keys`, and `hint_probe_id`.
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = Path(os.environ.get("SOURCE_DIR", ROOT / "upstream" / "dynamo"))

RUNTIME_LOGGING_TEMPLATE = textwrap.dedent(
    '''\
    """Helpers for opt-in structured runtime JSON logging."""

    from __future__ import annotations

    import json
    import logging
    import os
    from typing import Any

    _RUNTIME_JSON_ENV = "DYN_RUNTIME_JSON_LOGS"
    _RUNTIME_JSON_PREFIX = "[RUNTIME_JSON]"
    _OBSERVABILITY_KEY = "runtime_observability"


    def _maybe_register_transfer_runtime_event(event: dict[str, Any]) -> None:
        try:
            from sglang.srt.mem_cache.transfer_logging import register_runtime_event_metadata
        except Exception:
            return

        try:
            register_runtime_event_metadata(event)
        except Exception:
            return


    def runtime_json_logs_enabled() -> bool:
        return os.environ.get(_RUNTIME_JSON_ENV, "").lower() not in ("", "0", "false")


    def _sanitize(value: Any) -> Any:
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, dict):
            sanitized: dict[str, Any] = {}
            for key, item in value.items():
                if key is None:
                    continue
                sanitized[str(key)] = _sanitize(item)
            return sanitized
        if isinstance(value, (list, tuple, set)):
            return [_sanitize(item) for item in value]

        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            return _sanitize(model_dump())

        tolist = getattr(value, "tolist", None)
        if callable(tolist):
            try:
                return _sanitize(tolist())
            except Exception:
                pass

        return str(value)


    def extract_runtime_observability(request: dict[str, Any]) -> dict[str, Any]:
        extra_args = request.get("extra_args")
        if not isinstance(extra_args, dict):
            return {}
        runtime_observability = extra_args.get(_OBSERVABILITY_KEY)
        if not isinstance(runtime_observability, dict):
            return {}
        return _sanitize(runtime_observability)


    def extract_request_context(request: dict[str, Any]) -> dict[str, Any] | None:
        nvext = request.get("nvext")
        if isinstance(nvext, dict):
            request_context = nvext.get("request_context")
            if isinstance(request_context, dict):
                return _sanitize(request_context)

        runtime_observability = extract_runtime_observability(request)
        request_context = runtime_observability.get("request_context")
        if isinstance(request_context, dict):
            return _sanitize(request_context)

        nested_nvext = runtime_observability.get("nvext")
        if isinstance(nested_nvext, dict):
            request_context = nested_nvext.get("request_context")
            if isinstance(request_context, dict):
                return _sanitize(request_context)

        return None


    def extract_agent_hints_with_source(
        request: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, str]:
        nvext = request.get("nvext")
        if isinstance(nvext, dict):
            agent_hints = nvext.get("agent_hints")
            if isinstance(agent_hints, dict):
                return _sanitize(agent_hints), "nvext.agent_hints"

        runtime_observability = extract_runtime_observability(request)
        agent_hints = runtime_observability.get("agent_hints")
        if isinstance(agent_hints, dict):
            return _sanitize(agent_hints), "runtime_observability.agent_hints"

        nested_nvext = runtime_observability.get("nvext")
        if isinstance(nested_nvext, dict):
            agent_hints = nested_nvext.get("agent_hints")
            if isinstance(agent_hints, dict):
                return _sanitize(agent_hints), "runtime_observability.nvext.agent_hints"

        return None, "missing"


    def extract_agent_hints(request: dict[str, Any]) -> dict[str, Any] | None:
        agent_hints, _source = extract_agent_hints_with_source(request)
        return agent_hints


    def extract_cache_control_with_source(
        request: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, str]:
        nvext = request.get("nvext")
        if isinstance(nvext, dict):
            cache_control = nvext.get("cache_control")
            if isinstance(cache_control, dict):
                return _sanitize(cache_control), "nvext.cache_control"

        runtime_observability = extract_runtime_observability(request)
        cache_control = runtime_observability.get("cache_control")
        if isinstance(cache_control, dict):
            return _sanitize(cache_control), "runtime_observability.cache_control"

        nested_nvext = runtime_observability.get("nvext")
        if isinstance(nested_nvext, dict):
            cache_control = nested_nvext.get("cache_control")
            if isinstance(cache_control, dict):
                return _sanitize(cache_control), "runtime_observability.nvext.cache_control"

        return None, "missing"


    def extract_cache_control(request: dict[str, Any]) -> dict[str, Any] | None:
        cache_control, _source = extract_cache_control_with_source(request)
        return cache_control


    def agent_hint_log_fields(request: dict[str, Any]) -> dict[str, Any]:
        agent_hints, source = extract_agent_hints_with_source(request)
        cache_control, cache_control_source = extract_cache_control_with_source(request)
        if not isinstance(agent_hints, dict):
            return {
                "agent_hints": None,
                "agent_hints_source": source,
                "agent_hints_keys": [],
                "hint_probe_id": None,
                "cache_control": cache_control,
                "cache_control_source": cache_control_source,
                "cache_control_type": cache_control.get("type") if isinstance(cache_control, dict) else None,
                "cache_control_ttl": cache_control.get("ttl") if isinstance(cache_control, dict) else None,
            }
        return {
            "agent_hints": agent_hints,
            "agent_hints_source": source,
            "agent_hints_keys": sorted(str(key) for key in agent_hints),
            "hint_probe_id": agent_hints.get("hint_probe_id"),
            "cache_control": cache_control,
            "cache_control_source": cache_control_source,
            "cache_control_type": cache_control.get("type") if isinstance(cache_control, dict) else None,
            "cache_control_ttl": cache_control.get("ttl") if isinstance(cache_control, dict) else None,
        }


    def preferred_request_id(request: dict[str, Any], fallback: str | None = None) -> str | None:
        request_context = extract_request_context(request)
        if isinstance(request_context, dict):
            request_id = request_context.get("request_id")
            if isinstance(request_id, str) and request_id:
                return request_id

        runtime_observability = extract_runtime_observability(request)
        runtime_request_id = runtime_observability.get("runtime_request_id")
        if isinstance(runtime_request_id, str) and runtime_request_id:
            return runtime_request_id

        frontend_request_id = runtime_observability.get("frontend_request_id")
        if isinstance(frontend_request_id, str) and frontend_request_id:
            return frontend_request_id

        return fallback


    def build_runtime_observability_extra_args(
        request: dict[str, Any],
        frontend_request_id: str,
        runtime_request_id: str,
    ) -> dict[str, Any] | None:
        base_extra_args = request.get("extra_args")
        extra_args = _sanitize(base_extra_args) if isinstance(base_extra_args, dict) else {}

        runtime_observability: dict[str, Any] = {
            "frontend_request_id": frontend_request_id,
            "runtime_request_id": runtime_request_id,
        }

        request_context = extract_request_context(request)
        if request_context:
            runtime_observability["request_context"] = request_context

        agent_hints, agent_hints_source = extract_agent_hints_with_source(request)
        if agent_hints:
            runtime_observability["agent_hints"] = agent_hints
            runtime_observability["agent_hints_source"] = agent_hints_source
            runtime_observability["agent_hints_keys"] = sorted(str(key) for key in agent_hints)
            runtime_observability["hint_probe_id"] = agent_hints.get("hint_probe_id")

        cache_control, cache_control_source = extract_cache_control_with_source(request)
        if cache_control:
            runtime_observability["cache_control"] = cache_control
            runtime_observability["cache_control_source"] = cache_control_source

        if request_context or agent_hints or cache_control:
            runtime_observability["nvext"] = {}
            if request_context:
                runtime_observability["nvext"]["request_context"] = request_context
            if agent_hints:
                runtime_observability["nvext"]["agent_hints"] = agent_hints
            if cache_control:
                runtime_observability["nvext"]["cache_control"] = cache_control

        extra_args[_OBSERVABILITY_KEY] = runtime_observability
        return extra_args


    def emit_runtime_event(
        logger: logging.Logger,
        event_type: str,
        component: str,
        **payload: Any,
    ) -> None:
        if not runtime_json_logs_enabled():
            return

        event: dict[str, Any] = {
            "event_type": event_type,
            "component": component,
        }
        for key, value in payload.items():
            event[key] = _sanitize(value)

        _maybe_register_transfer_runtime_event(event)

        logger.info(
            "%s %s",
            _RUNTIME_JSON_PREFIX,
            json.dumps(event, sort_keys=True, separators=(",", ":")),
        )
    '''
)


def write_if_changed(path: Path, text: str) -> None:
    old = path.read_text()
    if old == text:
        print(f"unchanged: {path}")
        return
    path.write_text(text)
    print(f"updated: {path}")


def replace_method_block(text: str, method_name: str, replacement: str) -> str:
    marker = f"    async def {method_name}("
    start = text.find(marker)
    if start == -1:
        raise SystemExit(f"Could not find method {method_name}")

    next_method = text.find("\n    async def ", start + len(marker))
    if next_method == -1:
        next_method = text.find("\nclass ", start + len(marker))
    if next_method == -1:
        next_method = len(text)

    return text[:start] + textwrap.indent(textwrap.dedent(replacement).strip("\n") + "\n", "    ") + text[next_method:]


def repair_runtime_logging() -> None:
    path = SOURCE_DIR / "components/src/dynamo/common/runtime_logging.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    if existed and path.read_text() == RUNTIME_LOGGING_TEMPLATE:
        print(f"unchanged: {path}")
        return
    path.write_text(RUNTIME_LOGGING_TEMPLATE)
    print(f"{'updated' if existed else 'created'}: {path}")


def repair_handler(path: Path, helper_name: str) -> None:
    text = path.read_text()

    if helper_name == "_decode_request_payload":
        old_import = """from dynamo._core import Context
from dynamo.common.constants import DisaggregationMode
"""
        new_import = """from dynamo._core import Context
from dynamo.common.constants import DisaggregationMode
from dynamo.common.runtime_logging import (
    agent_hint_log_fields,
    emit_runtime_event,
    extract_request_context,
    preferred_request_id,
)
"""
        if "from dynamo.common.runtime_logging import (" not in text:
            if old_import not in text:
                raise SystemExit(f"Could not patch runtime logging imports in {path}")
            text = text.replace(old_import, new_import, 1)

        helper_block = '''

def _decode_request_payload(
    request: Dict[str, Any],
    runtime_context_id: str,
) -> Dict[str, Any]:
    request_context = extract_request_context(request)
    external_request_id = preferred_request_id(
        request, fallback=runtime_context_id
    ) or runtime_context_id
    return {
        "external_request_id": external_request_id,
        "runtime_context_id": runtime_context_id,
        "request_context": request_context,
        **agent_hint_log_fields(request),
    }
'''
        anchor = '_TOP_LOGPROBS_UNSUPPORTED_MSG = (\n'
        if "_decode_request_payload(" not in text:
            end_marker = ')\n\n\ndef _top_logprobs_allowed()'
            if end_marker not in text:
                raise SystemExit(f"Could not insert decode payload helper in {path}")
            text = text.replace(end_marker, ')\n' + helper_block + '\n\ndef _top_logprobs_allowed()', 1)

        normalize_helper = '''
def _normalize_output_ids_delta(
    previous_output_ids: list[int],
    current_output_ids: list[int],
) -> tuple[list[int], list[int]]:
    """Normalize cumulative SGLang ``output_ids`` into per-chunk deltas."""
    if not current_output_ids:
        return [], previous_output_ids

    if not previous_output_ids:
        return current_output_ids, current_output_ids

    prev_len = len(previous_output_ids)
    current_len = len(current_output_ids)

    if current_len >= prev_len and current_output_ids[:prev_len] == previous_output_ids:
        return current_output_ids[prev_len:], current_output_ids

    if current_len < prev_len and previous_output_ids[:current_len] == current_output_ids:
        return current_output_ids, current_output_ids

    return current_output_ids, previous_output_ids + current_output_ids
'''
        if "def _normalize_output_ids_delta(" not in text:
            end_marker = "\n\ndef _openai_stop_sampling_params(request: Dict[str, Any]) -> Dict[str, Any]:"
            if end_marker not in text:
                raise SystemExit(f"Could not insert output-id normalization helper in {path}")
            text = text.replace(end_marker, "\n\n" + normalize_helper + end_marker, 1)

        old_generate = '''        logging.debug(f"New Request ID: {context.id()}")
        trace_id = context.trace_id
'''
        new_generate = '''        runtime_context_id = context.id()
        logging.debug(f"New Request ID: {runtime_context_id}")
        emit_runtime_event(
            logging.getLogger(__name__),
            "worker.decode.request_received",
            "worker.decode",
            **_decode_request_payload(request, runtime_context_id),
            model=self.config.server_args.served_model_name,
            serving_mode=str(self.serving_mode),
        )
        trace_id = context.trace_id
'''
        if 'worker.decode.request_received' not in text:
            if old_generate not in text:
                raise SystemExit(f"Could not patch decode generate() runtime event in {path}")
            text = text.replace(old_generate, new_generate, 1)

        old_token_call = '''                async for out in self._process_token_stream(
                    decode,
                    context,
                    return_tokens_as_token_ids,
                    user_stop_token_ids=user_stop_token_ids,
                ):
'''
        new_token_call = '''                async for out in self._process_token_stream(
                    decode,
                    context,
                    request,
                    return_tokens_as_token_ids,
                    user_stop_token_ids=user_stop_token_ids,
                ):
'''
        if old_token_call in text:
            text = text.replace(old_token_call, new_token_call)

        old_agg_call = '''                async for out in self._process_token_stream(
                    agg,
                    context,
                    return_tokens_as_token_ids,
                    user_stop_token_ids=user_stop_token_ids,
                ):
'''
        new_agg_call = '''                async for out in self._process_token_stream(
                    agg,
                    context,
                    request,
                    return_tokens_as_token_ids,
                    user_stop_token_ids=user_stop_token_ids,
                ):
'''
        if old_agg_call in text:
            text = text.replace(old_agg_call, new_agg_call)

        token_stream_replacement = '''
async def _process_token_stream(
    self,
    stream_source: AsyncGenerator[Dict[str, Any], None],
    context: Context,
    request: Dict[str, Any],
    return_tokens_as_token_ids: bool = False,
    user_stop_token_ids: set[int] | None = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Process token-based stream output.

    With stream_output=True (enforced by Dynamo), SGLang sends disjoint segments
    containing only new tokens since the last output. We pass these through directly.
    """
    request_id_future: asyncio.Future[str] = asyncio.Future()
    output_logprobs_per_choice: dict[int, int] = {}
    output_ids_per_choice: dict[int, list[int]] = {}
    attach_logged = False
    async with self._cancellation_monitor(request_id_future, context):
        async for res in stream_source:
            if not request_id_future.done():
                meta_info = res.get("meta_info", {})
                sglang_request_id = meta_info.get("id")
                if sglang_request_id:
                    request_id_future.set_result(sglang_request_id)
                    logging.debug(f"New SGLang Request ID: {sglang_request_id}")
                    if not attach_logged:
                        emit_runtime_event(
                            logging.getLogger(__name__),
                            "worker.decode.request_attached",
                            "worker.decode",
                            sglang_request_id=sglang_request_id,
                            model=self.config.server_args.served_model_name,
                            **_decode_request_payload(request, context.id()),
                        )
                        attach_logged = True

            output_idx = res.get("index") or 0
            out: dict[str, Any] = {"index": output_idx}
            finish_reason = res["meta_info"]["finish_reason"]
            if finish_reason:
                out["finish_reason"] = normalize_finish_reason(finish_reason["type"])
                stop_reason = _extract_sglang_stop_reason(
                    finish_reason, user_stop_token_ids
                )
                if stop_reason is not None:
                    out["stop_reason"] = stop_reason

            raw_output_ids = res.get("output_ids", [])
            output_ids, next_output_ids = _normalize_output_ids_delta(
                output_ids_per_choice.get(output_idx, []),
                raw_output_ids,
            )
            if raw_output_ids:
                output_ids_per_choice[output_idx] = next_output_ids
            if not output_ids and not finish_reason:
                if context.is_stopped():
                    break
                continue

            out["token_ids"] = output_ids

            (
                log_probs,
                top_logprobs,
                next_logprobs_total,
            ) = self._extract_logprobs(
                res["meta_info"],
                output_logprobs_per_choice.get(output_idx, 0),
                return_tokens_as_token_ids=return_tokens_as_token_ids,
            )
            output_logprobs_per_choice[output_idx] = next_logprobs_total
            if log_probs is not None:
                out["log_probs"] = log_probs
            if top_logprobs is not None:
                out["top_logprobs"] = top_logprobs

            routed_experts = res["meta_info"].get("routed_experts")
            if routed_experts is not None:
                routed_experts = pybase64.b64encode(
                    routed_experts.numpy().tobytes()
                ).decode("utf-8")
                out["disaggregated_params"] = {"routed_experts": routed_experts}
            if finish_reason:
                input_tokens = res["meta_info"]["prompt_tokens"]
                completion_tokens = res["meta_info"]["completion_tokens"]
                cached_tokens = res["meta_info"]["cached_tokens"]
                prefill_prompt_tokens_details = None
                if cached_tokens is not None and cached_tokens > 0:
                    prefill_prompt_tokens_details = {"cached_tokens": cached_tokens}
                out["completion_usage"] = {
                    "prompt_tokens": input_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": input_tokens + completion_tokens,
                    "prompt_tokens_details": prefill_prompt_tokens_details,
                }
                emit_runtime_event(
                    logging.getLogger(__name__),
                    "worker.decode.request_completed",
                    "worker.decode",
                    sglang_request_id=res["meta_info"].get("id"),
                    finish_reason=out.get("finish_reason"),
                    stop_reason=out.get("stop_reason"),
                    completion_usage=out["completion_usage"],
                    model=self.config.server_args.served_model_name,
                    serving_mode=str(self.serving_mode),
                    **_decode_request_payload(request, context.id()),
                )
            if not context.is_stopped():
                yield out
'''
        token_fn_start = text.find("    async def _process_token_stream(")
        token_fn_end = text.find("\n    async def _process_text_stream(", token_fn_start)
        if token_fn_start == -1 or token_fn_end == -1:
            raise SystemExit(f"Could not locate decode token/text stream functions in {path}")
        token_fn = text[token_fn_start:token_fn_end]
        if "request: Dict[str, Any]," not in token_fn or "attach_logged = False" not in token_fn or "_normalize_output_ids_delta(" not in token_fn:
            text = replace_method_block(text, "_process_token_stream", token_stream_replacement)

        if 'worker.decode.request_attached' not in text:
            attach_old = '''                        request_id_future.set_result(sglang_request_id)
                        logging.debug(f"New SGLang Request ID: {sglang_request_id}")

                # Check cancellation before yielding to allow proper cleanup.
'''
            attach_new = '''                        request_id_future.set_result(sglang_request_id)
                        logging.debug(f"New SGLang Request ID: {sglang_request_id}")
                        if not attach_logged:
                            emit_runtime_event(
                                logging.getLogger(__name__),
                                "worker.decode.request_attached",
                                "worker.decode",
                                sglang_request_id=sglang_request_id,
                                model=self.config.server_args.served_model_name,
                                **_decode_request_payload(request, context.id()),
                            )
                            attach_logged = True

                # Check cancellation before yielding to allow proper cleanup.
'''
            replaced = text.replace(attach_old, attach_new)
            if replaced == text:
                raise SystemExit(f"Could not patch decode attached runtime event in {path}")
            text = replaced

        if 'worker.decode.request_completed' not in text:
            complete_old = '''                    out["completion_usage"] = {
                        "prompt_tokens": input_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": input_tokens + completion_tokens,
                        "prompt_tokens_details": prefill_prompt_tokens_details,
                    }
                if not context.is_stopped():
                    yield out
'''
            complete_new = '''                    out["completion_usage"] = {
                        "prompt_tokens": input_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": input_tokens + completion_tokens,
                        "prompt_tokens_details": prefill_prompt_tokens_details,
                    }
                    emit_runtime_event(
                        logging.getLogger(__name__),
                        "worker.decode.request_completed",
                        "worker.decode",
                        sglang_request_id=res["meta_info"].get("id"),
                        finish_reason=out.get("finish_reason"),
                        stop_reason=out.get("stop_reason"),
                        completion_usage=out["completion_usage"],
                        model=self.config.server_args.served_model_name,
                        serving_mode=str(self.serving_mode),
                        **_decode_request_payload(request, context.id()),
                    )
                if not context.is_stopped():
                    yield out
'''
            replaced = text.replace(complete_old, complete_new)
            if replaced == text:
                text_chunk_old = '''                    if cached_tokens is not None and cached_tokens > 0:
                        completion_usage["prompt_tokens_details"] = {
                            "cached_tokens": cached_tokens
                        }
                if not context.is_stopped():
                    yield response
'''
                text_chunk_new = '''                    if cached_tokens is not None and cached_tokens > 0:
                        completion_usage["prompt_tokens_details"] = {
                            "cached_tokens": cached_tokens
                        }
                    emit_runtime_event(
                        logging.getLogger(__name__),
                        "worker.decode.request_completed",
                        "worker.decode",
                        sglang_request_id=meta_info.get("id"),
                        finish_reason=finish_reason_type,
                        stop_reason=stop_reason,
                        completion_usage=completion_usage,
                        model=self.config.server_args.served_model_name,
                        serving_mode=str(self.serving_mode),
                        **_decode_request_payload(request, context.id()),
                    )
                if not context.is_stopped():
                    yield response
'''
                replaced = text.replace(text_chunk_old, text_chunk_new)
            if replaced == text:
                raise SystemExit(f"Could not patch decode completed runtime event in {path}")
            text = replaced

    elif helper_name == "_prefill_request_payload":
        old_import = """from dynamo._core import Context
from dynamo.common.utils.otel_tracing import build_trace_headers
"""
        new_import = """from dynamo._core import Context
from dynamo.common.runtime_logging import (
    agent_hint_log_fields,
    emit_runtime_event,
    extract_request_context,
    preferred_request_id,
)
from dynamo.common.utils.otel_tracing import build_trace_headers
"""
        if "from dynamo.common.runtime_logging import (" not in text:
            if old_import not in text:
                raise SystemExit(f"Could not patch runtime logging imports in {path}")
            text = text.replace(old_import, new_import, 1)

        helper_block = '''

def _prefill_request_payload(
    request: Dict[str, Any],
    runtime_context_id: str,
) -> Dict[str, Any]:
    request_context = extract_request_context(request)
    external_request_id = preferred_request_id(
        request, fallback=runtime_context_id
    ) or runtime_context_id
    return {
        "external_request_id": external_request_id,
        "runtime_context_id": runtime_context_id,
        "request_context": request_context,
        **agent_hint_log_fields(request),
    }
'''
        if "_prefill_request_payload(" not in text:
            end_marker = "_DP_RANK_UNSET = 2**32 - 1\n"
            if end_marker not in text:
                raise SystemExit(f"Could not insert prefill payload helper in {path}")
            text = text.replace(end_marker, end_marker + helper_block + "\n", 1)

        old_task_call = "        task = asyncio.create_task(self._consume_results(results, context))\n"
        new_task_call = "        task = asyncio.create_task(self._consume_results(results, context, inner_request))\n"
        if old_task_call in text and new_task_call not in text:
            text = text.replace(old_task_call, new_task_call, 1)

        old_signature = '''    async def _consume_results(
        self, results: AsyncGenerator[Any, None], context: Context
    ) -> None:
'''
        new_signature = '''    async def _consume_results(
        self,
        results: AsyncGenerator[Any, None],
        context: Context,
        request: Dict[str, Any],
    ) -> None:
'''
        if old_signature in text and new_signature not in text:
            text = text.replace(old_signature, new_signature, 1)

        old_generate = '''        logging.debug(f"New Request ID: {context.id()}")
        trace_id = context.trace_id
'''
        new_generate = '''        runtime_context_id = context.id()
        logging.debug(f"New Request ID: {runtime_context_id}")
        trace_id = context.trace_id

        emit_runtime_event(
            logging.getLogger(__name__),
            "worker.prefill.request_received",
            "worker.prefill",
            **_prefill_request_payload(inner_request, runtime_context_id),
            model=self.config.server_args.served_model_name,
            serving_mode="prefill",
        )
'''
        if 'worker.prefill.request_received' not in text:
            # this replacement must happen after inner_request is defined, so we
            # rewrite the old logging/trace block and keep the surrounding request
            # parsing intact.
            if old_generate not in text:
                raise SystemExit(f"Could not patch prefill generate() runtime event in {path}")
            text = text.replace(old_generate, '        runtime_context_id = context.id()\n        logging.debug(f"New Request ID: {runtime_context_id}")\n        trace_id = context.trace_id\n', 1)
            after_request_parse = '''            sampling_params = {
                k: v for k, v in sampling_params.items() if v is not None
            }
'''
            insertion = '''            sampling_params = {
                k: v for k, v in sampling_params.items() if v is not None
            }

        emit_runtime_event(
            logging.getLogger(__name__),
            "worker.prefill.request_received",
            "worker.prefill",
            **_prefill_request_payload(inner_request, runtime_context_id),
            model=self.config.server_args.served_model_name,
            serving_mode="prefill",
        )
'''
            if after_request_parse not in text:
                raise SystemExit(f"Could not place prefill runtime event after request parsing in {path}")
            text = text.replace(after_request_parse, insertion, 1)

        if "        attach_logged = False\n" not in text:
            marker = "        request_id_future: asyncio.Future[str] = asyncio.Future()\n"
            replacement = marker + "        attach_logged = False\n        last_meta_info: Dict[str, Any] | None = None\n"
            if marker not in text:
                raise SystemExit(f"Could not add prefill helper state in {path}")
            text = text.replace(marker, replacement, 1)

        last_meta_marker = '''            async for res in results:
                # Extract SGLang request ID from the first response and set the future
'''
        last_meta_replacement = '''            async for res in results:
                meta_info = res.get("meta_info", {})
                if isinstance(meta_info, dict):
                    last_meta_info = meta_info
                # Extract SGLang request ID from the first response and set the future
'''
        if "last_meta_info = meta_info" not in text:
            if last_meta_marker not in text:
                raise SystemExit(f"Could not add prefill meta_info tracking in {path}")
            text = text.replace(last_meta_marker, last_meta_replacement, 1)

        if 'worker.prefill.request_attached' not in text:
            attach_old = '''                        request_id_future.set_result(sglang_request_id)
                        logging.debug(f"New Prefill Request ID: {sglang_request_id}")

                # Note: No explicit cancellation checks needed here.
'''
            attach_new = '''                        request_id_future.set_result(sglang_request_id)
                        logging.debug(f"New Prefill Request ID: {sglang_request_id}")
                        if not attach_logged:
                            emit_runtime_event(
                                logging.getLogger(__name__),
                                "worker.prefill.request_attached",
                                "worker.prefill",
                                sglang_request_id=sglang_request_id,
                                model=self.config.server_args.served_model_name,
                                **_prefill_request_payload(request, context.id()),
                            )
                            attach_logged = True

                # Note: No explicit cancellation checks needed here.
'''
            replaced = text.replace(attach_old, attach_new)
            if replaced == text:
                raise SystemExit(f"Could not patch prefill attached runtime event in {path}")
            text = replaced

        if 'worker.prefill.request_completed' not in text:
            complete_old = '''            if cached_tokens is not None and cached_tokens > 0:
                completion_usage["prompt_tokens_details"] = {
                    "cached_tokens": cached_tokens
                }
'''
            complete_new = '''            if cached_tokens is not None and cached_tokens > 0:
                completion_usage["prompt_tokens_details"] = {
                    "cached_tokens": cached_tokens
                }
            emit_runtime_event(
                logging.getLogger(__name__),
                "worker.prefill.request_completed",
                "worker.prefill",
                sglang_request_id=last_meta_info.get("id"),
                finish_reason=last_meta_info.get("finish_reason"),
                completion_usage=completion_usage,
                bootstrap_host=self.bootstrap_host,
                bootstrap_port=self.bootstrap_port,
                model=self.config.server_args.served_model_name,
                **_prefill_request_payload(request, context.id()),
            )
'''
            replaced = text.replace(complete_old, complete_new)
            if replaced == text:
                append_marker = '''                # Note: No explicit cancellation checks needed here.
                # When abort_request is called by the cancellation monitor,
                # SGLang will terminate this async generator automatically.
'''
                append_replacement = append_marker + '''
        if last_meta_info:
            prompt_tokens = last_meta_info.get("prompt_tokens")
            completion_tokens = last_meta_info.get("completion_tokens")
            completion_usage: Dict[str, Any] = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": (prompt_tokens or 0) + (completion_tokens or 0),
            }
            cached_tokens = last_meta_info.get("cached_tokens")
            if cached_tokens is not None and cached_tokens > 0:
                completion_usage["prompt_tokens_details"] = {
                    "cached_tokens": cached_tokens
                }
            emit_runtime_event(
                logging.getLogger(__name__),
                "worker.prefill.request_completed",
                "worker.prefill",
                sglang_request_id=last_meta_info.get("id"),
                finish_reason=last_meta_info.get("finish_reason"),
                completion_usage=completion_usage,
                bootstrap_host=self.bootstrap_host,
                bootstrap_port=self.bootstrap_port,
                model=self.config.server_args.served_model_name,
                **_prefill_request_payload(request, context.id()),
            )
'''
                replaced = text.replace(append_marker, append_replacement, 1)
            if replaced == text:
                raise SystemExit(f"Could not patch prefill completed runtime event in {path}")
            text = replaced

    if "agent_hint_log_fields" not in text:
        raise SystemExit(f"Failed to add agent_hint_log_fields to {helper_name}: {path}")

    write_if_changed(path, text)


def main() -> None:
    repair_runtime_logging()
    repair_handler(
        SOURCE_DIR / "components/src/dynamo/sglang/request_handlers/llm/decode_handler.py",
        "_decode_request_payload",
    )
    repair_handler(
        SOURCE_DIR / "components/src/dynamo/sglang/request_handlers/llm/prefill_handler.py",
        "_prefill_request_payload",
    )
    print("Hint-aware worker logging source repair complete.")


if __name__ == "__main__":
    main()
