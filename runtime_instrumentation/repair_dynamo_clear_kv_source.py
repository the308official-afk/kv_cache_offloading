#!/usr/bin/env python3
"""Repair Dynamo source so precise runtimes expose clear_kv_blocks end to end.

This keeps the fix small and idempotent:
- export the frontend `clear_kv_blocks` route module
- merge the frontend `/clear_kv_blocks` route into the live HTTP router
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


def repair_http_service_v2() -> None:
    path = SOURCE_DIR / "lib/llm/src/http/service/service_v2.rs"
    text = path.read_text()

    route_line = "            super::clear_kv_blocks::clear_kv_blocks_router(state.clone(), None),\n"
    if route_line not in text:
        anchor = "            super::busy_threshold::busy_threshold_router(state.clone(), None),\n"
        if anchor not in text:
            raise SystemExit(f"Could not find busy_threshold router anchor in {path}")
        text = text.replace(anchor, anchor + route_line, 1)

    write_if_changed(path, text)


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
    repair_http_service_module()
    repair_http_service_v2()
    repair_init_llm()
    repair_handler_base()
    print("Dynamo clear_kv_blocks source repair complete.")


if __name__ == "__main__":
    main()
