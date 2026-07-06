ojaiyeob@gracehopper:~/kv_cache_offloading$ cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
CACHE_PINNING_MODE=sweep \
DISTRACTOR_COUNTS="200" \
PROTECTED_INPUT_LEN=2000 \
DISTRACTOR_INPUT_LEN=2000 \
./agentbench/run_cache_pinning_microbenchmark_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
========================================
EXPERIMENT DIRS READY (raw/report/chart/runtime directories exist and are writable)
========================================
  /home/central/ojaiyeob/kv_cache_offloading/experiments/raw/sglang_transfer_logs
  /home/central/ojaiyeob/kv_cache_offloading/experiments/raw/lpx_decode_split/profiles
  /home/central/ojaiyeob/kv_cache_offloading/experiments/raw/agentbench/results
  /home/central/ojaiyeob/kv_cache_offloading/experiments/raw/agentbench/diagnostics
  /home/central/ojaiyeob/kv_cache_offloading/experiments/reports
  /home/central/ojaiyeob/kv_cache_offloading/experiments/charts
  /home/central/ojaiyeob/kv_cache_offloading/experiments/runtime_state
========================================
CACHE PINNING MICROBENCH CONTRACT
========================================
Contract file: contracts/cache_pinning_microbenchmark.contract.sh
Contract doc: contracts/cache_pinning_microbenchmark.contract.md
Mode: sweep
Model: Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
Machine profile: gh200

Pinned Dynamo:
  repo=https://github.com/ai-dynamo/dynamo.git
  pull_ref=6213
  ref=7d3d4ec8e4ae865af2f903b21b4afabca28e1940

Pinned SGLang:
  repo=https://github.com/sgl-project/sglang.git
  pull_ref=18941
  ref=ff2f70b0fcb6b3ea130c46927ed98edf69d5c17c

Images:
  frontend=local/dynamo-frontend:cache-pinning-gh200
  worker=local/dynamo-sglang:cache-pinning-gh200

Frontend cache-control contract:
  flag_mode=auto
  flag_value=--enable-cache-control
  enable_cache_control=1
  router_mode=kv

Shared pinning knobs:
  request_type=ephemeral
  ttl=1h
  ttl_min_seconds=300
  ttl_max_seconds=3600
  pinned_ratio=0.1
  sglang_hicache_max_pinned_ratio=0.1
  hicache_ratio=1
  hicache_write_policy=write_through
  mem_fraction_static=0.7
  enable_cache_report=1
  enable_hierarchical_cache=1
  require_hierarchical_cache=1
  development_branch_stack=1
  retention_probe_seed=42
  retention_sweep_seed_mode=fixed
========================================
PRECISE CLEAN START ACTIVE (clearing any old runtime before Cache-pinning microbenchmark)
========================================
========================================
PRECISE CLEAN START READY (old runtime cleared before Cache-pinning microbenchmark)
========================================
========================================
CACHE PINNING MICROBENCH SWEEP
========================================
Ensuring isolated cache-pinning images...
Using machine profile: gh200
FRONTEND_IMAGE=local/dynamo-frontend:cache-pinning-gh200
WORKER_IMAGE=local/dynamo-sglang:cache-pinning-gh200
Preparing isolated cache-pinning sources...
Cloning https://github.com/ai-dynamo/dynamo.git into /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo_cache_pinning
Cloning into '/home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo_cache_pinning'...
remote: Enumerating objects: 539930, done.
remote: Counting objects: 100% (2270/2270), done.
remote: Compressing objects: 100% (1185/1185), done.
Receiving objects: 100% (539930/539930), 590.29 MiB | 61.24 MiB/s, done.
remote: Total 539930 (delta 1636), reused 1150 (delta 1066), pack-reused 537660 (from 2)
Resolving deltas: 100% (426590/426590), done.
Updating files: 100% (4424/4424), done.
Fetching pull/6213/head for cache-pinning validation
remote: Enumerating objects: 345, done.
remote: Counting objects: 100% (264/264), done.
remote: Compressing objects: 100% (5/5), done.
remote: Total 345 (delta 259), reused 259 (delta 259), pack-reused 81 (from 1)
Receiving objects: 100% (345/345), 77.05 KiB | 1.57 MiB/s, done.
Resolving deltas: 100% (277/277), completed with 99 local objects.
From https://github.com/ai-dynamo/dynamo
 * [new ref]               refs/pull/6213/head -> origin/cache_pinning_pr_6213
