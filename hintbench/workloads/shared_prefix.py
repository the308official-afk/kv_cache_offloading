#!/usr/bin/env python3

"""Generate a simple shared-prefix multi-turn workload."""

from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import asdict, dataclass


DEFAULT_SYSTEM_PROMPT = (
    "You are a careful assistant. Reuse prior context when possible and answer concisely."
)


@dataclass
class WorkloadRequest:
    request_id: str
    prompt_id: str
    workload_name: str
    shared_prefix_group: str
    turn_index: int
    messages: list[dict[str, str]]
    hint_payload: dict


def build_requests(
    num_conversations: int,
    turns_per_conversation: int,
    *,
    system_prompt: str,
    shared_prefix_group: str,
    hint_defaults: dict,
) -> list[WorkloadRequest]:
    requests: list[WorkloadRequest] = []
    workload_name = "shared_prefix"

    for conv_idx in range(num_conversations):
        topic = f"topic-{conv_idx}"
        user_seed = (
            f"We are discussing {topic}. Keep terminology consistent across turns."
        )
        prior_user_messages: list[str] = []

        for turn_idx in range(turns_per_conversation):
            turn_prompt = (
                f"{user_seed} Turn {turn_idx + 1}: summarize the next step in one short paragraph."
            )
            prior_user_messages.append(turn_prompt)

            messages = [{"role": "system", "content": system_prompt}]
            for idx, content in enumerate(prior_user_messages):
                messages.append({"role": "user", "content": content})
                if idx < len(prior_user_messages) - 1:
                    messages.append(
                        {
                            "role": "assistant",
                            "content": f"A placeholder assistant reply for replay turn {idx + 1}.",
                        }
                    )

            requests.append(
                WorkloadRequest(
                    request_id=str(uuid.uuid4()),
                    prompt_id=f"{topic}-turn-{turn_idx + 1}",
                    workload_name=workload_name,
                    shared_prefix_group=shared_prefix_group,
                    turn_index=turn_idx + 1,
                    messages=messages,
                    hint_payload=dict(hint_defaults),
                )
            )

    return requests


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-conversations", type=int, default=4)
    parser.add_argument("--turns-per-conversation", type=int, default=3)
    parser.add_argument("--system-prompt", default=DEFAULT_SYSTEM_PROMPT)
    parser.add_argument("--shared-prefix-group", default="group-a")
    parser.add_argument(
        "--hint-defaults-json",
        default='{"priority": 5, "reuse_likelihood": 0.9, "agent_phase": "execution", "expected_output_tokens": 128}',
    )
    args = parser.parse_args()

    hint_defaults = json.loads(args.hint_defaults_json)

    for item in build_requests(
        args.num_conversations,
        args.turns_per_conversation,
        system_prompt=args.system_prompt,
        shared_prefix_group=args.shared_prefix_group,
        hint_defaults=hint_defaults,
    ):
        print(json.dumps(asdict(item), ensure_ascii=True))


if __name__ == "__main__":
    main()
