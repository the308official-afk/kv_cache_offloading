# Misc Debug Notes



```bash
cd ~/kv_cache_offloading

python3 - <<'PY'
import csv
from collections import Counter
from pathlib import Path

p = Path("experiments/reports/latest_swebench_trajectory_prompt_catalog.csv")
rows = list(csv.DictReader(p.open()))
stage_counts = Counter(r.get("stage_name") or r.get("phase") for r in rows)

print("total prompt rows:", len(rows))
print("stage counts:")
for k, v in sorted(stage_counts.items()):
    print(f"  {k}: {v}")
PY

```


```bash
Anticipated Direction	Value	Why There Is Opportunity for Value	Can Hints Power It?
Lifecycle-aware KV management	Very High	Agent KV can be retained while active and removed immediately when the agent or subagent finishes, reducing both recomputation and wasted memory.	Yes. Session identity, parent-session and completion signals can guide retention and cleanup.
Direct tool-call-aware KV prefetch	Very High	Agents often pause during tool calls. Moving KV back to GPU before the tool returns could hide transfer latency and speed up the next reasoning step.	Yes. Future timing or tool-state hints could trigger direct storage-to-GPU prefetch.
Cache-value / semantic awareness	Very High	System prompts and tool definitions are highly reusable, while temporary reasoning and finished-subagent KV may have little value. Treating them differently improves memory efficiency.	Partly. Hints could identify content type or reuse value, but Dynamo and the runtime must enforce block-level policies.
Cross-worker and subagent KV sharing	Very High	Shared prompts could be computed once and reused by multiple workers or subagents, avoiding repeated prefill across the cluster.	Partly. Session and shared-prefix hints help identify related requests, but shared storage, indexing and NIXL perform the actual sharing.
Learned routing and automatic hints	High	Harnesses may not predict output length, reuse or the best worker accurately. Learned policies can improve routing automatically from past performance.	Partly. Hints provide context, but runtime telemetry and an online-learning router make the final prediction.
Explicit latency objectives	High	Actual TTFT and inter-token-latency targets are more useful than a vague urgency score and can guide pool selection and scheduling.	Yes. Dynamo already accepts per-request ttft_target and itl_target router parameters.
Hardware and worker-pool placement	Medium–High	Long-context or latency-sensitive requests may benefit from workers with more HBM, faster interconnects or specialized configurations.	Yes. Routing constraints can require or prefer workers with selected characteristics.
Agent-phase awareness	Potentially High	Planning, tool waiting, synthesis and final-response stages have different latency, compute and cache needs.	Yes, if added. A future phase hint could select different scheduling, retention and prefetch policies.
Expected resume-time awareness	Potentially High	Knowing when an agent will return helps decide whether KV should remain in GPU, move to CPU or be prefetched shortly before reuse.	Yes, if added. A future timing hint could coordinate memory placement and prefetching.
```











```bash
cd ~/kv_cache_offloading

RUN_ID="exp6_prompt_evolution_gh200_1"
grep '^25,' "experiments/reports/batches/${RUN_ID}/task_trace_index.csv" || echo "task 25 not completed; resume should retry it"
```

