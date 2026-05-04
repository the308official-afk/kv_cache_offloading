# HintBench

`hintbench/` is the lightweight benchmark harness for hint-guided Dynamo + SGLang experiments.

## Cluster First

Run HintBench only after the serving cluster is already up.

### Head node

```bash
cd ~/kv_cache_offloading
sudo ./aws/bootstrap_ec2_docker.sh
DYNAMO_MODEL_PATH=Qwen/Qwen2.5-0.5B ./run_dynamo_head.sh start
./run_dynamo_head.sh status
./run_dynamo_head.sh logs
hostname -I
```

Use the private IP from `hostname -I` for the workers.

### Worker nodes

Recommended worker instance:

- `g5.xlarge`
- `g5.2xlarge`

Run this on each worker:

```bash
cd ~/kv_cache_offloading
sudo ./aws/bootstrap_ec2_gpu.sh rootdisk
newgrp docker
./aws/check_ec2_rootdisk_worker_ready.sh
DYNAMO_MODEL_PATH=Qwen/Qwen2.5-0.5B \
DYNAMO_SERVED_MODEL_NAME=Qwen/Qwen2.5-0.5B \
ETCD_ENDPOINTS=http://172.31.92.60:2379 \
./run_dynamo_worker.sh start
./run_dynamo_worker.sh status
./run_dynamo_worker.sh logs -f
```

`172.31.92.60` is just an example. Replace it with the current head-node private IP.

## Run One Experiment

```bash
python3 hintbench/run_experiment.py \
  --config hintbench/experiments/baseline_round_robin.yaml \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions
```

This:

- reads one experiment config
- generates a workload
- sends requests to the frontend
- writes per-request results
- writes a compact summary

Outputs go under:

- `hintbench/results/<experiment_name>_<timestamp>/`

Default result timestamps use Texas-local time:

- timezone: `America/Chicago`

Key files in each run directory:

- `metadata.json`
- `workload.jsonl`
- `results.jsonl`
- `summary.json`

## Run the Standard 3-Config Suite

Use this if you want:

- `baseline_round_robin`
- `kv_router`
- `hint_routing`
- automatic comparison at the end

```bash
python3 hintbench/run_suite.py \
  --frontend-url http://127.0.0.1:8000/v1/chat/completions
```

Notes:

- workers should already be running
- `run_suite.py` restarts the head node between runs to switch router modes

Suite output:

- normal per-run folders under `hintbench/results/`
- one suite folder under `hintbench/results/suite_<timestamp>/`

The suite folder contains:

- `comparison.txt`
- `comparison.json`

## Compare Existing Runs

```bash
python3 hintbench/analysis/compare_runs.py \
  hintbench/results/baseline_round_robin_20260504_163703 \
  hintbench/results/kv_router_20260504_164046 \
  hintbench/results/hint_routing_20260504_164139
```

This prints a side-by-side table with:

- success count
- average latency
- p50 latency
- p95 latency
- average cached tokens
- average KV hit rate
- worker-pair counts