Updating files: 100% (4386/4386), done.
HEAD is now at 7d3d4ec8e4 Address review feedback on CacheControl

Cache-pinning Dynamo source is ready at:
  /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo_cache_pinning
Pinned ref:
  7d3d4ec8e4ae865af2f903b21b4afabca28e1940
Cloning https://github.com/sgl-project/sglang.git into /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang_cache_pinning
Cloning into '/home/central/ojaiyeob/kv_cache_offloading/upstream/sglang_cache_pinning'...
remote: Enumerating objects: 296748, done.
remote: Counting objects: 100% (1338/1338), done.
remote: Compressing objects: 100% (756/756), done.
remote: Total 296748 (delta 971), reused 586 (delta 582), pack-reused 295410 (from 4)
Receiving objects: 100% (296748/296748), 205.57 MiB | 55.28 MiB/s, done.
Resolving deltas: 100% (234639/234639), done.
Updating files: 100% (6947/6947), done.
Fetching pull/18941/head for cache-pinning validation
remote: Enumerating objects: 414, done.
remote: Counting objects: 100% (350/350), done.
remote: Compressing objects: 100% (6/6), done.
remote: Total 414 (delta 345), reused 344 (delta 344), pack-reused 64 (from 1)
Receiving objects: 100% (414/414), 257.58 KiB | 3.22 MiB/s, done.
Resolving deltas: 100% (359/359), completed with 135 local objects.
From https://github.com/sgl-project/sglang
 * [new ref]               refs/pull/18941/head -> origin/cache_pinning_pr_18941
Updating files: 100% (6250/6250), done.
HEAD is now at ff2f70b0fc Merge branch 'main' into idhanani/dyn-1986-poc-pin-v2

Cache-pinning SGLang source is ready at:
  /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang_cache_pinning
Pinned ref:
  ff2f70b0fcb6b3ea130c46927ed98edf69d5c17c