```bash
Published 3 public Exp 6 report(s) after task 24 (agentbench-20260721_150945) to experiments/charts.
===== Running SWE-bench index 25 =====
Traceback (most recent call last):
  File "/home/central/ojaiyeob/kv_cache_offloading/agentbench/deepagents_swebench_single_host.py", line 5231, in <module>
    main()
  File "/home/central/ojaiyeob/kv_cache_offloading/agentbench/deepagents_swebench_single_host.py", line 4644, in main
    workspace_dir, workspace_metadata = prepare_workspace(
                                        ^^^^^^^^^^^^^^^^^^
  File "/home/central/ojaiyeob/kv_cache_offloading/agentbench/deepagents_swebench_single_host.py", line 4197, in prepare_workspace
    run_command(["git", "checkout", checkout_commit], cwd=shared_repo_source)
  File "/home/central/ojaiyeob/kv_cache_offloading/agentbench/deepagents_swebench_single_host.py", line 1686, in run_command
    return subprocess.run(
           ^^^^^^^^^^^^^^^
  File "/usr/lib/python3.11/subprocess.py", line 569, in run
    raise CalledProcessError(retcode, process.args,
subprocess.CalledProcessError: Command '['git', 'checkout', 'c35133622a7950d2aa96d1db03ad8b96ccd65df9']' returned non-zero exit status 128.
Published 3 public Exp 6 report(s) after task 25 (agentbench-20260721_151210) to experiments/charts.
Run failed: agentbench-20260721_151210
Partial result dir: experiments/raw/agentbench/results/agentbench-20260721_151210
Partial report dir: experiments/reports/runs/agentbench-20260721_151210
Exit status: 1

Index 25 failed; stopping because AGENTBENCH_BATCH_CONTINUE_ON_ERROR=0
Building SWE-bench trajectory prompt catalog from Experiment 6 traces...
Preparing SWE-bench trajectory prompts...
Trace index: experiments/reports/latest_prompt_evolution_trace_index.csv
Catalog ID: swebench_trajectory_prompts_exp6_prompt_evolution_gh200_1
Stages: planning execution patch_generation review
Min prompt chars: 200
Max tasks: 0

SWE-bench trajectory prompt catalog ready.
catalog_id: swebench_trajectory_prompts_exp6_prompt_evolution_gh200_1
trace_index: experiments/reports/latest_prompt_evolution_trace_index.csv
catalog_csv: /home/central/ojaiyeob/kv_cache_offloading/experiments/reports/swebench_trajectory_prompts/swebench_trajectory_prompts_exp6_prompt_evolution_gh200_1/swebench_trajectory_pro    mpt_catalog.csv
catalog_jsonl: /home/central/ojaiyeob/kv_cache_offloading/experiments/reports/swebench_trajectory_prompts/swebench_trajectory_prompts_exp6_prompt_evolution_gh200_1/swebench_trajectory_p    rompt_catalog.jsonl
latest_csv: /home/central/ojaiyeob/kv_cache_offloading/experiments/reports/latest_swebench_trajectory_prompt_catalog.csv
latest_jsonl: /home/central/ojaiyeob/kv_cache_offloading/experiments/reports/latest_swebench_trajectory_prompt_catalog.jsonl
task_count: 25
prompt_count: 93
stage_filter: planning execution patch_generation review
min_prompt_chars: 200

Latest catalog CSV: experiments/reports/latest_swebench_trajectory_prompt_catalog.csv
Latest catalog JSONL: experiments/reports/latest_swebench_trajectory_prompt_catalog.jsonl
Published catalog CSV to: experiments/charts/exp6_swebench_trajectory_prompt_catalog.csv

Prompt evolution batch finished.
Batch dir: experiments/reports/batches/exp6_prompt_evolution_gh200_1
Driver log: experiments/reports/batches/exp6_prompt_evolution_gh200_1/prompt_evolution_batch_driver.log
Smoke log: experiments/reports/batches/exp6_prompt_evolution_gh200_1/prompt_evolution_batch_smoke_test.log
Progress CSV: experiments/reports/batches/exp6_prompt_evolution_gh200_1/progress_overview.csv
Trace index CSV: experiments/reports/batches/exp6_prompt_evolution_gh200_1/task_trace_index.csv
Trace index MD: experiments/reports/batches/exp6_prompt_evolution_gh200_1/task_trace_index.md
Prompt evolution summary: experiments/reports/prompt_evolution_run_overview.csv
Latest trace index CSV: experiments/reports/latest_prompt_evolution_trace_index.csv
Latest trace index MD: experiments/reports/latest_prompt_evolution_trace_index.md
Published readable Exp 6 reports:
  experiments/charts/exp6_prompt_evolution_run_overview.csv
  experiments/charts/exp6_prompt_evolution_task_summary.csv
  experiments/charts/exp6_swebench_trajectory_prompt_catalog.csv


```






For a presentation, I'd keep it to these core capabilities:

