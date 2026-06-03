# Debug Guide

## AgentBench Environment Setup Runbook

Use [README_AGENTBENCH_ENVIRONMENT.md](README/README_AGENTBENCH_ENVIRONMENT.md) as the
compact setup checklist for new machines. It collects the Node, NodeBB, Redis,
`config.json`, missing-module, and `workspace.patch` checks that are repeated in
the debugging sections below.

## Phased SWE-bench Worker Profile

Use this path when the goal is realistic DeepAgents/SWE-bench traffic while
profiling only the SGLang worker with Nsight:

```bash
cd ~/kv_cache_offloading

AGENTBENCH_WORKFLOW_MODE=phased \
WORKER_PROFILE_EXTRA_ARGS='--sample=none --cuda-event-trace=false --cuda-graph-trace=node' \
PROFILE_STOP_TIMEOUT_SECS=240 \
MODEL='Qwen/Qwen2.5-7B-Instruct' \
TASK_INDEX=0 \
experiments/scripts/deepagents_swebench_profile/profile_one_case.sh
```

Verify the latest run:

```bash
LATEST_PROFILE="$(ls -td experiments/raw/deepagents_swebench_profile/profiles/* | head -1)"
AGENTBENCH_RESULT_DIR="$(cat "$LATEST_PROFILE/agentbench-result-dir.txt")"

python3.11 experiments/scripts/deepagents_swebench_profile/verify_profile_run.py \
  --profile-dir "$LATEST_PROFILE" \
  --agentbench-result-dir "$AGENTBENCH_RESULT_DIR" \
  --show-timing-table \
  --inference-phase decode
```

Expected phase hints:

```text
planning
execution
patch_generation
review
```

Optional HBM pass after a successful worker profile:

```bash
LATEST_PROFILE="$(ls -td experiments/raw/deepagents_swebench_profile/profiles/* | head -1)"

HBM_TOP_KERNELS_PER_GROUP=1 \
HBM_INFERENCE_PHASES=decode \
experiments/scripts/deepagents_swebench_profile/profile_hbm_top_kernels.sh "$LATEST_PROFILE"

cat "$LATEST_PROFILE/kernel_analysis/hbm/hbm_summary.md"
column -s, -t "$LATEST_PROFILE/kernel_analysis/hbm/hbm_phase_bucket_summary.csv" | less -S
```

If the worker image does not have `ncu`, set `WORKER_PROFILE_NCU_DIR` to a host
Nsight Compute install directory before running the HBM script.

If `agent_phase_inference_bucket_summary.csv` is missing, rerun the analyzer
with the worker log:

```bash
BASENAME="$(basename "$LATEST_PROFILE")"

python3.11 experiments/scripts/lpx_decode_split/analyze_nsys_sqlite.py \
  --sqlite "$LATEST_PROFILE/${BASENAME}.sqlite" \
  --worker-log "$LATEST_PROFILE/dynamo-sglang-worker.full.log" \
  --out-dir "$LATEST_PROFILE/kernel_analysis"
```

If phases are still missing, inspect whether hints reached the worker:

```bash
grep -n 'agent_phase' "$LATEST_PROFILE/dynamo-sglang-worker.full.log" | head -40
grep -n 'hint_probe_id' "$LATEST_PROFILE/dynamo-sglang-worker.full.log" | head -40
```

If every kernel is `unassigned`, the analyzer did not receive usable worker
runtime JSON or phase timestamp mapping failed. Keep `DYN_RUNTIME_JSON_LOGS=1`,
run with `AGENTBENCH_WORKFLOW_MODE=phased`, and pass
`--worker-log "$LATEST_PROFILE/dynamo-sglang-worker.full.log"` to
`analyze_nsys_sqlite.py`.

If `.nsys-rep` is missing and only `.qdstrm` exists, the worker stopped before
Nsight finished exporting. Re-run with:

```bash
PROFILE_STOP_TIMEOUT_SECS=240
```

## Frontend Did Not Become Healthy

If startup fails with:

```text
Frontend did not become healthy on port 8000.
```

collect the container state and logs:

```bash
cd ~/kv_cache_offloading

./run_dynamo_single_host.sh status

docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Command}}'

docker logs --tail 200 dynamo-frontend
docker logs --tail 100 dynamo-etcd
docker logs --tail 100 dynamo-nats
```

The most important output is:

```bash
docker logs --tail 200 dynamo-frontend
```

If it contains:

```text
unknown shorthand flag: 'l' in -lc
```

then the frontend image entrypoint is still `/epp` instead of `/bin/bash`.
Make sure the machine has the latest `run_dynamo_head.sh`, which starts the
frontend container with:

```bash
--entrypoint /bin/bash
```

Check the local script:

```bash
grep -n -- '--entrypoint /bin/bash' run_dynamo_head.sh
```

If there is no match, upload the latest repo files and retry.

## Port 8000 Already In Use

Check whether another process already owns port 8000:

```bash
ss -ltnp | grep ':8000' || true
```

If something is listening on port 8000, either stop that process/container or
start Dynamo on another port:

```bash
./run_dynamo_single_host.sh stop

DYNAMO_FRONTEND_PORT=8001 \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH='Qwen/Qwen2.5-7B-Instruct' \
DYNAMO_SERVED_MODEL_NAME='Qwen/Qwen2.5-7B-Instruct' \
./run_dynamo_single_host.sh start
```

Then verify:

```bash
curl -fsS http://127.0.0.1:8001/v1/models
```

## etcd Is Not Running

Dynamo uses etcd like a small registry. The worker registers itself there, and
the frontend uses it to discover workers. If etcd is down, the frontend may not
become healthy.

Check etcd:

```bash
docker ps -a --filter name=dynamo-etcd \
  --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Command}}'

docker logs --tail 200 dynamo-etcd
```

Restart only etcd:

```bash
docker restart dynamo-etcd
```

Try a clean stack restart:

```bash
./run_dynamo_single_host.sh stop
./run_dynamo_single_host.sh start
```

If etcd still exits, clear its saved state and start fresh:

```bash
./run_dynamo_single_host.sh stop

rm -rf ~/kv_cache_offloading/dynamo_head_state/etcd-data

DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH='Qwen/Qwen2.5-7B-Instruct' \
DYNAMO_SERVED_MODEL_NAME='Qwen/Qwen2.5-7B-Instruct' \
./run_dynamo_single_host.sh start
```

Also check whether etcd's port is already in use:

```bash
ss -ltnp | grep ':2379' || true
```

If something is listening on `2379`, stop that process/container before
retrying.

Temporary manual etcd start, if you only need to bring the registry up for a
single-host smoke test:

```bash
curl -s http://127.0.0.1:2379/health || true

docker rm -f dynamo-etcd etcd >/dev/null 2>&1 || true

mkdir -p ~/kv_cache_offloading/dynamo_head_state/etcd-data

docker run -d \
  --name dynamo-etcd \
  --network host \
  -v ~/kv_cache_offloading/dynamo_head_state/etcd-data:/etcd-data \
  quay.io/coreos/etcd:v3.5.14 \
  /usr/local/bin/etcd \
  --name dynamo-etcd \
  --data-dir /etcd-data \
  --listen-client-urls http://0.0.0.0:2379 \
  --advertise-client-urls http://127.0.0.1:2379

curl -s http://127.0.0.1:2379/health
```

Expected:

```json
{"health":"true","reason":""}
```

Prefer the container name `dynamo-etcd`. The repo scripts look for that name in
`status`, `logs`, and `stop`. A manually started container named only `etcd` can
work on port `2379`, but the scripts will not manage it cleanly and it can later
cause port conflicts.

## Worker Or Model Not Ready

If the frontend becomes healthy but the model never appears in `/v1/models`,
watch the worker logs:

```bash
docker logs -f --tail 200 dynamo-sglang-worker
```

Then check model registration again:

```bash
curl -fsS http://127.0.0.1:8000/v1/models
```

If using a non-default frontend port, replace `8000` with that port.

## First Simple Request

Once etcd, nats, frontend, and worker are up, first confirm the model is
registered:

```bash
curl -fsS http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/models
```

Then send a tiny chat completion:

```bash
curl -sS http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [
      {"role": "user", "content": "Reply with exactly: ok"}
    ],
    "max_tokens": 8
  }'
echo
```

Expected response: JSON with a `choices[0].message.content` value similar to
`ok`.

For instrumented Dynamo, run a direct hint probe before full AgentBench:

```bash
PROBE_ID="manual-instrumented-dynamo-probe-$(date +%s)"

curl -sS http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d "{
    \"model\": \"Qwen/Qwen2.5-7B-Instruct\",
    \"messages\": [
      {\"role\": \"user\", \"content\": \"Reply with exactly: ok\"}
    ],
    \"max_tokens\": 8,
    \"nvext\": {
      \"agent_hints\": {
        \"hint_probe_id\": \"${PROBE_ID}\",
        \"program_id\": \"manual_probe\",
        \"agent_phase\": \"hint_path_test\",
        \"expected_output_tokens\": 8
      },
      \"request_context\": {
        \"probe\": \"manual_instrumented_dynamo\"
      }
    }
  }"

echo
echo "PROBE_ID=${PROBE_ID}"
```

Then confirm the same probe id reached the worker:

```bash
docker logs dynamo-sglang-worker 2>&1 | \
  grep -E "${PROBE_ID}|agent_hints|hint_probe_id|worker.decode" | \
  tail -50
```

Success means a worker `[RUNTIME_JSON]` event contains the same `hint_probe_id`
and `agent_hints`.

To profile the Dynamo/SGLang decode path directly for the GPU/LPU split study,
run one controlled synthetic case. This does not run Deep Agents or AgentBench:

```bash
cd ~/kv_cache_offloading

PROMPT_TOKEN_TARGET=8192 \
MAX_TOKENS=256 \
MODEL='Qwen/Qwen2.5-7B-Instruct' \
experiments/scripts/lpx_decode_split/profile_one_decode_case.sh
```

Check:

```bash
LATEST_PROFILE="$(ls -td experiments/raw/lpx_decode_split/profiles/* | head -1)"
LATEST_RESULT_ROOT="$(ls -td experiments/reports/lpx_decode_split/results/* | head -1)"

echo "$LATEST_PROFILE"
echo "$LATEST_RESULT_ROOT"

find "$LATEST_RESULT_ROOT" -name measurements.csv -o -name summary.md
find "$LATEST_PROFILE" -maxdepth 3 -type f | sort

ls experiments/raw/lpx_decode_split/profiles/*/kernel_analysis/summary.md
ls experiments/raw/lpx_decode_split/profiles/*/kernel_analysis/lpx_what_if/summary.md
```

