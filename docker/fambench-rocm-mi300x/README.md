# FAMBench on ROCm / MI300X

This is a minimal launcher for testing FAMBench DLRM on AMD MI300X GPUs with
`rocm/pytorch:latest`.

It downloads FAMBench into:

```text
~/dlrm/FAMBench
```

Inside the container, that path is mounted as:

```text
/workspace/dlrm/FAMBench
```

## Run

```bash
docker/fambench-rocm-mi300x/run.sh
```

The script starts `rocm/pytorch:latest` with:

```text
/dev/kfd
/dev/dri
host networking
host IPC
SYS_PTRACE
seccomp=unconfined
64G shared memory
$HOME/dockerx:/dockerx
$HOME/dlrm:/workspace/dlrm
/data/ojaiyeob:/workspace/data
```

After cloning or refreshing submodules, it checks:

```text
/workspace/dlrm/FAMBench/benchmarks/dlrm/ootb/bench/dlrm_s_benchmark.sh
```

## Hot Patch `dlrm_s_benchmark.sh`

To run a custom benchmark script instead of the upstream file:

```bash
CUSTOM_DLRM_BENCH_SH=/path/to/your/dlrm_s_benchmark.sh \
docker/fambench-rocm-mi300x/run.sh
```

The custom file is mounted read-only into the container, copied over:

```text
/workspace/dlrm/FAMBench/benchmarks/dlrm/ootb/bench/dlrm_s_benchmark.sh
```

and marked executable before the check runs.