updated: /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo_cache_pinning/lib/llm/src/kv_router/push_router.rs
updated: /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo_cache_pinning/components/src/dynamo/sglang/init_llm.py
Cache-pinning Dynamo source repair complete.
updated: /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang_cache_pinning/python/sglang/srt/mem_cache/hiradix_cache.py
Cache-pinning SGLang source repair complete.
========================================
CACHE PINNING IMAGE BUILD START (building isolated cache-pinning images; plain Docker logs are expected while output is captured)
========================================
Building isolated cache-pinning runtime images from the cache-pinning PR stack...
Build reason(s): frontend image missing worker image missing
Rendering cache-pinning Dynamo frontend Dockerfile
INFO: Generated Dockerfile written to /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo_cache_pinning/container/rendered.Dockerfile
Applying cache-pinning EPP image override: registry.k8s.io/gateway-api-inference-extension/epp:v0.5.1
Applying lean frontend Dockerfile adjustment: skip benchmark package install
Building local/dynamo-frontend:cache-pinning-gh200 for platform linux/arm64 via docker buildx
[+] Building 6.8s (20/64)                                                                                                                                               docker:default
 => [internal] load build definition from rendered.Dockerfile                                                                                                                     0.0s
 => => transferring dockerfile: 22.49kB                                                                                                                                           0.0s
 => resolve image config for docker-image://docker.io/docker/dockerfile:1.10.0-labs                                                                                               0.4s
 => CACHED docker-image://docker.io/docker/dockerfile:1.10.0-labs@sha256:940282bab7a18daad689c238d407ad22393369ad53c6125c9c00f8be8a9da678                                         0.0s
 => [internal] load metadata for ghcr.io/astral-sh/uv:latest                                                                                                                      0.3s
 => [internal] load metadata for quay.io/pypa/manylinux_2_28_aarch64:latest                                                                                                       0.4s
 => [internal] load metadata for nvcr.io/nvidia/base/ubuntu:noble-20250619                                                                                                        0.6s
 => [internal] load metadata for nvcr.io/nvidia/cuda-dl-base:25.06-cuda12.9-devel-ubuntu24.04                                                                                     0.5s
 => [internal] load metadata for registry.k8s.io/gateway-api-inference-extension/epp:v0.5.1                                                                                       5.2s
 => [internal] load .dockerignore                                                                                                                                                 0.0s
 => => transferring context: 1.79kB                                                                                                                                               0.0s
 => CACHED [internal] setting cache mount permissions                                                                                                                             0.0s
 => [internal] load build context                                                                                                                                                 1.0s
 => => transferring context: 68.77MB                                                                                                                                              1.0s
 => CACHED FROM ghcr.io/astral-sh/uv:latest@sha256:4d01caf3b22dfd11003455e2e68153da08c4ee1fa54fdbd166c6282d22693419                                                               0.0s
 => [dynamo_base 1/7] FROM nvcr.io/nvidia/cuda-dl-base:25.06-cuda12.9-devel-ubuntu24.04@sha256:ab128a0b5d4298e62c691e478e42e0af98aecdb71ea17b1fea0261875faf4611                   0.0s
 => CANCELED [epp 1/1] FROM registry.k8s.io/gateway-api-inference-extension/epp:v0.5.1@sha256:5364ac1243c8522a45f64e47247fac59994829a24750202c5340b23bc12729fa                    1.1s
 => => resolve registry.k8s.io/gateway-api-inference-extension/epp:v0.5.1@sha256:5364ac1243c8522a45f64e47247fac59994829a24750202c5340b23bc12729fa                                 0.0s
 => => sha256:5364ac1243c8522a45f64e47247fac59994829a24750202c5340b23bc12729fa 2.65kB / 2.65kB                                                                                    0.0s
 => => sha256:b4096246e80ee012d24584061ce715fa829c67a077f73b66fdaf67ea151f953c 1.98kB / 1.98kB                                                                                    0.0s
 => => sha256:bfb59b82a9b65e47d485e53b3e815bca3b3e21a095bd0cb88ced9ac0b48062bf 13.36kB / 13.36kB                                                                                  0.1s
 => => sha256:4eff9a62d888790350b2481ff4a4f38f9c94b3674d26b2f2c85ca39cdef43fd9 547.59kB / 547.59kB                                                                                0.2s
 => => sha256:35d697fe273816c60d20a62a879f8643f79cd4ed85a8e80dba28a17350fc26b6 104.23kB / 104.23kB                                                                                0.2s
 => => sha256:a62778643d563b511190663ef9a77c30d46d282facfdce4f3a7aecc03423c1f3 67B / 67B                                                                                          0.2s
 => => extracting sha256:35d697fe273816c60d20a62a879f8643f79cd4ed85a8e80dba28a17350fc26b6                                                                                         0.0s
 => => extracting sha256:bfb59b82a9b65e47d485e53b3e815bca3b3e21a095bd0cb88ced9ac0b48062bf                                                                                         0.0s
 => => extracting sha256:4eff9a62d888790350b2481ff4a4f38f9c94b3674d26b2f2c85ca39cdef43fd9                                                                                         0.0s
 => => sha256:3214acf345c0cc6bbdb56b698a41ccdefc624a09d6beb0d38b5de0b2303ecaf4 123B / 123B                                                                                        0.3s
 => => sha256:5664b15f108bf9436ce3312090a767300800edbbfd4511aa1a6d64357024d5dd 168B / 168B                                                                                        0.3s
 => => sha256:7c12895b777bcaa8ccae0605b4de635b68fc32d60fa08f421dc3818bf55ee212 188B / 188B                                                                                        0.2s
 => => sha256:0bab15eea81d0fe6ab56ebf5fba14e02c4c1775a7f7436fbddd3505add4e18fa 93B / 93B                                                                                          0.3s
 => => sha256:4aa0ea1413d37a58615488592a0b827ea4b2e48fa5a77cf707d0e35f025e613f 385B / 385B                                                                                        0.3s
 => => sha256:da7816fa955ea24533c388143c78804c28682eef99b4ee3723b548c70148bba6 321B / 321B                                                                                        0.3s
 => => extracting sha256:a62778643d563b511190663ef9a77c30d46d282facfdce4f3a7aecc03423c1f3                                                                                         0.0s
 => => extracting sha256:7c12895b777bcaa8ccae0605b4de635b68fc32d60fa08f421dc3818bf55ee212                                                                                         0.0s
 => => extracting sha256:3214acf345c0cc6bbdb56b698a41ccdefc624a09d6beb0d38b5de0b2303ecaf4                                                                                         0.0s
 => => extracting sha256:5664b15f108bf9436ce3312090a767300800edbbfd4511aa1a6d64357024d5dd                                                                                         0.0s
 => => extracting sha256:0bab15eea81d0fe6ab56ebf5fba14e02c4c1775a7f7436fbddd3505add4e18fa                                                                                         0.0s
 => => extracting sha256:4aa0ea1413d37a58615488592a0b827ea4b2e48fa5a77cf707d0e35f025e613f                                                                                         0.0s
 => => extracting sha256:da7816fa955ea24533c388143c78804c28682eef99b4ee3723b548c70148bba6                                                                                         0.0s
 => => sha256:ddf74a63f7d8b7d157e5db1a45675a58e304b4c1d425b05c28c835b987623395 131.93kB / 131.93kB                                                                                0.4s
 => => sha256:926118dbafe4c55b1234a141ac6cb4632ecf714d133f0205ff538d62b68d165f 23.07MB / 35.65MB                                                                                  1.1s
 => => extracting sha256:ddf74a63f7d8b7d157e5db1a45675a58e304b4c1d425b05c28c835b987623395                                                                                         0.0s
 => [frontend  1/21] FROM nvcr.io/nvidia/base/ubuntu:noble-20250619@sha256:7291df3657ecfcf05332af183b373994eb2cf328c7914944b09e6c437bf2edf8                                       0.0s
 => [wheel_builder  1/24] FROM quay.io/pypa/manylinux_2_28_aarch64:latest@sha256:360bf4ec4349372e9bcfb123bf11bcc4f085072bfa4f3b946d98f5a28f9c03b0                                 0.0s
 => CACHED [dynamo_base 2/7] WORKDIR /opt/dynamo                                                                                                                                  0.0s
 => [dynamo_base 3/7] RUN wget --tries=3 --waitretry=5         "https://github.com/mozilla/sccache/releases/download/v0.14.0/sccache-v0.14.0-aarch64-unknown-linux-musl.tar.gz"   0.7s
 => [dynamo_base 4/7] COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/                                                                                                      0.0s
 => ERROR [dynamo_base 5/7] RUN --mount=type=cache,target=/var/cache/apt,sharing=locked     wget --tries=3 --waitretry=5 https://github.com/nats-io/nats-server/releases/downloa  0.4s