Worker logs like `Registered endpoint 'dynamo.backend.generate'` and
`Model registration succeeded` mean the profiled worker reached the stage that
previously failed. Keep waiting for the script to print `Running decode-sweep...`
and then the final profile/result directories.

If the script appears stuck after:

```text
Model registration succeeded; processing queued requests
```

and no `measurements.csv` or profile files appear yet, the wrapper is probably
waiting on the tiny generation-readiness request. Use the latest
`profile_one_decode_case.sh`; readiness requests are time-bounded and write:

```text
experiments/raw/lpx_decode_split/profiles/<run>/generation-readiness-last-response.txt
```

For faster diagnosis, rerun with shorter readiness timeouts:

```bash
PROFILE_READY_RETRIES=6 \
PROFILE_READY_DELAY_SECS=3 \
PROFILE_READY_REQUEST_TIMEOUT_SECS=10 \
PROMPT_TOKEN_TARGET=8192 \
MAX_TOKENS=256 \
MODEL='Qwen/Qwen2.5-7B-Instruct' \
experiments/scripts/lpx_decode_split/profile_one_decode_case.sh
```

If startup stops earlier with:

```text
Timed out waiting for model registration in the frontend.
```

and the worker log still shows model download or `Load weight begin`, the worker
is not dead; the wrapper gave up too early and cleaned up the container. Rerun
with a longer model-registration wait:

```bash
MODEL_READY_RETRIES=600 \
MODEL_READY_DELAY_SECS=2 \
WORKER_PROFILE_TRACE='cuda,nvtx,cublas' \
WORKER_PROFILE_EXTRA_ARGS='--sample=none --cuda-event-trace=false --cuda-graph-trace=node' \
PROFILE_READY_RETRIES=6 \
PROFILE_READY_DELAY_SECS=3 \
PROFILE_READY_REQUEST_TIMEOUT_SECS=10 \
PROMPT_TOKEN_TARGET=8192 \
MAX_TOKENS=256 \
MODEL='Qwen/Qwen2.5-7B-Instruct' \
experiments/scripts/lpx_decode_split/profile_one_decode_case.sh
```

If the worker log warns about unauthenticated Hugging Face requests, set
`HF_TOKEN` before starting the stack to reduce model download throttling:

```bash
export HF_TOKEN='<your-hugging-face-token>'
```

`docker logs -f dynamo-sglang-worker` will fail after this timeout because the
wrapper cleans up the stack on failure. Inspect the saved logs instead:

```bash
LATEST_PROFILE="$(ls -td experiments/raw/lpx_decode_split/profiles/* | head -1)"
tail -300 "$LATEST_PROFILE/dynamo-sglang-worker.log"
cat "$LATEST_PROFILE/docker-worker-state.txt"
```

In another shell, you can test the same tiny readiness request manually:

```bash
curl -fsS --connect-timeout 3 --max-time 10 \
  http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [
      {"role": "user", "content": "Reply with exactly: ok"}
    ],
    "max_tokens": 4,
    "temperature": 0
  }'
echo
```

If `kernel_analysis/summary.md` is missing but an `.nsys-rep` file exists,
export SQLite manually with `nsys export --force-overwrite true --type sqlite`, then run
`experiments/scripts/lpx_decode_split/analyze_nsys_sqlite.py`.

If the profile wrapper returns:

```text
HTTP 500: {"message":"Failed to generate completions: Connection refused (os error 111)"}
```

the frontend registered the model before the profiled worker was ready for real
generation traffic. Use the latest `profile_one_decode_case.sh`; it waits for a
tiny generation request before sending the measured request and saves:

```text
experiments/raw/lpx_decode_split/profiles/<run>/dynamo-frontend.log
experiments/raw/lpx_decode_split/profiles/<run>/dynamo-sglang-worker.log
```

If it still fails, inspect:

```bash
LATEST_PROFILE="$(ls -td experiments/raw/lpx_decode_split/profiles/* | head -1)"
cat "$LATEST_PROFILE/dynamo-frontend.log" | tail -200
cat "$LATEST_PROFILE/dynamo-sglang-worker.log" | tail -300
```

To separate "Nsight broke worker startup" from "the request shape is broken,"
run the same wrapper with profiling disabled:

```bash
PROFILE_MODE=off \
PROMPT_TOKEN_TARGET=8192 \
MAX_TOKENS=256 \
MODEL='Qwen/Qwen2.5-7B-Instruct' \
experiments/scripts/lpx_decode_split/profile_one_decode_case.sh
```

If `PROFILE_MODE=off` works but the default `PROFILE_MODE=nsys` fails, the
worker image/runtime likely cannot serve correctly under `nsys profile`. In that
case, first collect decode-sweep measurements without Nsight, then use a lower
overhead profiler configuration or profile a smaller request.

If the frontend log shows a worker selected, then:

```text
Failed to generate completions: Connection refused (os error 111)
Removing worker ...
chat endpoints disabled
```

the worker registered and then died or became unreachable under profiling. Retry
with a lower-overhead Nsight configuration:

```bash
WORKER_PROFILE_TRACE='cuda,nvtx,cublas' \
WORKER_PROFILE_EXTRA_ARGS='--sample=none --cuda-event-trace=false --cuda-graph-trace=node' \
PROFILE_READY_RETRIES=6 \
PROFILE_READY_DELAY_SECS=3 \
PROFILE_READY_REQUEST_TIMEOUT_SECS=10 \
PROMPT_TOKEN_TARGET=8192 \
MAX_TOKENS=256 \
MODEL='Qwen/Qwen2.5-7B-Instruct' \
experiments/scripts/lpx_decode_split/profile_one_decode_case.sh
```

If that still fails, confirm the synthetic decode request works without Nsight:

```bash
PROFILE_MODE=off \
PROMPT_TOKEN_TARGET=8192 \
MAX_TOKENS=256 \
MODEL='Qwen/Qwen2.5-7B-Instruct' \
experiments/scripts/lpx_decode_split/profile_one_decode_case.sh
```

If `PROFILE_MODE=off` works, try a smaller profiled request:

```bash
WORKER_PROFILE_TRACE='cuda,nvtx,cublas' \
WORKER_PROFILE_EXTRA_ARGS='--sample=none --cuda-event-trace=false --cuda-graph-trace=node' \
PROMPT_TOKEN_TARGET=1024 \
MAX_TOKENS=32 \
MODEL='Qwen/Qwen2.5-7B-Instruct' \
experiments/scripts/lpx_decode_split/profile_one_decode_case.sh
```

The latest wrapper also saves these files for this failure mode:

```text
experiments/raw/lpx_decode_split/profiles/<run>/docker-worker-state.txt
experiments/raw/lpx_decode_split/profiles/<run>/docker-worker-inspect.json
experiments/raw/lpx_decode_split/profiles/<run>/dynamo-sglang-worker.full.log
```

If the run succeeds but Nsight prints:

```text
Unable to retrieve the importer version: skipping importation of the QDSTRM file.
Generated:
  /profiles/<run>.qdstrm
```

then the measured request succeeded and Nsight captured a raw `.qdstrm` stream,
but the container could not convert it to `.nsys-rep`. NVIDIA's Nsight Systems
docs describe `.qdstrm` as an intermediate CLI output that must be imported into
`.nsys-rep`; the CLI and QdstrmImporter versions need to match.

If you see this message while following `docker logs -f dynamo-sglang-worker`,
remember that it is the in-container importer failing. The outer
`profile_one_decode_case.sh` wrapper may still import the `.qdstrm` after the
worker stops, as long as host `QdstrmImporter` is on `PATH` in the same shell
that launched the profile script. Wait for the profile script itself to return,
then inspect the profile directory.

If only `.qdstrm` exists after the wrapper returns, manually re-add host Nsight
tools to `PATH` and import the latest capture:

```bash
cd ~/tools/nsight-systems-install

NSYS_BIN="$(find "$PWD/extracted" -type f -name nsys | head -1)"
QDISTRM_BIN="$(find "$PWD/extracted" -type f -name QdstrmImporter | head -1)"
export PATH="$(dirname "$NSYS_BIN"):$(dirname "$QDISTRM_BIN"):${PATH}"

cd ~/kv_cache_offloading

LATEST_PROFILE="$(ls -td experiments/raw/lpx_decode_split/profiles/* | head -1)"
BASENAME="$(basename "$LATEST_PROFILE")"

rm -f "$LATEST_PROFILE/${BASENAME}.nsys-rep" "$LATEST_PROFILE/${BASENAME}.sqlite"

QdstrmImporter \
  -i "$LATEST_PROFILE/${BASENAME}.qdstrm" \
  -o "$LATEST_PROFILE/${BASENAME}.nsys-rep"
```

If that import fails with:

```text
Qdstrm file does not have valid time conversion factors.
```

the raw stream is not recoverable. Do not keep trying to import that file. Use
the newest profile that already has `.nsys-rep`, or regenerate the profile while
forcing the worker container to use the same host `nsys` package as host
`QdstrmImporter`.

Find the newest completed profile:

```bash
cd ~/kv_cache_offloading

LATEST_PROFILE="$(find experiments/raw/lpx_decode_split/profiles -name '*.nsys-rep' -exec dirname {} \; | sort -r | head -1)"
echo "$LATEST_PROFILE"
```

If this prints nothing, rerun the profile command from the README golden path.
To regenerate:

```bash
cd ~/tools/nsight-systems-install

NSYS_BIN="$(find "$PWD/extracted" -type f -name nsys | head -1)"
QDISTRM_BIN="$(find "$PWD/extracted" -type f -name QdstrmImporter | head -1)"
export PATH="$(dirname "$NSYS_BIN"):$(dirname "$QDISTRM_BIN"):${PATH}"

cd ~/kv_cache_offloading

NSYS_COMMAND_PATH="$(readlink -f "$(command -v nsys)")"
NSYS_COMMAND_DIR="$(dirname "${NSYS_COMMAND_PATH}")"
if [[ "$(basename "${NSYS_COMMAND_DIR}")" = target-linux-* ]]; then
  WORKER_PROFILE_NSYS_DIR="$(dirname "${NSYS_COMMAND_DIR}")"
else
  WORKER_PROFILE_NSYS_DIR="${NSYS_COMMAND_DIR}"
fi

WORKER_PROFILE_NSYS_DIR="${WORKER_PROFILE_NSYS_DIR}" \
PROFILE_STOP_TIMEOUT_SECS=240 \
PROMPT_TOKEN_TARGET=8192 \
MAX_TOKENS=256 \
MODEL='Qwen/Qwen2.5-7B-Instruct' \
experiments/scripts/lpx_decode_split/profile_one_decode_case.sh
```