LLM orchestration platform for scalable inference.
KV cache-aware routing to maximize cache reuse and reduce recomputation.
Disaggregated serving by coordinating separate prefill and decode workers.
Distributed KV cache management with offloading across GPU, CPU, and storage.
High-performance multi-node communication for efficient data movement between workers.




NVIDIA Dynamo is an orchestration platform for LLM inference. It does not implement the transformer model itself. Instead, it coordinates where requests run, separates prefill and decode, routes requests using KV-cache awareness, manages the KV cache across the memory hierarchy, and moves data efficiently between machines so inference remains fast and scalable.


Here are concise, slide-friendly descriptions for each major component:

API Server – Receives LLM requests and forwards them into Dynamo for processing.
Planner – Continuously optimizes scheduling and resource usage.
Smart Router – Routes requests to the best worker, prioritizing KV cache reuse.
Prefill Worker – Processes the input prompt and builds the initial KV cache.
Decode Worker – Generates output tokens using the existing KV cache.
Distributed KV Cache – Stores and shares KV cache across workers for reuse.
KV Cache Manager – Decides where KV cache should live (GPU, CPU, or object storage).
NIXL (Inference Transfer Engine) – Moves data efficiently between GPUs and nodes.
Event Plane – Monitors system health, performance, and metrics across all components.
Host Memory – Provides larger, slower storage for offloaded KV cache.
Object Storage – Stores long-lived KV cache beyond GPU and CPU memory.
Disaggregated Serving – Separates prefill and decode onto specialized workers for higher efficiency.






```bash
Run	Status	Repo	Model	Steps	Planning	Execution	Exec Size Î”	Patch Gen	Review	Other	Total	Patch
5310	recursion_soft_stop	NodeBB	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	0	0 - none	0 - none		0 - none	0 - none	0 - none	0	0 B
5412	recursion_soft_stop	qutebrowser	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	0	0 - none	0 - none		0 - none	0 - none	0 - none	0	0 B
5455	complete	NodeBB	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	1	39 - edit_file, execute, ls, read_file, write_file, write_todos	21 - execute, grep, ls, read_file, write_todos	-4979	11 - execute, ls, read_file	17 - execute, ls, read_file, write_todos	0 - none	88	4.3 KB
5649	recursion_soft_stop	qutebrowser	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	0	0 - none	0 - none		0 - none	0 - none	0 - none	0	0 B
5732	recursion_soft_stop	ansible	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	0	0 - none	0 - none		0 - none	0 - none	0 - none	0	0 B
5807	recursion_soft_stop	ansible	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	0	0 - none	0 - none		0 - none	0 - none	0 - none	0	0 B
5924	recursion_soft_stop	openlibrary	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	0	0 - none	0 - none		0 - none	0 - none	0 - none	0	0 B
10020	recursion_soft_stop	qutebrowser	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	0	0 - none	0 - none		0 - none	0 - none	0 - none	0	0 B
10112	recursion_soft_stop	teleport	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	0	0 - none	0 - none		0 - none	0 - none	0 - none	0	0 B
10242	recursion_soft_stop	navidrome	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	0	0 - none	0 - none		0 - none	0 - none	0 - none	0	0 B
10315	recursion_soft_stop	openlibrary	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	0	0 - none	0 - none		0 - none	0 - none	0 - none	0	0 B


```