------
 > [dynamo_base 5/7] RUN --mount=type=cache,target=/var/cache/apt,sharing=locked     wget --tries=3 --waitretry=5 https://github.com/nats-io/nats-server/releases/download/v2.10.28/nats-server-v2.10.28-linux/arm64.deb &&     dpkg -i nats-server-v2.10.28-linux/arm64.deb && rm nats-server-v2.10.28-linux/arm64.deb:
0.121 --2026-07-06 23:29:56--  https://github.com/nats-io/nats-server/releases/download/v2.10.28/nats-server-v2.10.28-linux/arm64.deb
0.141 Resolving github.com (github.com)... 140.82.112.4
0.142 Connecting to github.com (github.com)|140.82.112.4|:443... connected.
0.196 HTTP request sent, awaiting response... 404 Not Found
0.338 2026-07-06 23:29:56 ERROR 404: Not Found.
0.338
------
ERROR: failed to solve: process "/bin/sh -c wget --tries=3 --waitretry=5 https://github.com/nats-io/nats-server/releases/download/${NATS_VERSION}/nats-server-${NATS_VERSION}-${ARCH}.deb &&     dpkg -i nats-server-${NATS_VERSION}-${ARCH}.deb && rm nats-server-${NATS_VERSION}-${ARCH}.deb" did not complete successfully: exit code: 8
ojaiyeob@gracehopper:~/kv_cache_offloading$