The patched wrapper auto-detects host `nsys` when it is on `PATH`, mounts that
directory into the worker container, and runs `/opt/host-nsys-target/nsys` so the
generated `.qdstrm` and host `QdstrmImporter` come from the same Nsight Systems
package.

Check the latest outputs:

```bash
LATEST_PROFILE="$(ls -td experiments/raw/lpx_decode_split/profiles/* | head -1)"
LATEST_RESULT_ROOT="$(ls -td experiments/reports/lpx_decode_split/results/* | head -1)"

find "$LATEST_RESULT_ROOT" -name measurements.csv -o -name summary.md
find "$LATEST_PROFILE" -maxdepth 1 -type f | sort
```

After worker logs show:

```text
Generated:
  /profiles/<run>.nsys-rep
```

wait for `profile_one_decode_case.sh` itself to return, then inspect the latest
analysis:

```bash
cd ~/kv_cache_offloading

LATEST_PROFILE="$(ls -td experiments/raw/lpx_decode_split/profiles/* | head -1)"
LATEST_RESULT_ROOT="$(ls -td experiments/reports/lpx_decode_split/results/* | head -1)"

find "$LATEST_RESULT_ROOT" -name measurements.csv -o -name summary.md
find "$LATEST_PROFILE" -maxdepth 3 -type f | sort

cat "$LATEST_RESULT_ROOT"/*/summary.md
cat "$LATEST_PROFILE/kernel_analysis/summary.md"
cat "$LATEST_PROFILE/kernel_analysis/lpx_what_if/summary.md"
```

The kernel summary should now include:

```text
Phase assignment: epoch_wall
```

or:

```text
Phase assignment: relative_tail_heuristic
```

and sections named `Phase Summary`, `Phase x Bucket Summary`, and
`Top Phase Kernels`. The wrapper passes
`dynamo-sglang-worker.full.log` into `analyze_nsys_sqlite.py` so the analyzer can
use the measured request's `worker.decode.request_received`,
`worker.decode.request_attached`, and `worker.decode.request_completed` events
to split kernels into `prefill` and `decode`.

The corresponding CSV files are:

```text
kernel_analysis/phase_summary.csv
kernel_analysis/phase_bucket_summary.csv
kernel_analysis/top_phase_kernels.csv
```

If `kernel_analysis/summary.md` says:

```text
Phase assignment: `none`
```

but the worker log contains the measured decode-sweep request, the profile is
still usable. This means phase metadata was not attached during analysis, often
because the local analyzer is stale or could not parse the exact Docker log
format. First confirm the measured request events are in the full worker log:

```bash
cd ~/kv_cache_offloading

LATEST_PROFILE="$(ls -td experiments/raw/lpx_decode_split/profiles/* | head -1)"

grep -n 'decode-sweep_.*ctx.*out' "$LATEST_PROFILE/dynamo-sglang-worker.full.log" | tail -20
```

You should see `worker.decode.request_received`,
`worker.decode.request_attached`, and `worker.decode.request_completed` for the
same `external_request_id`. Then update to the latest
`analyze_nsys_sqlite.py` and rerun analysis on the existing profile; you do not
need to rerun Nsight:

```bash
cd ~/kv_cache_offloading

LATEST_PROFILE="$(ls -td experiments/raw/lpx_decode_split/profiles/* | head -1)"
BASENAME="$(basename "$LATEST_PROFILE")"

rm -rf "$LATEST_PROFILE/kernel_analysis"

python3.11 experiments/scripts/lpx_decode_split/analyze_nsys_sqlite.py \
  --sqlite "$LATEST_PROFILE/${BASENAME}.sqlite" \
  --worker-log "$LATEST_PROFILE/dynamo-sglang-worker.full.log" \
  --out-dir "$LATEST_PROFILE/kernel_analysis"

python3.11 experiments/scripts/lpx_decode_split/estimate_lpx_speedup.py \
  --classification-json "$LATEST_PROFILE/kernel_analysis/kernel_classification.json" \
  --completion-tokens 256 \
  --out-dir "$LATEST_PROFILE/kernel_analysis/lpx_what_if"

cat "$LATEST_PROFILE/kernel_analysis/summary.md"
cat "$LATEST_PROFILE/kernel_analysis/lpx_what_if/summary.md"
```

Expected: phase assignment should change to `epoch_wall` or
`relative_tail_heuristic`, and `Phase Summary` should show separate `prefill`
and `decode` rows.

If `kernel_analysis/summary.md` exists but
`kernel_analysis/lpx_what_if/summary.md` is missing, run only the estimator:

```bash
cd ~/kv_cache_offloading

LATEST_PROFILE="$(ls -td experiments/raw/lpx_decode_split/profiles/* | head -1)"

python3.11 experiments/scripts/lpx_decode_split/estimate_lpx_speedup.py \
  --classification-json "$LATEST_PROFILE/kernel_analysis/kernel_classification.json" \
  --completion-tokens 256 \
  --out-dir "$LATEST_PROFILE/kernel_analysis/lpx_what_if"

cat "$LATEST_PROFILE/kernel_analysis/lpx_what_if/summary.md"
```

The wrapper now runs this automatically after successful kernel classification.

If your SSH session closes and you see local paths such as:

```text
/Users/<name>/...
```

you are back on your local laptop, not the GPU machine. Do not run profile
recovery commands there unless you have copied the profile directory locally and
installed Nsight locally. Reconnect to the GPU machine first, then use
`~/kv_cache_offloading`:

```bash
ssh <your-gpu-machine>
cd ~/kv_cache_offloading
```

Also, `find -printf` is GNU/Linux-specific and fails on macOS. Use this portable
form when looking for the newest completed profile:

```bash
LATEST_PROFILE="$(find experiments/raw/lpx_decode_split/profiles -name '*.nsys-rep' -exec dirname {} \; | sort -r | head -1)"
echo "$LATEST_PROFILE"
```

If you have `QdstrmImporter` available on a machine with the matching Nsight
Systems install, import the stream and continue analysis:

```bash
LATEST_PROFILE="$(ls -td experiments/raw/lpx_decode_split/profiles/* | head -1)"
BASENAME="$(basename "$LATEST_PROFILE")"

test -f "$LATEST_PROFILE/${BASENAME}.qdstrm" || {
  echo "ERROR: missing $LATEST_PROFILE/${BASENAME}.qdstrm"
  exit 1
}

QdstrmImporter \
  -i "$LATEST_PROFILE/${BASENAME}.qdstrm" \
  -o "$LATEST_PROFILE/${BASENAME}.nsys-rep"

nsys export --force-overwrite true --type sqlite \
  --output "$LATEST_PROFILE/${BASENAME}.sqlite" \
  "$LATEST_PROFILE/${BASENAME}.nsys-rep"

python3.11 experiments/scripts/lpx_decode_split/analyze_nsys_sqlite.py \
  --sqlite "$LATEST_PROFILE/${BASENAME}.sqlite" \
  --worker-log "$LATEST_PROFILE/dynamo-sglang-worker.full.log" \
  --out-dir "$LATEST_PROFILE/kernel_analysis"

python3.11 experiments/scripts/lpx_decode_split/estimate_lpx_speedup.py \
  --classification-json "$LATEST_PROFILE/kernel_analysis/kernel_classification.json" \
  --out-dir "$LATEST_PROFILE/kernel_analysis/lpx_what_if"
```

If `kernel_analysis/summary.md` says:

```text
Kernel table: `ENUM_CUDA_KERNEL_LAUNCH_TYPE`
Kernel rows: 0
```

the profile capture probably succeeded, but the local analyzer is stale and
picked a lookup table instead of a real CUDA kernel event table. Update the repo
to the latest `analyze_nsys_sqlite.py`, then rerun analysis on the existing
SQLite export:

```bash
cd ~/kv_cache_offloading

LATEST_PROFILE="$(ls -td experiments/raw/lpx_decode_split/profiles/* | head -1)"
BASENAME="$(basename "$LATEST_PROFILE")"

rm -rf "$LATEST_PROFILE/kernel_analysis"

python3.11 experiments/scripts/lpx_decode_split/analyze_nsys_sqlite.py \
  --sqlite "$LATEST_PROFILE/${BASENAME}.sqlite" \
  --worker-log "$LATEST_PROFILE/dynamo-sglang-worker.full.log" \
  --out-dir "$LATEST_PROFILE/kernel_analysis"

python3.11 experiments/scripts/lpx_decode_split/estimate_lpx_speedup.py \
  --classification-json "$LATEST_PROFILE/kernel_analysis/kernel_classification.json" \
  --out-dir "$LATEST_PROFILE/kernel_analysis/lpx_what_if"

cat "$LATEST_PROFILE/kernel_analysis/summary.md"
cat "$LATEST_PROFILE/kernel_analysis/lpx_what_if/summary.md"
```

Expected: `Kernel table` should be a real event table such as
`CUPTI_ACTIVITY_KIND_KERNEL` or `CUDA_GRAPH_EVENTS`, not an `ENUM_*` table, and
`Kernel rows` should be greater than zero. `CUDA_GRAPH_EVENTS` is valid for
runs where SGLang serves through CUDA graph replay. If the analyzer still cannot
find a usable table, it prints a diagnostic list of CUDA/kernel-like tables;
paste that output back into the debug session.

If the diagnostic shows `CUDA_GRAPH_EVENTS` with timed rows but no classic
`CUPTI_ACTIVITY_KIND_KERNEL` table, update to the analyzer that accepts
`CUDA_GRAPH_EVENTS` and rerun the same commands above. If the resulting top
kernel names are too generic to separate attention from FFN/MLP, collect another
profile with CUDA graph node tracing enabled. NVIDIA Nsight Systems documents
`--cuda-graph-trace=graph` as graph-level tracing where node activities are not
collected; `--cuda-graph-trace=node` collects node activities with higher
overhead:

```bash
WORKER_PROFILE_EXTRA_ARGS='--sample=none --cuda-event-trace=false --cuda-graph-trace=node' \
PROFILE_STOP_TIMEOUT_SECS=240 \
PROMPT_TOKEN_TARGET=8192 \
MAX_TOKENS=256 \
MODEL='Qwen/Qwen2.5-7B-Instruct' \
experiments/scripts/lpx_decode_split/profile_one_decode_case.sh
```

If that still reports only `Graph Creation` / `GraphExec Creation` with zero
duration, collect a slower profile with CUDA graphs disabled so Nsight records
individual kernel launches:

