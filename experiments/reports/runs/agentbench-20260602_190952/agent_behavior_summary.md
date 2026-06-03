# Agent Behavior Summary: agentbench-20260602_190952

## Tool Results

| Run | Repo | Runtime | Execution subrequests | Tool calls | Tools used | Patch |
| --- | --- | --- | ---: | ---: | --- | ---: |
| 190952 | qutebrowser | upstream | 3 | 5 | read_file, write_todos | 0 bytes |

## Phase Results

| Phase | Requests | Worker subrequests | Tool calls | Tools used | TTFT avg ms | Cache hit | Cached max | H2D KV MB | D2H KV MB |
| --- | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: | ---: |
| planning | 1 | 0 | 0 | none | n/a | True | 8640 | 0.000 | 0.000 |
| execution | 3 | 0 | 0 | none | n/a | True | 8704 | 0.000 | 0.000 |
| patch_generation | 1 | 0 | 3 | read_file, write_todos | n/a | True | 11328 | 0.000 | 0.000 |
| review | 1 | 0 | 2 | read_file, write_todos | n/a | True | 10560 | 0.000 | 0.000 |

## Notes

- Exact tool-call arguments and command strings: `agent_tool_calls.md`
- Tool source: `step_results.tool_progress`
- Execution loop steps: `0`
- Patch nonempty: `False`
- Git diff nonempty: `False`