```bash
ojaiyeob@gracehopper:~/kv_cache_offloading$ cd ~/kv_cache_offloading

RUN_DIR="$(ls -td experiments/raw/agentbench/results/agentbench-* | head -1)"
export RUN_DIR

python3 - <<'PY'
import json
import os
from pathlib import Path

run_dir = Path(os.environ["RUN_DIR"])
p = run_dir / "others" / "stage_lifecycle_trace_raw.json"
events = json.loads(p.read_text())

for e in events:
    if e.get("event_kind") != "agent_stream_step":
        continue
    s = e.get("chunk_summary", {})
    msgs = s.get("last_messages", [])
    last = msgs[-1] if msgs else {}
    print(
        e["stage"],
        "step=", e.get("chunk_index"),
        "messages=", s.get("message_count"),
        "last_type=", last.get("type"),
        "tools=", last.get("tool_call_names"),
        "preview=", (last.get("content_preview") or "")[:160].replace("\n", " "),
    )

for e in events:
    if e.get("event_kind") == "agent_stream_error":
        print("\nERROR:", e.get("error_type"), e.get("error"))
        print("last:", e.get("last_chunk_summary"))
PY
execution_agent_stream_step step= 1 messages= 1 last_type= human tools= [] preview= Phase: execution_loop_inspect  Loop state reason: start_with_inspection.  Do not write a plan, markdown code fence, or next-steps-only answer. Use the available
execution_agent_stream_step step= 2 messages= 2 last_type= ai tools= ['ls'] preview= I'll start by inspecting the repository structure to understand the codebase and locate the relevant files mentioned in the issue.
execution_agent_stream_step step= 3 messages= 3 last_type= tool tools= [] preview= ['/.codeclimate.yml', '/.editorconfig', '/.eslintignore', '/.eslintrc', '/.git/', '/.gitattributes', '/.github/', '/.gitignore', '/.husky/', '/.mocharc.yml', '/
execution_agent_stream_step step= 4 messages= 4 last_type= ai tools= ['ls'] preview= Let me explore the src directory to find the database and user modules:
execution_agent_stream_step step= 5 messages= 5 last_type= tool tools= [] preview= ['/src/admin/', '/src/als.js', '/src/analytics.js', '/src/api/', '/src/batch.js', '/src/cache.js', '/src/cache/', '/src/cacheCreate.js', '/src/categories/', '/s
execution_agent_stream_step step= 6 messages= 6 last_type= ai tools= ['ls'] preview= Now let me look at the database directory structure to find the adapters:
execution_agent_stream_step step= 7 messages= 7 last_type= tool tools= [] preview= ['/src/database/cache.js', '/src/database/helpers.js', '/src/database/index.js', '/src/database/mongo.js', '/src/database/mongo/', '/src/database/postgres.js',
execution_agent_stream_step step= 8 messages= 8 last_type= ai tools= ['ls'] preview= Let me check the database adapter files to understand their current structure:
execution_agent_stream_step step= 9 messages= 9 last_type= tool tools= [] preview= ['/src/database/mongo/connection.js', '/src/database/mongo/hash.js', '/src/database/mongo/helpers.js', '/src/database/mongo/list.js', '/src/database/mongo/main.
execution_agent_stream_step step= 10 messages= 10 last_type= ai tools= ['ls'] preview=
execution_agent_stream_step step= 11 messages= 11 last_type= tool tools= [] preview= ['/src/database/postgres/connection.js', '/src/database/postgres/hash.js', '/src/database/postgres/helpers.js', '/src/database/postgres/list.js', '/src/database
execution_agent_stream_step step= 12 messages= 12 last_type= ai tools= ['ls'] preview=
execution_agent_stream_step step= 13 messages= 13 last_type= tool tools= [] preview= ['/src/database/redis/connection.js', '/src/database/redis/hash.js', '/src/database/redis/helpers.js', '/src/database/redis/list.js', '/src/database/redis/main.
execution_agent_stream_step step= 14 messages= 14 last_type= ai tools= ['ls'] preview= Now let me check the user module structure:
execution_agent_stream_step step= 15 messages= 15 last_type= tool tools= [] preview= ['/src/user/admin.js', '/src/user/approval.js', '/src/user/auth.js', '/src/user/bans.js', '/src/user/blocks.js', '/src/user/categories.js', '/src/user/create.js
execution_agent_stream_step step= 16 messages= 16 last_type= ai tools= ['read_file'] preview= Let me first examine the current implementation of the database adapters to understand what's missing:
execution_agent_stream_step step= 17 messages= 17 last_type= tool tools= [] preview=      1     'use strict';      2          3 module.exports = function (module) {      4             const helpers = require('./helpers');      5         module.flushdb = async function (
execution_agent_stream_step step= 18 messages= 18 last_type= ai tools= ['read_file'] preview=
execution_agent_stream_step step= 19 messages= 19 last_type= tool tools= [] preview=      1     'use strict';      2          3 module.exports = function (module) {      4             const helpers = require('./helpers');      5       6         module.flushdb = async fu
execution_agent_stream_step step= 20 messages= 20 last_type= ai tools= ['read_file'] preview=
execution_agent_stream_step step= 21 messages= 21 last_type= tool tools= [] preview=      1     'use strict';      2          3 module.exports = function (module) {      4             const helpers = require('./helpers');      5       6         module.flushdb = async fu
execution_agent_stream_step step= 22 messages= 22 last_type= ai tools= ['read_file'] preview= Now let me check the user email module to understand the current implementation:
execution_agent_stream_step step= 23 messages= 23 last_type= tool tools= [] preview=      1           2 'use strict';      3          4 const nconf = require('nconf');      5  const winston = require('winston');      6         7 const user = require('./in
execution_agent_stream_step step= 24 messages= 24 last_type= ai tools= ['read_file'] preview=
execution_agent_stream_step step= 25 messages= 25 last_type= tool tools= [] preview=    101                     options = {    102                              email: options,    103      };    104                }    105            106         const confirm_code = utils.generateUUID();    107               const confirm_link = `${
execution_agent_stream_step step= 26 messages= 26 last_type= ai tools= ['read_file'] preview=
execution_agent_stream_step step= 27 messages= 27 last_type= tool tools= [] preview=    201             if (oldUid && oldUid !== parseInt(uid, 10)) {    202                    throw new Error('[[error:email-taken]]');    203             }    204            205         const confirmedEmails = await
execution_agent_stream_step step= 28 messages= 28 last_type= ai tools= ['read_file'] preview= Now let me check the user info module to understand how loadUserInfo works:
execution_agent_stream_step step= 29 messages= 29 last_type= tool tools= [] preview=      1     'use strict';      2          3 const _ = require('lodash');      4     const validator = require('validator');      5             6 const db = require('../database')
execution_agent_stream_step step= 30 messages= 30 last_type= ai tools= ['read_file'] preview=
execution_agent_stream_step step= 31 messages= 31 last_type= tool tools= [] preview=    101             async function formatBanMuteData(keys, noReasonLangKey) {    102                    const data = await db.getObjects(keys);    103                   const uids = data.map(d => d.fromUid
execution_agent_stream_step step= 32 messages= 32 last_type= ai tools= ['grep'] preview= Let me search for the loadUserInfo function to understand how it's implemented:
execution_agent_stream_step step= 33 messages= 33 last_type= tool tools= [] preview= /src/controllers/admin/users.js
execution_agent_stream_step step= 34 messages= 34 last_type= ai tools= ['read_file'] preview=
execution_agent_stream_step step= 35 messages= 35 last_type= tool tools= [] preview=      1     'use strict';      2          3 const validator = require('validator');      4        5 const user = require('../../user');      6   const meta = require('../.
execution_agent_stream_step step= 36 messages= 36 last_type= ai tools= ['read_file'] preview=
execution_agent_stream_step step= 37 messages= 37 last_type= tool tools= [] preview=    101         102         await render(req, res, {    103                 users: users.filter(user => user && parseInt(user.uid, 10)),    104                  page: page,    105                      pageCount: Math.max
execution_agent_stream_step step= 38 messages= 38 last_type= ai tools= ['ls'] preview= Now let me check the test files to understand what's expected:
execution_agent_stream_step step= 39 messages= 39 last_type= tool tools= [] preview= ['/test/.eslintrc', '/test/api.js', '/test/authentication.js', '/test/batch.js', '/test/blacklist.js', '/test/build.js', '/test/categories.js', '/test/controlle
execution_agent_stream_step step= 40 messages= 40 last_type= ai tools= ['ls'] preview=
execution_agent_stream_step step= 41 messages= 41 last_type= tool tools= [] preview= ['/test/database/hash.js', '/test/database/keys.js', '/test/database/list.js', '/test/database/sets.js', '/test/database/sorted.js']
execution_agent_stream_step step= 42 messages= 42 last_type= ai tools= ['ls'] preview=
execution_agent_stream_step step= 43 messages= 43 last_type= tool tools= [] preview= ['/test/user/emails.js', '/test/user/reset.js', '/test/user/uploads.js']
execution_agent_stream_step step= 44 messages= 44 last_type= ai tools= ['read_file'] preview= Let me check the database keys test to understand what's expected for mget:
execution_agent_stream_step step= 45 messages= 45 last_type= tool tools= [] preview=      1     'use strict';      2          3       4 const async = require('async');      5  const assert = require('assert');      6     const db = require('../mocks/databas
execution_agent_stream_step step= 46 messages= 46 last_type= ai tools= ['read_file'] preview=
execution_agent_stream_step step= 47 messages= 47 last_type= tool tools= [] preview=    101                     });    102              });    103          104         it('should delete all keys passed in', (done) => {    105                    async.parallel([    106                         function (next) {    107                                        db.
execution_agent_stream_step step= 48 messages= 48 last_type= ai tools= ['read_file'] preview= Now let me check the user emails test to understand the current behavior:
execution_agent_stream_step step= 49 messages= 49 last_type= tool tools= [] preview=      1     'use strict';      2          3 const assert = require('assert');      4        const nconf = require('nconf');      5       const util = require('util');      6          7
execution_agent_stream_step step= 50 messages= 50 last_type= ai tools= ['ls'] preview= Now I'll check the database mock to understand how the database interface works:
execution_agent_stream_step step= 51 messages= 51 last_type= tool tools= [] preview= ['/test/mocks/databasemock.js', '/test/mocks/plugin_modules/']
execution_agent_stream_step step= 52 messages= 52 last_type= ai tools= ['read_file'] preview=
execution_agent_stream_step step= 53 messages= 53 last_type= tool tools= [] preview=      1     'use strict';      2          3 /**      4       * Database Mock - wrapper for database.js, makes system use separate test db, instead of production      5   * AT
execution_agent_stream_step step= 54 messages= 54 last_type= ai tools= ['execute'] preview= Let me now run the tests to see what's currently failing:

ERROR: GraphRecursionError GraphRecursionError('Recursion limit of 80 reached without hitting a stop condition. You can increase the limit by setting the `recursion_limit` config key.\nFor troubleshooting, visit: https://docs.langchain.com/oss/python/langgraph/errors/GRAPH_RECURSION_LIMIT')
last: {'kind': 'state', 'keys': ['files', 'messages'], 'message_count': 54, 'last_messages': [{'type': 'ai', 'name': None, 'tool_call_id': None, 'tool_call_count': 1, 'tool_call_names': ['read_file'], 'content_preview': ''}, {'type': 'tool', 'name': 'read_file', 'tool_call_id': 'call-33fd0a50-fb4b-44ca-8bbc-9eb219a94520', 'tool_call_count': 0, 'tool_call_names': [], 'content_preview': "     1\t'use strict';\n     2\t\n     3\t/**\n     4\t * Database Mock - wrapper for database.js, makes system use separate test db, instead of production\n     5\t * ATTENTION: testing db is flushed before every use!\n     6\t */\n     7\t\n     8\trequire('../../require-main');\n     9\t\n    10\tconst path = require('path');\n    11\tconst nconf = require('nconf');\n    12\tconst url = require('url');\n    13\tconst util = require('util');\n    14\t\n    15\tprocess.env.NODE_ENV = process.env.TEST_ENV || 'production';\n    16\tglobal.env = process.env.NODE_ENV || 'production';\n    17\t\n    18\t\n    19\tconst winston = require('winston');\n    20\tconst packageInfo = require('../../package.json');\n    21\t\n    22\twinston.add(new winston.transports.Console({\n    23\t\tformat: winston.format.combine(\n    24\t\t\twinston.format.splat(),\n    25\t\t\twinston.format.simple()\n    26\t\t),\n    27\t}));\n    28\t\n    29\ttry {\n    30\t\tconst fs = require('fs');\n    31\t\tconst configJSON = fs.readFileSync(path.join(__dirname, '../../config.json'"}, {'type': 'ai', 'name': None, 'tool_call_id': None, 'tool_call_count': 1, 'tool_call_names': ['execute'], 'content_preview': "Let me now run the tests to see what's currently failing:\n\n"}]}
ojaiyeob@gracehopper:~/kv_cache_offloading$

```

## Experiment 6: Deep Agents Recursion Debug

Use this when Experiment 6 hits `GraphRecursionError` and you want to inspect
why the agent is taking many graph steps instead of hiding the issue with a cap.

This run intentionally disables model-only planning:

- `AGENTBENCH_MODEL_ONLY_PHASES=""`
- `AGENTBENCH_TRACE_AGENT_STREAM=1`

That means planning runs through the real Deep Agents graph, and every graph
step is written into `stage_lifecycle_trace_raw.json`.

```bash
cd ~/kv_cache_offloading

export AGENTBENCH_EXECUTION_LOOP=1
export AGENTBENCH_EXECUTION_LOOP_MAX_STEPS=6
export AGENTBENCH_EXECUTION_LOOP_REQUIRE_TEST=1
export AGENTBENCH_EXECUTION_GUARD=1
export AGENTBENCH_PRINT_CHECKPOINTS=1
export DYN_TOOL_CALL_PARSER=qwen3_coder
export DYN_REASONING_PARSER=qwen3
export AGENTBENCH_DEEPAGENTS_SOURCE=upstream
export AGENTBENCH_FORCE_TOOL_CHOICE=auto
export AGENTBENCH_DISABLE_GENERAL_PURPOSE_SUBAGENT=1
export AGENTBENCH_BATCH_CONTINUE_ON_ERROR=0
export PROMPT_EVOLUTION_REQUIRE_TOOL_LOOP=1
export PROMPT_EVOLUTION_TOOL_LOOP_CASE=edit-validate

# Important: disable model-only planning so this run exposes the real loop.
export AGENTBENCH_MODEL_ONLY_PHASES=""
export AGENTBENCH_TRACE_AGENT_STREAM=1
export AGENTBENCH_TRACE_AGENT_STREAM_MODE=values
export AGENTBENCH_AGENT_RECURSION_LIMIT=80

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
PROMPT_EVOLUTION_BATCH_START_INDEX=0 \
PROMPT_EVOLUTION_BATCH_END_INDEX=1 \
PROMPT_EVOLUTION_VALUE_CHAR_LIMIT=200000 \
./agentbench/run_prompt_evolution_batch_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

After the run fails or finishes, inspect the stream trace:

```bash
cd ~/kv_cache_offloading

RUN_DIR="$(ls -td experiments/raw/agentbench/results/agentbench-* | head -1)"
export RUN_DIR

python3 - <<'PY'
import json
import os
from pathlib import Path

run_dir = Path(os.environ["RUN_DIR"])
p = run_dir / "others" / "stage_lifecycle_trace_raw.json"
events = json.loads(p.read_text())

for e in events:
    if e.get("event_kind") != "agent_stream_step":
        continue
    s = e.get("chunk_summary", {})
    msgs = s.get("last_messages", [])
    last = msgs[-1] if msgs else {}
    print(
        e["stage"],
        "step=", e.get("chunk_index"),
        "messages=", s.get("message_count"),
        "last_type=", last.get("type"),
        "tools=", last.get("tool_call_names"),
        "preview=", (last.get("content_preview") or "")[:160].replace("\n", " "),
    )

for e in events:
    if e.get("event_kind") == "agent_stream_error":
        print("\nERROR:", e.get("error_type"), e.get("error"))
        print("last:", e.get("last_chunk_summary"))
PY
```

How to read the output:

- If you see the same tool or same message pattern repeating, it is probably a
  real loop.
- If you see many different file reads, edits, and validation commands, the task
  is genuinely long and needs a better phase budget.
- If planning loops before useful tool work, the issue is in the planning graph
  path, not in the execution phase.
- If execution loops after planning succeeds, the issue is in tool use,
  validation, or stop-condition handling.