```bash
WORKER_EXTRA_ARGS='--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --disable-cuda-graph' \
WORKER_PROFILE_EXTRA_ARGS='--sample=none --cuda-event-trace=false' \
PROFILE_STOP_TIMEOUT_SECS=240 \
PROMPT_TOKEN_TARGET=8192 \
MAX_TOKENS=256 \
MODEL='Qwen/Qwen2.5-7B-Instruct' \
experiments/scripts/lpx_decode_split/profile_one_decode_case.sh
```

This run is usually slower, but it can expose clearer per-kernel names for the
attention-vs-FFN classification.

If `QdstrmImporter` is installed but not on `PATH`, locate it first:

```bash
find /opt /usr/local /usr -name QdstrmImporter 2>/dev/null | head
```

If that prints nothing, this machine does not have the importer installed. Do not
run `/path/to/QdstrmImporter` literally; that is only a placeholder. Either
install a matching Nsight Systems host package on this machine, or move the
`.qdstrm` file to a machine that already has Nsight Systems installed.

For new machines, verify Nsight Systems host tools during setup:

```bash
command -v nsys || echo "nsys is missing"
find /opt /usr/local /usr -name QdstrmImporter 2>/dev/null | head
```

Smoke tests and AgentBench correctness runs do not require these tools. Decode
kernel profiling analysis does require them, because `.qdstrm` must be imported
to `.nsys-rep` and then exported to SQLite before
`analyze_nsys_sqlite.py` can classify kernels.

Install them with NVIDIA's full Nsight Systems `.run` package:

```bash
cd ~
mkdir -p tools/nsight-systems-install
cd tools/nsight-systems-install

NSYS_VERSION="2026.3.1.157-3804839"

case "$(uname -m)" in
  x86_64)
    NSYS_RUN="NsightSystems-linux-public-${NSYS_VERSION}.run"
    ;;
  aarch64|arm64)
    NSYS_RUN="NsightSystems-linux-sbsa-public-${NSYS_VERSION}.run"
    ;;
  *)
    echo "Unsupported architecture for this command: $(uname -m)" >&2
    exit 1
    ;;
esac

wget -O "${NSYS_RUN}" \
  "https://developer.download.nvidia.com/devtools/nsight-systems/${NSYS_RUN}"

chmod +x "${NSYS_RUN}"

rm -rf extracted
mkdir -p extracted
./"${NSYS_RUN}" --target "$PWD/extracted" --noexec

NSYS_BIN="$(find ~/tools/nsight-systems-install/extracted -type f -name nsys | head -1)"
QDISTRM_BIN="$(find ~/tools/nsight-systems-install/extracted -type f -name QdstrmImporter | head -1)"

test -n "${NSYS_BIN}" || { echo "ERROR: nsys not found; inspect installer output"; exit 1; }
test -n "${QDISTRM_BIN}" || { echo "ERROR: QdstrmImporter not found; install full Nsight Systems, not CLI-only"; exit 1; }

NSYS_BIN_DIR="$(dirname "${NSYS_BIN}")"
QDISTRM_BIN_DIR="$(dirname "${QDISTRM_BIN}")"

export PATH="${NSYS_BIN_DIR}:${QDISTRM_BIN_DIR}:${PATH}"

command -v nsys
command -v QdstrmImporter
nsys --version
```

If the commands are still missing, inspect the download and installer output:

```bash
cd ~/tools/nsight-systems-install
ls -lh
file "${NSYS_RUN}"
./"${NSYS_RUN}" --help | head -80
find "$PWD/extracted" -maxdepth 5 -type f | sort | head -100
```

When you do have the real path, call it by absolute path:

```bash
/path/to/QdstrmImporter \
  -i "$LATEST_PROFILE/${BASENAME}.qdstrm" \
  -o "$LATEST_PROFILE/${BASENAME}.nsys-rep"
```

If you only have the Nsight Systems GUI on another machine, copy the `.qdstrm`
there and import it with a matching or newer Nsight Systems install, then copy
the resulting `.nsys-rep` or exported `.sqlite` back into the same profile
directory.

If the measured request succeeds but no `.nsys-rep` file is produced, make sure
you have the latest wrapper. It now stops `dynamo-sglang-worker` gracefully before
normal stack cleanup so `nsys` can flush the report. You can increase the wait:

```bash
PROFILE_STOP_TIMEOUT_SECS=240 \
PROMPT_TOKEN_TARGET=8192 \
MAX_TOKENS=256 \
MODEL='Qwen/Qwen2.5-7B-Instruct' \
experiments/scripts/lpx_decode_split/profile_one_decode_case.sh
```

You can also use the built-in script test:

```bash
DYNAMO_FRONTEND_PORT="${DYNAMO_FRONTEND_PORT:-8000}" ./run_dynamo_single_host.sh test
```

If this run uses port `8001`, either export it once:

```bash
export DYNAMO_FRONTEND_PORT=8001
```

or replace the URLs with `http://127.0.0.1:8001/...`.

## Model Context Length Exceeded

If AgentBench fails with an error like:

```text
current token count exceeds the model maximum context length of 32768 tokens
```

the Dynamo/SGLang path is working, but the request plus agent/tool context is
too large for the worker's configured context window.

Ways to fix it without changing Dynamo/SGLang context length:

```bash
# Try a different, smaller SWE-bench task.
python3.11 agentbench/deepagents_swebench_single_host.py \
  --app-variant upstream_deploy_coding_agent \
  --frontend-url http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  --model Qwen/Qwen2.5-7B-Instruct \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 1
```

Other non-restart options:

- use a smaller task index or specific smaller `--instance-id`
- use the direct smoke-test curl instead of AgentBench when you only need to
  prove the runtime works
- reduce prompt/tool-history size in AgentBench code if you need this exact
  task to fit a 32k context window

Lowering generation output tokens only helps when the request is barely over the
limit. It will not fix a prompt/tool transcript that already exceeds 32k before
generation.

For a basic runtime smoke test, use the tiny direct request instead of
AgentBench:

```bash
curl -sS http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [
      {"role": "user", "content": "Reply with exactly: ok"}
    ],
    "max_tokens": 8
  }'
echo
```

For AgentBench, restart the worker with a larger SGLang context length if the
GPU has enough memory:

```bash
./run_dynamo_single_host.sh stop

DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH='Qwen/Qwen2.5-7B-Instruct' \
DYNAMO_SERVED_MODEL_NAME='Qwen/Qwen2.5-7B-Instruct' \
WORKER_EXTRA_ARGS='--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --context-length 65536' \
./run_dynamo_single_host.sh start
```

If you are using a non-default frontend port, include it in the restart and in
the AgentBench URL:

```bash
export DYNAMO_FRONTEND_PORT=8001
```

Then rerun AgentBench with:

```bash
python3.11 agentbench/deepagents_swebench_single_host.py \
  --app-variant upstream_deploy_coding_agent \
  --frontend-url http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  --model Qwen/Qwen2.5-7B-Instruct \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 0
```

If the larger context causes GPU OOM, pick a smaller SWE-bench task index or use
a larger-memory machine. Lowering `max_tokens` only helps when the prompt is
near the limit; it does not help if the prompt/tool transcript alone already
exceeds the context window.

If SGLang rejects the larger context with:

```text
User-specified context_length (65536) is greater than the derived context_length (32768)
```

then the model/runtime derived a 32k safe limit. Preferred fixes:

- keep the default 32k context and use a smaller AgentBench task
- use a model/runtime configuration that naturally supports the needed context

Override only if you accept the risk of incorrect outputs or CUDA errors:

```bash
./run_dynamo_single_host.sh stop

SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN=1 \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH='Qwen/Qwen2.5-7B-Instruct' \
DYNAMO_SERVED_MODEL_NAME='Qwen/Qwen2.5-7B-Instruct' \
WORKER_EXTRA_ARGS='--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --context-length 65536' \
./run_dynamo_single_host.sh start
```

Verify the override reached the worker container:

```bash
docker inspect dynamo-sglang-worker \
  --format '{{range .Config.Env}}{{println .}}{{end}}' | \
  grep SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN
```

Expected:

```text
SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN=1
```

If this line is missing, update `run_dynamo_single_host.sh` and
`run_dynamo_worker.sh` so the variable is forwarded into Docker, then restart.

If using instrumented local images, include `DYN_RUNTIME_JSON_LOGS=1`,
`FRONTEND_IMAGE=local/dynamo-frontend:runtime-json-logs`, and
`WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs` in the restart command.

## GPU Or Docker Problems

Verify the host and Docker can see the GPU:

```bash
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

If `nvidia-smi` works on the host but fails inside Docker, reinstall or
reconfigure NVIDIA Container Toolkit.

## Deep Agents Local Install Missing

If dependency installation fails with an error like:

```text
... is not a valid requirement
```

then either `upstream/deepagents` is missing, or the install command
was run from the wrong directory.

The repo expects Deep Agents to exist here:

```text
upstream/deepagents/libs/deepagents
```

That nested `libs/deepagents` directory is the Python package. Do not install
from `upstream/deepagents` itself.

From the repo root, run:

```bash
cd ~/kv_cache_offloading

mkdir -p upstream

if [ ! -f upstream/deepagents/libs/deepagents/pyproject.toml ]; then
  git clone https://github.com/langchain-ai/deepagents.git upstream/deepagents
  git -C upstream/deepagents checkout 2cf7e25dbb40e783d9d4d545c29e595800bf314f
fi

python3.11 -m pip install -r agentbench/requirements.txt
```

Direct install equivalent:

```bash
cd ~/kv_cache_offloading
python3.11 -m pip install ./upstream/deepagents/libs/deepagents
```

Quick verification:

```bash
python3.11 - <<'PY'
import deepagents
print(deepagents.__file__)
PY
```

## Deep Agents Installed But Import Fails

If AgentBench fails with:

```text
ModuleNotFoundError: No module named 'deepagents'
```

and this command prints `WARNING: Package(s) not found: deepagents`:

```bash
python3.11 -m pip show deepagents
```

then Deep Agents is not installed in the `python3.11` environment currently
running AgentBench. Install it with `python3.11 -m pip`, not plain `pip`.

first make sure you are using the same Python interpreter for install and run:

```bash
cd ~/kv_cache_offloading

which python3.11
python3.11 -m pip --version
python3.11 -m pip show deepagents || true
```

Check that the local Deep Agents checkout exists:

```bash
test -f upstream/deepagents/libs/deepagents/pyproject.toml && echo "Deep Agents checkout exists" || echo "Deep Agents checkout missing"
```

If the checkout is missing:

```bash
mkdir -p upstream
git clone https://github.com/langchain-ai/deepagents.git upstream/deepagents
git -C upstream/deepagents checkout 2cf7e25dbb40e783d9d4d545c29e595800bf314f
```

If the checkout exists but `python3.11 -m pip show deepagents` says
`WARNING: Package(s) not found: deepagents`, the source is present but not
installed into the `python3.11` environment yet.

Reinstall with the exact interpreter used to run AgentBench:

```bash
python3.11 -m pip install --upgrade pip
python3.11 -m pip install ./upstream/deepagents/libs/deepagents
python3.11 -m pip install -r agentbench/requirements.txt
```

Verify the import:

```bash
python3.11 - <<'PY'
import sys
import deepagents
print(sys.executable)
print(deepagents.__file__)
PY
```

If you are using a virtual environment, activate it before both install and run,
or call the venv Python directly:

```bash
source .venv/bin/activate
python -m pip install -r agentbench/requirements.txt
python agentbench/deepagents_swebench_single_host.py --help
```

Temporary fallback if local install is still not visible:

```bash
cd ~/kv_cache_offloading
export PYTHONPATH="$PWD/upstream/deepagents/libs/deepagents:${PYTHONPATH:-}"
python3.11 - <<'PY'
import deepagents
print(deepagents.__file__)
PY
```

## Disk Pressure

Check disk usage:

```bash
df -h /
docker system df
```

For a smoke test, keep at least 30-50 GB free. For a Dynamo rebuild, keep at
least 80-120 GB free.

If Docker fails while downloading or unpacking an image with an error like:

```text
failed to register layer: mkdir ... no space left on device
```

the root filesystem or Docker data root is full. First stop the local runtime:

```bash
cd ~/kv_cache_offloading
./run_dynamo_single_host.sh stop || true
```

Then check where the space is going:

```bash
df -h /
docker system df
sudo du -xh /var/lib/docker 2>/dev/null | sort -h | tail -30
du -xh ~/.cache/huggingface 2>/dev/null | sort -h | tail -30
du -xh ~/kv_cache_offloading 2>/dev/null | sort -h | tail -30
```

Safe Docker cleanup for retrying an image pull:

```bash
docker container prune -f
docker image prune -f
docker builder prune -f
```

If Docker still reports many reclaimable GB and no important local images need
to be preserved, do the stronger cleanup:

```bash
docker system prune -af
docker builder prune -af
```

If Hugging Face/model cache is the largest consumer, remove only models you can
redownload:

```bash
du -sh ~/.cache/huggingface 2>/dev/null || true
rm -rf ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct
rm -rf ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct
```

Recheck free space before retrying:

```bash
df -h /
docker system df
```

## Image Architecture

On GH200, verify host architecture:

```bash
uname -m
```

If it prints `aarch64`, rebuild Dynamo images on that machine. Images built on
`g5.xlarge` are usually `linux/amd64` and should not be reused on ARM64 GH200.

After building local images:

```bash
docker image inspect local/dynamo-frontend:runtime-json-logs --format '{{.Architecture}}'
docker image inspect local/dynamo-sglang:runtime-json-logs --format '{{.Architecture}}'
```

Expected:

```text
x86_64 host -> amd64 images
aarch64 host -> arm64 images
```

## Clean Restart

Use this to retry a non-instrumented smoke test:

```bash
cd ~/kv_cache_offloading

./run_dynamo_single_host.sh stop

DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH='Qwen/Qwen2.5-7B-Instruct' \
DYNAMO_SERVED_MODEL_NAME='Qwen/Qwen2.5-7B-Instruct' \
./run_dynamo_single_host.sh start
```

Verify:

```bash
curl -fsS http://127.0.0.1:8000/v1/models
./run_dynamo_single_host.sh test
```

=====
docker run -d
--name etcd
--network host
quay.io/coreos/etcd:v3.5.14
etcd
--listen-client-urls http://0.0.0.0:2379
--advertise-client-urls http://127.0.0.1:2379 Then verify:

curl -s http://127.0.0.1:2379/health
docker run -d \
  --name etcd \
  --network host \
  quay.io/coreos/etcd:v3.5.14 \
  etcd \
  --listen-client-urls http://0.0.0.0:2379 \
  --advertise-client-urls http://127.0.0.1:2379
Then verify:

curl -s http://127.0.0.1:2379/health
# Expected: {"health":"true","reason":""}

## Agent Did Not Edit The Workspace

Use this when a run completes but `workspace.patch`, `git_status.txt`, and
`git_diff_stat.txt` are empty. That means the serving stack worked, but the
agent did not actually fix the SWE-bench task.

First compare a single continuous agent run against the phased run. The single
run is the best sanity check because Deep Agents keeps one tool loop instead of
splitting planning, execution, patch generation, and review into separate model
calls.

Choose the model with `MODEL_KIND`:

```bash
cd ~/kv_cache_offloading

MODEL_KIND="${MODEL_KIND:-coder}"  # coder, coder30b, or instruct
case "$MODEL_KIND" in
  coder)
    MODEL_NAME='Qwen/Qwen2.5-Coder-7B-Instruct'
    ;;
  coder30b)
    MODEL_NAME='Qwen/Qwen3-Coder-30B-A3B-Instruct'
    ;;
  instruct)
    MODEL_NAME='Qwen/Qwen2.5-7B-Instruct'
    ;;
  *)
    echo "MODEL_KIND must be coder, coder30b, or instruct" >&2
    exit 1
    ;;
esac

echo "Using model: $MODEL_NAME"
```

Restart Dynamo/SGLang with the selected model:

```bash
./run_dynamo_single_host.sh stop

SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN=1 \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="$MODEL_NAME" \
DYNAMO_SERVED_MODEL_NAME="$MODEL_NAME" \
WORKER_EXTRA_ARGS='--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --context-length 65536' \
./run_dynamo_single_host.sh start
```

Verify model registration:

```bash
curl -fsS http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/models
```

Run the continuous baseline agent:

```bash
AGENTBENCH_WORKFLOW_MODE=baseline \
python3.11 agentbench/deepagents_swebench_single_host.py \
  --app-variant upstream_deploy_coding_agent \
  --frontend-url http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  --model "$MODEL_NAME" \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 0 \
  --prompt-evolution-value-char-limit 1000
```

Check whether the task was actually attempted:

```bash
LATEST_RESULT="$(ls -td experiments/raw/agentbench/results/* | head -1)"

echo "$LATEST_RESULT"
cat "$LATEST_RESULT/others/git_status.txt"
cat "$LATEST_RESULT/others/git_diff_stat.txt"
wc -c "$LATEST_RESULT/workspace.patch"
grep -R "workspace_changed\\|tool_call\\|finish_reason\\|output_tokens" -n \
  "$LATEST_RESULT/prompt_evolution_values" "$LATEST_RESULT/others/step_results.json" | head -80
```

Expected for a useful run:

```text
workspace.patch size > 0
git_status.txt or git_diff_stat.txt is non-empty
model output includes edit/write/execute tool activity, not only ls/read_file
```

If the baseline edits files but the phased run does not, the problem is likely
the phased orchestration: the planning response may be empty or malformed, and
that bad planning text gets fed into later phases. If both baseline and phased
runs fail to edit files, inspect model/tool compatibility and try the other
model with `MODEL_KIND=instruct` or `MODEL_KIND=coder`.

## workspace.patch Still Appears Under others/

New runs should write the patch here:

```text
experiments/raw/agentbench/results/<run_id>/workspace.patch
```

If a machine still writes this instead:

```text
experiments/raw/agentbench/results/<run_id>/others/workspace.patch
```

then it is probably running an older copy of
`agentbench/deepagents_swebench_single_host.py`, or the run was created before
the report-layout update.

Check the script:

```bash
grep -n "collect_workspace_artifacts(run_dir, workspace_dir, auxiliary_dir=others_dir)" \
  agentbench/deepagents_swebench_single_host.py

grep -n "patch_path = report_dir / \"workspace.patch\"" \
  agentbench/deepagents_swebench_single_host.py
```

Both commands should print a matching line. If either command prints nothing,
upload or pull the latest repo files before rerunning AgentBench.

For an already-created result, move the patch manually:

```bash
LATEST_RESULT="$(ls -td experiments/raw/agentbench/results/* | head -1)"

if [ -f "$LATEST_RESULT/others/workspace.patch" ] && [ ! -f "$LATEST_RESULT/workspace.patch" ]; then
  mv "$LATEST_RESULT/others/workspace.patch" "$LATEST_RESULT/workspace.patch"
fi

find "$LATEST_RESULT" -maxdepth 2 -name workspace.patch -print -exec wc -c {} \;
```

## Agent Tool Shell Cannot Find node

Use this when the AgentBench transcript shows tool results like:

```text
/bin/sh: line 1: node: command not found
```

This usually means Node.js is installed through `nvm`, but the Python process
that launched Deep Agents did not inherit the `nvm` Node binary path. Installing
or updating `nvm` during the agent run is not enough because the agent tool
commands run in non-interactive shells.

Before launching AgentBench, prepare Node.js in the same shell:

```bash
cd ~/kv_cache_offloading

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm install 22
nvm use 22

export PATH="$(dirname "$(command -v node)"):$PATH"

node -v
npm -v
```

Both `node -v` and `npm -v` must succeed before starting the benchmark. Then run
AgentBench from that same shell so `LocalShellBackend(inherit_env=True)` passes
the Node path into tool commands:

```bash
AGENTBENCH_WORKFLOW_MODE=baseline \
python3.11 agentbench/deepagents_swebench_single_host.py \
  --app-variant upstream_deploy_coding_agent \
  --frontend-url http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  --model "$MODEL_NAME" \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 0 \
  --prompt-evolution-value-char-limit 1000
```

After the run:

```bash
LATEST_RESULT="$(ls -td experiments/raw/agentbench/results/* | head -1)"
grep -R "node: command not found" -n "$LATEST_RESULT" || true
wc -c "$LATEST_RESULT/workspace.patch"
```

## Node Project Dependencies Missing

Use this when the AgentBench transcript shows tool results like:

```text
Error: Cannot find module 'nconf'
Error: Cannot find module 'async'
Error: Cannot find module 'winston'
Error: Cannot find module 'semver'
Error: Cannot find module 'ioredis'
Error: Cannot find module 'lru-cache'
Error: Cannot find module 'chalk'
Error: Cannot find module 'request'
Error: Cannot find module 'request-promise-native'
Error: Cannot find module 'xregexp'
Error: Cannot find module 'mkdirp'
Error: Cannot find module 'mime'
Error: Cannot find module 'graceful-fs'
Error: Cannot find module 'validator'
Error: Cannot find module 'cron'
Error: Cannot find module 'benchpressjs'
Error: Cannot find module 'nodemailer'
Error: Cannot find module 'html-to-text'
Error: ENOENT: no such file or directory, scandir '.../node_modules/timeago/locales'
```

This means Node.js itself is available, but the checked-out task workspace has
not installed its full npm dependency set. If `npm install` says only a small
number of packages were installed, the shell may be in production mode or npm
may be omitting dev or optional dependencies. For NodeBB tasks, install all
dependencies in the benchmark workspace before rerunning AgentBench:

```bash
cd ~/kv_cache_offloading

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm use 22
export PATH="$(dirname "$(command -v node)"):$PATH"

cd agentbench/repos/NodeBB__NodeBB

unset NODE_ENV
npm install --include=dev --include=optional

node -e "require('nconf'); require('async'); require('winston'); require('semver'); require('ioredis'); require('lru-cache'); require('chalk'); require('request'); require('request-promise-native'); require('xregexp'); require('mkdirp'); require('mime'); require('graceful-fs'); require('validator'); require('cron'); require('benchpressjs'); require('nodemailer'); require('html-to-text'); console.log('node deps ok')"
```

Before using compatibility installs, inspect whether this checkout has the real
NodeBB dependency manifest. For this benchmark checkout, the real manifest may
live at `install/package.json` rather than root `package.json`:

```bash
git remote -v || true
git rev-parse HEAD || true
git ls-tree -r HEAD --name-only | grep -E '(^|/)package(-lock)?\.json$' || true

node - <<'NODE'
const fs = require('fs');
for (const file of ['package.json', 'install/package.json']) {
  if (!fs.existsSync(file)) continue;
  const p = JSON.parse(fs.readFileSync(file, 'utf8'));
  console.log(file, {
    name: p.name,
    version: p.version,
    dependencies: Object.keys(p.dependencies || {}).length,
    devDependencies: Object.keys(p.devDependencies || {}).length,
    optionalDependencies: Object.keys(p.optionalDependencies || {}).length,
  });
}
NODE
```

If root `package.json` has only a few dependencies but `install/package.json`
has the real NodeBB manifest, install the exact dependency versions from
`install/package.json` plus the root dependency ranges into the root workspace.
The root ranges are included last because NodeBB's dependency checker reads
root `package.json`:

```bash
NODEBB_INSTALL_DEPS="$(
node <<'NODE'
const fs = require('fs');
const install = JSON.parse(fs.readFileSync('install/package.json', 'utf8'));
const root = JSON.parse(fs.readFileSync('package.json', 'utf8'));
const deps = {
  ...(install.dependencies || {}),
  ...(install.devDependencies || {}),
  ...(root.dependencies || {}),
  ...(root.devDependencies || {}),
};
console.log(Object.entries(deps).map(([name, version]) => `${name}@${version}`).join(' '));
NODE
)"

npm install --no-save $NODEBB_INSTALL_DEPS

node -e "console.log(require('chalk').yellow('chalk ok'))"
node -e "new (require('@isaacs/ttlcache'))({ ttl: 1000 }); console.log('ttlcache ok')"
node -e "if (typeof require('connect-redis').default !== 'function') throw new Error('connect-redis mismatch'); console.log('connect-redis ok')"
npm ls nconf winston
test -d node_modules/timeago/locales && echo "timeago locales ok"
test -f node_modules/nodebb-theme-persona/theme.json && echo "persona theme ok"
```

If Mocha fails with:

```text
Error: dependencies-out-of-date
```

rerun this exact-manifest install block. That error usually means the root
`package.json` dependency ranges, commonly `nconf` or `winston`, were not
installed after the `install/package.json` versions.

Build the NodeBB templates before running the email tests:

```bash
./nodebb build tpl --series
test -f build/public/templates/emails/verify-email.js && echo "email template ok"
```

If Mocha fails with:

```text
Failed to lookup view "emails/verify-email"
```

rerun this template build. The dependency install prepares packages, but it does
not create `build/public/templates`.

For this preflight, webpack errors about missing `build/public/src/client.js` or
`build/public/src/admin/admin.js` during `./nodebb build tpl --series` are not
blocking as long as `email template ok` prints. The selected tests only need the
compiled templates.

Use the compatibility bundle below only if `install/package.json` is absent or
the exact-manifest install fails.

If the full install fails on optional/native packages, retry with:

```bash
npm install --include=dev --omit=optional
```

If the install still reports only a tiny dependency set, this benchmark
materialization has a sparse `package.json`. Inspect what this checkout actually
declares:

```bash
node -e "const p=require('./package.json'); console.log({name:p.name, deps:Object.keys(p.dependencies||{}).length, devDeps:Object.keys(p.devDependencies||{}).length}); console.log('has semver:', !!(p.dependencies||{}).semver || !!(p.devDependencies||{}).semver)"
npm ls semver ioredis lru-cache chalk request request-promise-native xregexp mkdirp mime graceful-fs validator cron benchpressjs nodemailer html-to-text || true
```

There is not a reliable single public package that safely provides all top-level
modules for this sparse checkout. Instead, generate one install list from the
checkout's own `require(...)` calls and install that list in one pass:

```bash
NODEBB_COMPAT_DEPS="$(
node <<'NODE'
const fs = require('fs');
const path = require('path');
const Module = require('module');

const builtins = new Set(Module.builtinModules.map((name) => name.replace(/^node:/, '')));
const roots = ['src', 'test'].filter((root) => fs.existsSync(root));
const deps = new Set();
const knownRuntimeDeps = [
  'xregexp',
  'timeago@1.6.7',
  'nodebb-theme-persona',
  'nodebb-plugin-dbsearch',
  'nodebb-widget-essentials',
  'nodebb-plugin-composer-default',
];
const pinnedPackages = new Map([
  ['chalk', 'chalk@4.1.2'],
  ['@isaacs/ttlcache', '@isaacs/ttlcache@1.4.1'],
  ['connect-redis', 'connect-redis@7.1.1'],
]);
const validPackage = /^(?:@[a-z0-9][a-z0-9._~-]*\/)?[a-z0-9][a-z0-9._~-]*$/i;

function walk(filePath) {
  const stat = fs.statSync(filePath);
  if (stat.isDirectory()) {
    for (const entry of fs.readdirSync(filePath)) {
      if (entry === 'node_modules' || entry === '.git') continue;
      walk(path.join(filePath, entry));
    }
    return;
  }
  if (!filePath.endsWith('.js')) return;
  const text = fs.readFileSync(filePath, 'utf8');
  const pattern = /require\s*\(\s*['"]([^'"]+)['"]\s*\)/g;
  let match;
  while ((match = pattern.exec(text))) {
    const spec = match[1];
    if (spec.startsWith('.') || spec.startsWith('/') || builtins.has(spec)) continue;
    const pkg = spec.startsWith('@')
      ? spec.split('/').slice(0, 2).join('/')
      : spec.split('/')[0];
    if (!validPackage.test(pkg)) continue;
    if (pkg.includes('*') || pkg.includes('$') || pkg.includes('{') || pkg.includes('}')) continue;
    if (!builtins.has(pkg)) deps.add(pinnedPackages.get(pkg) || pkg);
  }
}

for (const root of roots) walk(root);
for (const dep of knownRuntimeDeps) deps.add(dep);
console.log([...deps].sort().join(' '));
NODE
)"

echo "$NODEBB_COMPAT_DEPS"
npm install --no-save $NODEBB_COMPAT_DEPS
```

Run that as one block. Do not install `timeago@1.6.7` separately afterward:
another `npm install --no-save ...` can prune the previously installed
compatibility packages.

If the tests fail with:

```text
TypeError: TTLCache is not a constructor
```

rerun the generated compatibility install above. It pins
`@isaacs/ttlcache@1.4.1` because this older NodeBB checkout expects
`require('@isaacs/ttlcache')` to return the constructor directly.

If the tests fail with:

```text
TypeError: sessionStore is not a constructor
```

rerun the generated compatibility install above. It pins `connect-redis@7.1.1`
because this older NodeBB checkout expects `require('connect-redis').default`
to be the session-store constructor.

If the tests fail with:

```text
TypeError: chalk.yellow is not a function
```

rerun the generated compatibility install above. It pins `chalk@4.1.2` because
this older NodeBB checkout expects the CommonJS v4 API with helpers like
`chalk.yellow(...)`.

If the tests fail with:

```text
ENOENT ... node_modules/nodebb-theme-persona/theme.json
```

rerun the generated compatibility install above. The default NodeBB theme and
plugins are loaded from config names, so they are manually added to
`knownRuntimeDeps` because the `require(...)` scanner cannot discover them.

If a package is still missing after that, add it as an environment dependency
without saving it into the repo:

```bash
npm install --no-save semver ioredis lru-cache chalk@4.1.2 request request-promise-native xregexp mkdirp mime graceful-fs validator cron benchpressjs nodemailer html-to-text timeago@1.6.7 @isaacs/ttlcache@1.4.1 connect-redis@7.1.1 nodebb-theme-persona nodebb-plugin-dbsearch nodebb-widget-essentials nodebb-plugin-composer-default
node -e "require('semver'); require('ioredis'); require('lru-cache'); require('chalk'); require('request'); require('request-promise-native'); require('xregexp'); require('mkdirp'); require('mime'); require('graceful-fs'); require('validator'); require('cron'); require('benchpressjs'); require('nodemailer'); require('html-to-text'); new (require('@isaacs/ttlcache'))({ ttl: 1000 }); if (typeof require('connect-redis').default !== 'function') throw new Error('connect-redis default export mismatch'); console.log('redis deps ok')"
test -d node_modules/timeago/locales && echo "timeago locales ok"
test -f node_modules/nodebb-theme-persona/theme.json && echo "persona theme ok"
```

Install temporary `--no-save` dependencies together. Because they are not
recorded in `package.json`, running a later `npm install --no-save <other-package>`
can prune a previously installed temporary package.

If `npm install` reports an engine/version mismatch, inspect the repo's Node
version requirements and switch Node versions before installing:

```bash
cat package.json | grep -A5 '"engines"' || true
cat .nvmrc 2>/dev/null || true
```

Then rerun AgentBench from the same shell. A useful rerun should no longer show
`Cannot find module`, and `workspace.patch` should become non-empty if the agent
actually edits files.

## NodeBB config.json Missing

Use this when the AgentBench transcript shows tool results like:

```text
Error: ENOENT: no such file or directory, open '.../NodeBB__NodeBB/config.json'
```

This means npm dependencies are installed, but the NodeBB test harness cannot
boot because the checkout is missing its local `config.json`. Redis is used here
only as the simple local test database for NodeBB. Create a minimal test config
and start Redis before rerunning AgentBench:

```bash
cd ~/kv_cache_offloading/agentbench/repos/NodeBB__NodeBB

docker rm -f nodebb-test-redis >/dev/null 2>&1 || true
docker run -d \
  --name nodebb-test-redis \
  --network host \
  redis:7-alpine

cat > config.json <<'JSON'
{
  "url": "http://127.0.0.1:4567",
  "secret": "agentbench-test-secret",
  "database": "redis",
  "redis": {
    "host": "127.0.0.1",
    "port": "6379",
    "password": "",
    "database": "0"
  },
  "test_database": {
    "host": "127.0.0.1",
    "port": "6379",
    "password": "",
    "database": "1"
  }
}
JSON
```

Preflight the selected tests directly:

```bash
test -f config.json && echo "config.json exists"
node -e "require('nconf'); require('async'); require('winston'); console.log('node deps ok')"
./nodebb build tpl --series
test -f build/public/templates/emails/verify-email.js && echo "email template ok"
npx mocha --timeout 30000 test/database.js test/database/keys.js test/user/emails.js
```

Expected success signal:

```text
298 passing
```

If this reaches real assertion failures instead of `ENOENT` or
`MODULE_NOT_FOUND`, rerun AgentBench from the repo root:

```bash
cd ~/kv_cache_offloading

AGENTBENCH_WORKFLOW_MODE=baseline \
python3.11 agentbench/deepagents_swebench_single_host.py \
  --app-variant upstream_deploy_coding_agent \
  --frontend-url http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  --model "$MODEL_NAME" \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 0 \
  --prompt-evolution-value-char-limit 1000
```

## Agent Runs Mocha Tests With node

Use this when the AgentBench transcript shows tool calls like:

```text
node test/database.js
node test/database/keys.js
node test/user/emails.js
```

and the tool result fails with:

```text
ReferenceError: before is not defined
```

That is not a NodeBB dependency failure. Those files are Mocha test files, and
Mocha provides globals such as `before`, `describe`, and `it`. Running them
directly with `node` will fail even when the environment is healthy.

Verify the environment with the correct command:

```bash
cd ~/kv_cache_offloading/agentbench/repos/NodeBB__NodeBB

npx mocha --timeout 30000 test/database.js test/database/keys.js test/user/emails.js
```

Expected success signal:

```text
298 passing
```

For future AgentBench runs, make the task prompt or harness validation guidance
state the exact command:

```text
Run selected tests with:
npx mocha --timeout 30000 test/database.js test/database/keys.js test/user/emails.js

Do not run these test files directly with node.
```

The harness now builds a `validation_command` for JavaScript selected tests and
injects it into the task prompt and prompt-evolution artifacts. Check
`prompt_evolution_values/01_task_input.json`,
`prompt_evolution_values/02_formatted_prompt.json`, or the prompt evolution
report to confirm the model saw the command.

## Agent Stops After One Recon Tool Call

Use this when the prompt evolution report shows:

```text
observed_tool_calls=1
tools_used=ls
workspace_changed=False
```

and `final_summary.txt` says the agent will read files next, but the transcript
contains no `read_file`, `edit_file`, or validation command.

This means the environment and prompt were accepted, but the model stopped after
planning the next action instead of continuing the tool loop. It is not a NodeBB
dependency failure and not a Mocha invocation failure.

Check these files:

```bash
cat experiments/raw/agentbench/results/<run_id>/prompt_evolution_report.md
cat experiments/raw/agentbench/results/<run_id>/prompt_evolution_values/07_model_behavior.json
wc -c experiments/raw/agentbench/results/<run_id>/workspace.patch
cat experiments/raw/agentbench/results/<run_id>/others/git_status.txt
cat experiments/raw/agentbench/results/<run_id>/others/git_diff_stat.txt
```

Expected failure signal:

```text
workspace.patch is 0 bytes
git status is empty
git diff stat is empty
```

Next debug move: make the execution prompt stricter about continuing through
tool calls until it has either edited files and run validation, or hit a concrete
blocker. The prompt should explicitly say that writing "I will read files next"
is not a valid final answer when file tools are available.

The task prompt now includes this stricter instruction in its expectations:
after identifying files to inspect, the agent must read them with tools before
answering, and a valid final answer requires either a real code change plus a
validation attempt or a concrete blocker from a tool result.

The extra prompt guidance now lives outside the Python prompt builder:

```text
agentbench/deepagents_app/prompts/task_overrides.txt
```

Disable all prompt overrides for a clean larger-model baseline with:

```bash
AGENTBENCH_PROMPT_OVERRIDES=0
```

Use a different override file with:

```bash
AGENTBENCH_PROMPT_OVERRIDES_FILE=/path/to/task_overrides.txt
```

## Agent Stops After Reading One File

Use this when the prompt evolution report shows:

```text
observed_tool_calls=2
tools_used=ls, read_file
workspace_changed=False
```

and the final summary says the agent will inspect another file next. This means
the stricter prompt improved behavior from "only listed files" to "listed files
and read one file", but the model still ended the run before making edits.

Check whether the run used the current external override file:

```bash
grep -n "Execution discipline:" experiments/raw/agentbench/results/<run_id>/prompt_evolution_report.md
grep -n "I will read files next" experiments/raw/agentbench/results/<run_id>/prompt_evolution_report.md
```

If `Execution discipline:` is missing but the strict expectation lines are
present, the remote machine likely ran an older harness copy from before prompt
overrides moved into `agentbench/deepagents_app/prompts/task_overrides.txt`.

Next debug move: sync the latest harness to the machine that runs AgentBench,
then rerun. If the agent still stops after one `read_file`, make the override
more explicit by requiring it to inspect all named interface files before a
final answer, or switch to phased mode so planning and execution are separate
model calls.

## Agent Produces a Prose Patch Plan Instead of Editing

Use this when the prompt evolution report shows:

```text
observed_tool_calls=3
tools_used=ls, read_file
workspace_changed=False
```

and `final_summary.txt` contains proposed code snippets or "implementation
steps", but the transcript contains no `edit_file`, `write_file`, or validation
command.

This means the prompt override was loaded and the agent understood the task, but
the model treated the answer as a code-review/planning response instead of an
implementation run. The final patch is still missing:

```bash
wc -c experiments/raw/agentbench/results/<run_id>/workspace.patch
cat experiments/raw/agentbench/results/<run_id>/others/git_status.txt
cat experiments/raw/agentbench/results/<run_id>/others/git_diff_stat.txt
```

Expected failure signal:

```text
workspace.patch is 0 bytes
git status is empty
git diff stat is empty
```

Next debug move: strengthen `agentbench/deepagents_app/prompts/task_overrides.txt`
so it forbids proposing code snippets as the final answer. The override should
tell the agent to use `edit_file`/`write_file` for implementation, then run the
validation command. If this still fails, switch from baseline/single mode to
phased mode so the first call can plan and a later call is forced into execution.

The override now explicitly says:

```text
Do not provide proposed code snippets as the final answer when edit tools are available.
If you know what code should change, apply it with `edit_file` or `write_file`.
After applying changes, run the validation command above with `execute`.
```

## Agent Reads Target Files Then Hits Output Length

Use this when the prompt evolution report shows:

```text
observed_tool_calls=6
tools_used=ls, read_file
workspace_changed=False
```

and `measurements.json` shows:

```text
finish_reason=length
completion_tokens=2048
```

This means the prompt override worked well enough to make the model inspect the
named target files, but the model spent the post-inspection response on analysis
or repeated next steps and exhausted the output budget before calling
`edit_file`, `write_file`, or `execute`.

Check:

```bash
cat experiments/raw/agentbench/results/<run_id>/prompt_evolution_values/07_model_behavior.json
cat experiments/raw/agentbench/results/<run_id>/others/measurements.json
wc -c experiments/raw/agentbench/results/<run_id>/workspace.patch
```

Expected failure signal:

```text
finish_reason is length
workspace.patch is 0 bytes
no edit_file/write_file/execute tool calls
```

Next debug move: either switch to phased mode so the planning call can spend
tokens on analysis and the execution call can focus on edits, or make the
baseline override stricter: after reading target files, the next assistant action
must be an edit tool call unless a tool result shows a concrete blocker. Raising
the output-token cap may reduce truncation, but by itself may only produce a
longer prose plan.

## Phased Run Produces Empty Later Phases

Use this when a phased run has four phase measurements but still writes an empty
patch:

```text
workspace.patch is 0 bytes
planning response says "Next Step"
execution response is ```json
patch_generation response is ```json
review response is ```json
```

This means phased mode itself is working, but the phase prompts are too weak.
Planning can still end with a proposed next tool action, and execution,
patch-generation, and review can inherit that weak plan and emit empty JSON
fences instead of using edit tools.

Check:

```bash
cat experiments/raw/agentbench/results/<run_id>/step_results.json
cat experiments/raw/agentbench/results/<run_id>/others/measurements.json
wc -c experiments/raw/agentbench/results/<run_id>/workspace.patch
```

Expected failure signal:

```text
step_results has planning, execution, patch_generation, review
execution output is only an empty JSON fence
no edit_file/write_file/execute tool calls
```

Next debug move: strengthen `build_phase_prompt()` in
`agentbench/deepagents_app/src/agent.py`. The planning phase should return a
concrete edit plan, not "read this next"; the execution phase should explicitly
ignore planning that only proposes more inspection and must call file tools or
edit tools; patch_generation should report no patch if `git diff` is empty.

The phase prompts now explicitly:

```text
- forbid planning from ending with "read this next"
- forbid empty JSON/markdown fences
- tell execution to use read_file, then edit_file/write_file, then execute validation
- tell patch_generation/review to inspect git status/diff and report no patch if empty
```

## Phased Run Chases Redis Install Instead of Editing

Use this when a phased run still writes an empty patch and the execution model
behavior shows only an `execute` tool call like:

```text
sudo apt-get update && sudo apt-get install -y redis-server
```

Expected failure signal:

```text
workspace.patch is 0 bytes
observed_tool_call_count is 1
observed_tool_call_names is ["execute"]
tool result says apt-get: command not found
no read_file/edit_file/write_file calls
```

This means the model has confused the NodeBB test preflight with the SWE-bench
implementation task. Redis is an environment dependency for validation, not the
code change. The run should not spend its one useful action trying to install OS
packages.

Check:

```bash
jq '.after.messages[] | select(.tool_calls|length>0)' \
  experiments/raw/agentbench/results/<run_id>/prompt_evolution_values/07_model_behavior.json
wc -c experiments/raw/agentbench/results/<run_id>/workspace.patch
cat experiments/raw/agentbench/results/<run_id>/final_summary.txt
```

Next debug move: strengthen the external task override and/or phase prompts so
the agent treats Redis as preflight. The prompt should say that Redis and NodeBB
dependencies are expected to be prepared outside the coding run; do not install
OS packages with `apt-get`, `yum`, or `dnf`; if validation reports Redis is down,
report it as a validation preflight blocker after attempting code edits, not as
the implementation task.

## SGLang Extraction Fails On Out-of-Tree Symlink

Use this when extracting SGLang source from the worker image reaches the package
path but fails during copy:

```text
Package path: /sgl-workspace/sglang/python/sglang
invalid symlink ".../sglang/srt/mem_cache/cpp_radix_tree/.clang-format" -> "../../../../../sgl-kernel/.clang-format"
```

This means the package contains a symlink that points outside the copied package
tree. The symlink is not needed for runtime instrumentation, but raw `docker cp`
can fail on it.

Expected fix: use the updated
`runtime_instrumentation/sglang_transfer_logging/extract_sglang_source.sh`,
which streams the package with `tar` and excludes that `.clang-format` symlink.

Check the EC2 copy is current:

```bash
grep -n "tar -C" runtime_instrumentation/sglang_transfer_logging/extract_sglang_source.sh
grep -n "cpp_radix_tree/.clang-format" runtime_instrumentation/sglang_transfer_logging/extract_sglang_source.sh
```

## SGLang Transfer Log Directory Exists But Event File Is Missing

Use this when:

```text
ls -lh experiments/raw/sglang_transfer_logs/
# total 0
tail: cannot open 'experiments/raw/sglang_transfer_logs/latest_sglang_transfer_events.jsonl'
```

The transfer JSONL file is created only when an instrumented function emits an
event. An empty directory means either the worker did not load the patched
overlay, the logging env did not reach the container, or the request did not hit
the instrumented HiCache host-tier movement functions.

Check the worker env and bind mount:

```bash
docker inspect dynamo-sglang-worker \
  --format '{{range .Config.Env}}{{println .}}{{end}}' | \
  grep -E 'SGLANG_TRANSFER_LOG|SGLANG_TRANSFER_LOG_PATH'

docker inspect dynamo-sglang-worker \
  --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}' | \
  grep sglang_transfer_overlay
```

Check the patched source is what Python imports:

```bash
docker exec dynamo-sglang-worker python3 - <<'PY'
import inspect
import sglang.srt.mem_cache.memory_pool_host as mph
print(mph.__file__)
print("transfer marker:", "_sgl_log_transfer_event" in inspect.getsource(mph))
PY
```

If `transfer marker: True`, the next likely cause is that HiCache host movement
was not enabled or not triggered. Restart with HiCache enabled and enough cache
pressure to call `backup_from_device_all_layer()` and
`load_to_device_per_layer()`:

```bash
WORKER_EXTRA_ARGS='--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --enable-hierarchical-cache --hicache-ratio 0.1' \
WORKER_SGLANG_DEV_MODE=1 \
WORKER_SGLANG_SOURCE_ROOT="$PWD/upstream/sglang/python/sglang" \
SGLANG_TRANSFER_LOG=1 \
./run_dynamo_single_host.sh start
```

If env and mount checks pass but the Python import check prints nothing, split
the check into smaller commands. First confirm the mounted source file contains
the instrumentation marker without importing SGLang:

```bash
docker exec dynamo-sglang-worker bash -lc '
set -e
ls -l /workspace/sglang_transfer_overlay/sglang/srt/mem_cache/memory_pool_host.py
grep -n "_sgl_log_transfer_event\|backup_from_device_all_layer\|load_to_device_per_layer" \
  /workspace/sglang_transfer_overlay/sglang/srt/mem_cache/memory_pool_host.py | head -30
'
```

Then confirm Python resolves `sglang` from the overlay:

```bash
docker exec dynamo-sglang-worker python3 -c '
import sys
print("python ok")
print("\n".join(sys.path[:8]))
import sglang
print("sglang:", sglang.__file__)
'
```

If `sglang.__file__` is not under `/workspace/sglang_transfer_overlay`, the
overlay path is not winning on `PYTHONPATH`.

If the mounted file shows only one wrapped occurrence but multiple method
definitions:

```text
def load_to_device_per_layer(...)
def backup_from_device_all_layer(...)
```

pull the updated patcher and rerun it. `memory_pool_host.py` contains multiple
classes with the same method names, and the patcher must instrument every
occurrence, not just the first one.

```bash
python3 runtime_instrumentation/sglang_transfer_logging/patch_sglang_transfer_logging.py \
  --sglang-root upstream/sglang/python/sglang

grep -n "_sgl_log_transfer_event" \
  upstream/sglang/python/sglang/srt/mem_cache/memory_pool_host.py
```

## HiCache Startup Fails Due Host Memory

If the SGLang worker fails during HiCache startup with:

```text
ValueError: Not enough host memory available. Requesting 8.37 GB but only have 1.19 GB free.
```

the fatal issue is the HiCache host memory request, not the nearby `libnuma.so`
or `set_mempolicy` messages. Start with a smaller cache ratio:

```bash
WORKER_EXTRA_ARGS='--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru --enable-hierarchical-cache --hicache-ratio 0.1' \
WORKER_SGLANG_DEV_MODE=1 \
WORKER_SGLANG_SOURCE_ROOT="$PWD/upstream/sglang/python/sglang" \
SGLANG_TRANSFER_LOG=1 \
./run_dynamo_single_host.sh start
```

If that still exceeds available host memory, retry with
`--hicache-ratio 0.05` or free memory on the host.

If the error changes to:

```text
ValueError: Not enough host memory available. Requesting 4.19 GB but only have 1.34 GB free.
```

then `--hicache-ratio 1` is still too large for the current host/container free
RAM. Keep lowering the ratio; `0.1` is the safer starting point for this host.

To inspect GPU HBM separately from host RAM:

```bash
nvidia-smi
nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free --format=csv
nvidia-smi --query-compute-apps=pid,process_name,used_gpu_memory --format=csv
```

During startup or an AgentBench run, sample HBM once per second:

```bash
mkdir -p experiments/gpu_memory_logs
nvidia-smi \
  --query-gpu=timestamp,index,name,memory.total,memory.used,memory.free,utilization.gpu \
  --format=csv \
  -l 1 | tee experiments/gpu_memory_logs/nvidia_smi_memory.csv
```

To inspect host RAM and container limits:

```bash
free -h
docker stats --no-stream dynamo-sglang-worker
docker exec dynamo-sglang-worker bash -lc 'free -h; cat /sys/fs/cgroup/memory.max 2>/dev/null || true'
```

## SGLang Run Is Slow With Transfer Logging Enabled

Transfer logging can slow the run, especially if HiCache is actively moving KV
blocks. The logger writes one JSON event per instrumented transfer, flushes the
stderr line, and appends to the JSONL file. Full token IDs are only logged when
`SGLANG_TRANSFER_LOG_FULL_TOKENS=1`; by default only
`SGLANG_TRANSFER_LOG_TOKEN_PREVIEW` token IDs are included.

Check whether logging volume is the bottleneck:

```bash
ls -lh experiments/raw/sglang_transfer_logs/
LATEST_TRANSFER_LOG="$(ls -t experiments/raw/sglang_transfer_logs/sglang_transfer_events_*.jsonl | head -1)"
wc -l "$LATEST_TRANSFER_LOG"
du -h "$LATEST_TRANSFER_LOG"
docker stats --no-stream dynamo-sglang-worker
nvidia-smi
```

For a lower-overhead run, keep full tokens disabled and reduce preview/detail
sizes:

```bash
SGLANG_TRANSFER_LOG=1 \
SGLANG_TRANSFER_LOG_FULL_TOKENS=0 \
SGLANG_TRANSFER_LOG_TOKEN_PREVIEW=8 \
SGLANG_TRANSFER_LOG_MAX_TENSOR_DETAILS=4 \
./run_dynamo_single_host.sh start
```

If the JSONL line count grows very quickly, collect one short instrumented run
for transfer visibility, then rerun with `SGLANG_TRANSFER_LOG=0` to compare raw
benchmark latency.

## SGLang Transfer `numel` vs `token_ids_preview`

If a transfer event shows tensor details like:

```json
{"name":"host_indices","shape":[2048],"numel":2048}
```

but only:

```json
"token_ids_preview":[8358049613095],"token_preview_count":1
```

do not interpret the preview value as a real tokenizer ID. `numel` belongs to
the observed tensor metadata, usually `host_indices` and `device_indices`.
Those tensors are KV-cache slot/index tensors, not necessarily model token ID
tensors. The current preview extractor separately searches local variables whose
names look token-related, and it skips CUDA tensors to avoid synchronizing GPU
data back to CPU. As a result, a transfer can have thousands of tensor elements
while the token preview is empty or contains one unrelated scalar-like value.

For low-level frame accounting, use `num_bytes_observed`, `num_kb_observed`,
and `num_mb_observed`. For actual KV payload volume, prefer
`kv_num_bytes_estimated` / `kv_num_mb_estimated`; those estimates are now
token-granular and come from memory-pool shape metadata rather than the visible
index tensors. The page-granular comparison remains available under
`kv_num_bytes_estimated_page_granular`.

The transfer patcher now instruments both layers:

- `memory_pool_host.py` records bytes, direction, tensor metadata, and timing.
- `hiradix_cache.py` wraps `write_backup()` and `load_back()` with semantic
  token context, then passes that context down to the lower transfer event.

When the semantic context is active, events include:

```json
"token_preview_source":"semantic_context",
"semantic_token_ids_preview":[151644,872,198],
"semantic_token_count":64,
"semantic_token_source":"write_backup.node.key.token_ids"
```

If `token_preview_source` is `local_heuristic`, the event did not occur under a
HiRadix token context. Treat that preview as low-level debug metadata, not true
token IDs. Use `SGLANG_TRANSFER_LOG_INDEX_PREVIEW=1` only when you want an
explicit preview of CUDA index tensors such as `host_indices` or
`device_indices`; it introduces a small GPU-to-CPU sync.

Default events are compact. Use `SGLANG_TRANSFER_LOG_VERBOSE=1` for tensor
details and empty fallback diagnostics. Use `SGLANG_TRANSFER_LOG_SYNC_TIMING=1`
when you want `elapsed_ms_cuda_sync` and `cuda_sync_wait_ms`; that adds a device
synchronization while logging.
