ojaiyeob@gracehopper:~/kv_cache_offloading$ git pull origin main
remote: Enumerating objects: 144, done.
remote: Counting objects: 100% (144/144), done.
remote: Compressing objects: 100% (79/79), done.
remote: Total 123 (delta 94), reused 55 (delta 44), pack-reused 0 (from 0)
Receiving objects: 100% (123/123), 56.38 KiB | 1.61 MiB/s, done.
Resolving deltas: 100% (94/94), completed with 21 local objects.
From https://github.com/the308official-afk/kv_cache_offloading
 * branch            main       -> FETCH_HEAD
   8b77e4d..f496154  main       -> origin/main
Updating 8b77e4d..f496154
Fast-forward
 README/MISC.md                                                          | 706 +++----------------------------------------------------------------------------------------------------
 README/README_AGENTBENCH_EXPERIMENTS.md                                 | 232 +++++++++++++++++++++++++++++++++-
 agentbench/run_agentic_hint_sweeps_suite_single_host.sh                 |  18 ++-
 agentbench/run_cache_pinning_microbenchmark_single_host.sh              |  10 ++
 agentbench/run_kv_retention_microbenchmark_single_host.sh               |  10 ++
 agentbench/run_kv_retention_probe_single_host.sh                        |  21 ++++
 agentbench/run_priority_scheduling_microbenchmark_single_host.sh        |  10 ++
 agentbench/run_priority_scheduling_probe_single_host.sh                 |  20 +++
 agentbench/run_speculative_prefill_microbenchmark_single_host.sh        |  10 ++
 agentbench/run_speculative_prefill_probe_single_host.sh                 |  20 +++
 aws/download.sh                                                         |   2 +-
 aws/ssh-to-EC2.sh                                                       |   2 +-
 aws/upload.sh                                                           |   2 +-
 contracts/kv_retention_microbenchmark.contract.md                       |   6 +
 experiments/scripts/retention_probe/build_retention_threshold_report.py |   7 +-
 runtime_instrumentation/build_instrumented_dynamo_images.sh             |   8 ++
 runtime_instrumentation/ensure_experiment_dirs_ready.sh                 |  59 +++++++++
 runtime_instrumentation/precise_sglang_helper.sh                        |  15 ++-
 runtime_instrumentation/prepare_instrumented_dynamo_source.sh           |  11 ++
 runtime_instrumentation/repair_dynamo_clear_kv_source.py                | 172 +++++++++++++++++++++++++
 runtime_instrumentation/reset_experiment_state.sh                       |  18 ++-
 21 files changed, 657 insertions(+), 702 deletions(-)
 create mode 100755 runtime_instrumentation/ensure_experiment_dirs_ready.sh
 create mode 100644 runtime_instrumentation/repair_dynamo_clear_kv_source.py
ojaiyeob@gracehopper:~/kv_cache_offloading$ git pull origin main
From https://github.com/the308official-afk/kv_cache_offloading
 * branch            main       -> FETCH_HEAD
Already up to date.
ojaiyeob@gracehopper:~/kv_cache_offloading$ cd ~/kv_cache_offloading

export DYNAMO_MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-gh200}"   # or gh200
source runtime_instrumentation/dynamo_machine_profile.sh

./run_dynamo_single_host.sh stop || true
docker rm -f dynamo-sglang-worker dynamo-frontend dynamo-etcd dynamo-nats 2>/dev/null || true
docker rmi "$FRONTEND_IMAGE" "$WORKER_IMAGE" || true

./runtime_instrumentation/prepare_instrumented_dynamo_source.sh

DOCKER_BUILD_NO_CACHE=1 LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 \
./runtime_instrumentation/build_instrumented_dynamo_images.sh
Untagged: local/dynamo-frontend:runtime-json-logs-gh200
Deleted: sha256:d06805882680ad0a90c9beba024a1dbbb6ef3d3e37efd23a074faa19c0be8132
Untagged: local/dynamo-sglang:runtime-json-logs-gh200
Deleted: sha256:5133ddf30866ef5b7792292d00b09f56b8431330fe8737b10312d49233304ba9
Preparing instrumented Dynamo source at: /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo
Applying runtime JSON logging patch if needed...
Patch could not be applied cleanly to /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo
Check whether the upstream source version drifted from the patch target.
Runtime JSON logging patch did not apply cleanly.
Continuing with repair steps; they make partially patched source usable.
Applying agent-hint preservation patch if needed...
Patch could not be applied cleanly to /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo
Check whether the upstream source version drifted from the patch target.
Agent-hint preservation patch did not apply cleanly.
Continuing with repair steps; they make fresh upstream clones usable.
Repairing hint-aware worker logging fields...
unchanged: /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo/components/src/dynamo/common/runtime_logging.py
unchanged: /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py
unchanged: /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/llm/prefill_handler.py
Hint-aware worker logging source repair complete.
Repairing hint-preservation source drift...
unchanged: /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo/lib/llm/src/protocols/openai/nvext.rs
unchanged: /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo/lib/llm/src/preprocessor.rs
Hint-preservation source repair complete.
Repairing speculative-prefill source drift...
unchanged: /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs
Speculative-prefill source repair complete.
Repairing clear_kv_blocks source drift...
updated: /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo/lib/llm/src/http/service.rs
updated: /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo/lib/llm/src/http/service/service_v2.rs
updated: /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/init_llm.py
updated: /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo/components/src/dynamo/sglang/request_handlers/handler_base.py
Dynamo clear_kv_blocks source repair complete.
Repairing known Dynamo router field rename mismatch...
No overlap_score_credit references found under /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo
Repairing known Dynamo stream choice stop_reason mismatch...
No stale choice.stop_reason assignment found in /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo/lib/llm/src/preprocessor.rs
Verifying required instrumentation markers...

Instrumented Dynamo source is ready.

Preparation summary:
  runtime_json_patch: drift_repaired
  hint_preservation_patch: drift_repaired

Interpretation:
  - applied_or_already_present: patch matched cleanly or the source was already instrumented
  - drift_repaired: upstream source drifted, but the repair steps restored the required instrumentation

Safe to continue:
  - yes

Next:
  cd /home/central/ojaiyeob/kv_cache_offloading
  DYN_RUNTIME_JSON_LOGS=1 ./runtime_instrumentation/build_instrumented_dynamo_images.sh

Rendering Dynamo frontend Dockerfile
INFO: Generated Dockerfile written to /home/central/ojaiyeob/kv_cache_offloading/upstream/dynamo/container/rendered.Dockerfile
Applying lean frontend Dockerfile adjustment: skip benchmark package install
Building local/dynamo-frontend:runtime-json-logs-gh200 for platform linux/arm64 via docker buildx
[+] Building 387.5s (63/72)                                                                                                                                             docker:default
 => [internal] load build definition from rendered.Dockerfile                                                                                                                     0.0s
 => => transferring dockerfile: 28.89kB                                                                                                                                           0.0s
 => resolve image config for docker-image://docker.io/docker/dockerfile:1.10.0-labs                                                                                               0.9s
 => CACHED docker-image://docker.io/docker/dockerfile:1.10.0-labs@sha256:940282bab7a18daad689c238d407ad22393369ad53c6125c9c00f8be8a9da678                                         0.0s
 => [internal] load metadata for us-central1-docker.pkg.dev/k8s-staging-images/gateway-api-inference-extension/epp:v1.5.0-rc.2                                                    0.7s
 => [internal] load metadata for nvcr.io/nvidia/cuda-dl-base:25.06-cuda12.9-devel-ubuntu24.04                                                                                     0.5s
 => [internal] load metadata for nvcr.io/nvidia/base/ubuntu:noble-20250619                                                                                                        0.5s
 => [internal] load metadata for quay.io/pypa/manylinux_2_28_aarch64:latest                                                                                                       0.4s
 => [internal] load metadata for ghcr.io/astral-sh/uv:latest                                                                                                                     12.4s
 => [internal] load .dockerignore                                                                                                                                                 0.0s
 => => transferring context: 1.27kB                                                                                                                                               0.0s
 => [internal] load build context                                                                                                                                                 0.4s
 => => transferring context: 740.95kB                                                                                                                                             0.4s
 => CACHED [internal] setting cache mount permissions                                                                                                                             0.0s
 => FROM ghcr.io/astral-sh/uv:latest@sha256:4d01caf3b22dfd11003455e2e68153da08c4ee1fa54fdbd166c6282d22693419                                                                      0.5s
 => => resolve ghcr.io/astral-sh/uv:latest@sha256:4d01caf3b22dfd11003455e2e68153da08c4ee1fa54fdbd166c6282d22693419                                                                0.0s
 => => sha256:4d01caf3b22dfd11003455e2e68153da08c4ee1fa54fdbd166c6282d22693419 2.20kB / 2.20kB                                                                                    0.0s
 => => sha256:9e67831eb68ee8c6e19f667aa885feb8c2d25233867de36fbfcf2f1923a15667 669B / 669B                                                                                        0.0s
 => => sha256:958262594baf30cee1190f09c697f79996033d5b13fc34e0b0f34537cf6da5a0 1.30kB / 1.30kB                                                                                    0.0s
 => => sha256:d10b9c79c7fd9ef210d9e52b46a7a088d57409cf73988be61b25dbabd86373ef 25.43MB / 25.43MB                                                                                  0.3s
 => => sha256:4da82d7a3dc5b47ebce79daab8e40a14dded8dba61568e63519379b903e50a9f 94B / 94B                                                                                          0.4s
 => => extracting sha256:d10b9c79c7fd9ef210d9e52b46a7a088d57409cf73988be61b25dbabd86373ef                                                                                         0.1s
 => => extracting sha256:4da82d7a3dc5b47ebce79daab8e40a14dded8dba61568e63519379b903e50a9f                                                                                         0.0s
 => [dynamo_base 1/7] FROM nvcr.io/nvidia/cuda-dl-base:25.06-cuda12.9-devel-ubuntu24.04@sha256:ab128a0b5d4298e62c691e478e42e0af98aecdb71ea17b1fea0261875faf4611                   0.0s
 => CACHED [epp 1/1] FROM us-central1-docker.pkg.dev/k8s-staging-images/gateway-api-inference-extension/epp:v1.5.0-rc.2@sha256:a544513519bd2c04ffffa62119230f056a8722a21ca7816cd  0.0s
 => CACHED [frontend  1/21] FROM nvcr.io/nvidia/base/ubuntu:noble-20250619@sha256:7291df3657ecfcf05332af183b373994eb2cf328c7914944b09e6c437bf2edf8                                0.0s
 => CACHED [dynamo_base 2/7] WORKDIR /opt/dynamo                                                                                                                                  0.0s
 => [wheel_builder_base  1/17] FROM quay.io/pypa/manylinux_2_28_aarch64:latest@sha256:360bf4ec4349372e9bcfb123bf11bcc4f085072bfa4f3b946d98f5a28f9c03b0                            0.0s
 => [dynamo_base 3/7] RUN ARCH_ALT=$([ "arm64" = "amd64" ] && echo "x86_64" || echo "aarch64") &&     wget --tries=3 --waitretry=5         "https://github.com/mozilla/sccache/r  0.8s
 => CACHED [wheel_builder_base  2/17] WORKDIR /workspace                                                                                                                          0.0s
 => [frontend  2/21] RUN --mount=type=cache,target=/var/cache/apt,sharing=locked     apt-get update -y     && apt-get install -y --no-install-recommends         ca-certificate  10.9s
 => [dynamo_base 4/7] COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/                                                                                                      0.0s
 => [dynamo_base 5/7] RUN --mount=type=cache,target=/var/cache/apt,sharing=locked     wget --tries=3 --waitretry=5 https://github.com/nats-io/nats-server/releases/download/v2.  10.8s
 => [frontend  3/21] RUN userdel -r ubuntu > /dev/null 2>&1 || true     && useradd -m -s /bin/bash -g 0 dynamo     && [ `id -u dynamo` -eq 1000 ]     && mkdir -p /home/dynamo/.  0.1s
 => [frontend  4/21] COPY --chown=dynamo: --from=epp /epp /epp                                                                                                                    0.1s
 => [frontend  5/21] COPY --chown=dynamo: container/launch_message/frontend.txt /opt/dynamo/.launch_screen                                                                        0.0s
 => [frontend  6/21] COPY --chown=dynamo: tests /workspace/tests                                                                                                                  0.0s
 => [frontend  7/21] COPY --chown=dynamo: examples /workspace/examples                                                                                                            0.0s
 => [frontend  8/21] COPY --chown=dynamo: benchmarks /workspace/benchmarks                                                                                                        0.0s
 => [frontend  9/21] COPY --chown=dynamo: deploy /workspace/deploy                                                                                                                0.0s
 => [frontend 10/21] COPY --chown=dynamo: components/ /workspace/components/                                                                                                      0.0s
 => [frontend 11/21] COPY --chown=dynamo: recipes/ /workspace/recipes/                                                                                                            0.0s
 => [frontend 12/21] COPY --chown=dynamo: ATTRIBUTION* LICENSE /workspace/                                                                                                        0.0s
 => [dynamo_base 6/7] RUN wget --tries=3 --waitretry=5 https://github.com/etcd-io/etcd/releases/download/v3.5.21/etcd-v3.5.21-linux-arm64.tar.gz -O /tmp/etcd.tar.gz &&     mkdi  0.9s
 => [dynamo_base 7/7] RUN ARCH_ALT=$([ "arm64" = "amd64" ] && echo "x86_64" || echo "aarch64") &&     RUSTARCH="${ARCH_ALT}-unknown-linux-gnu" &&     wget --tries=3 --waitretry  8.7s
 => [wheel_builder_base  3/17] COPY --from=dynamo_base /usr/local/cuda /usr/local/cuda                                                                                            2.1s
 => [frontend 13/21] COPY --chown=dynamo: --from=dynamo_base /bin/uv /bin/uvx /bin/                                                                                               1.7s
 => [wheel_builder_base  4/17] COPY --from=dynamo_base /etc/ld.so.conf.d/hpcx.conf /etc/ld.so.conf.d/hpcx.conf                                                                    0.0s
 => [wheel_builder_base  5/17] COPY --from=dynamo_base /usr/local/rustup /usr/local/rustup                                                                                        0.3s
 => [wheel_builder_base  6/17] COPY --from=dynamo_base /usr/local/cargo /usr/local/cargo                                                                                          0.0s
 => [wheel_builder_base  7/17] RUN --mount=type=cache,target=/var/cache/dnf,sharing=locked     dnf install -y almalinux-release-synergy &&     dnf config-manager --set-enabled  49.5s
 => [wheel_builder_base  8/17] RUN HWLOC_SERIES="$(echo "2.12.0" | cut -d. -f1-2)" &&     cd /tmp &&     curl --retry 3 -LO "https://download.open-mpi.org/release/hwloc/v${HWL  12.5s
 => [wheel_builder_base  9/17] RUN set -eux;     ARCH_ALT=$([ "arm64" = "amd64" ] && echo "x86_64" || echo "aarch64");     PROTOC_VERSION=25.3;     case "${ARCH_ALT}" in         0.8s
 => [wheel_builder_base 10/17] RUN --mount=type=cache,target=/root/.cache/uv,sharing=shared     export UV_CACHE_DIR=/root/.cache/uv UV_HTTP_TIMEOUT=300 UV_HTTP_RETRIES=5 &&      0.9s
 => [wheel_builder_base 11/17] RUN ARCH_ALT=$([ "arm64" = "amd64" ] && echo "x86_64" || echo "aarch64") &&     git clone --depth 1 --branch v2.5.1 https://github.com/NVIDIA/gd  17.3s
 => [wheel_builder_base 12/17] COPY --from=dynamo_base /usr/local/bin/sccache /opt/sccache/sccache                                                                                0.0s
 => [wheel_builder_base 13/17] COPY container/use-sccache.sh /tmp/use-sccache.sh                                                                                                  0.0s
 => [wheel_builder_base 14/17] RUN if [ "$USE_SCCACHE" = "true" ]; then         ln -s /opt/sccache/sccache /usr/local/bin/sccache &&         /tmp/use-sccache.sh install;     fi  0.1s
 => [wheel_builder_base 15/17] RUN --mount=type=secret,id=aws-web-identity-token,target=/run/secrets/aws-token     --mount=type=secret,id=aws-role-arn,env=AWS_ROLE_ARN     exp  51.2s
 => [wheel_builder_base 16/17] RUN --mount=type=secret,id=aws-web-identity-token,target=/run/secrets/aws-token     --mount=type=secret,id=aws-role-arn,env=AWS_ROLE_ARN     exp  56.8s
 => [wheel_builder_base 17/17] RUN --mount=type=secret,id=aws-web-identity-token,target=/run/secrets/aws-token     --mount=type=secret,id=aws-role-arn,env=AWS_ROLE_ARN     exp  24.2s
 => [wheel_builder 1/9] RUN --mount=type=secret,id=aws-web-identity-token,target=/run/secrets/aws-token     --mount=type=secret,id=aws-role-arn,env=AWS_ROLE_ARN     export AWS  37.3s
 => [runtime_wheel_builder 1/6] COPY .cargo/ /opt/dynamo/.cargo/                                                                                                                  0.0s
 => [runtime_wheel_builder 2/6] COPY pyproject.toml README.md LICENSE Cargo.toml Cargo.lock rust-toolchain.toml hatch_build.py /opt/dynamo/                                       0.0s
 => [runtime_wheel_builder 3/6] COPY lib/ /opt/dynamo/lib/                                                                                                                        0.1s
 => [runtime_wheel_builder 4/6] COPY components/ /opt/dynamo/components/                                                                                                          0.0s
 => ERROR [runtime_wheel_builder 5/6] RUN --mount=type=secret,id=aws-web-identity-token,target=/run/secrets/aws-token     --mount=type=secret,id=aws-role-arn,env=AWS_ROLE_ARN  129.9s
 => [wheel_builder 2/9] RUN echo "/opt/nvidia/nvda_nixl/lib64" > /etc/ld.so.conf.d/nixl.conf &&     echo "/opt/nvidia/nvda_nixl/lib64/plugins" >> /etc/ld.so.conf.d/nixl.conf &&  0.1s
 => [wheel_builder 3/9] RUN --mount=type=secret,id=aws-web-identity-token,target=/run/secrets/aws-token     --mount=type=secret,id=aws-role-arn,env=AWS_ROLE_ARN     --mount=ty  27.1s
 => [wheel_builder 4/9] COPY .cargo/ /opt/dynamo/.cargo/                                                                                                                          0.0s
 => [wheel_builder 5/9] COPY pyproject.toml README.md LICENSE Cargo.toml Cargo.lock rust-toolchain.toml hatch_build.py /opt/dynamo/                                               0.0s
 => [wheel_builder 6/9] COPY lib/ /opt/dynamo/lib/                                                                                                                                0.1s
 => [wheel_builder 7/9] COPY components/ /opt/dynamo/components/                                                                                                                  0.1s
 => CANCELED [wheel_builder 8/9] RUN --mount=type=secret,id=aws-web-identity-token,target=/run/secrets/aws-token     --mount=type=secret,id=aws-role-arn,env=AWS_ROLE_ARN     -  67.1s
------
 > [runtime_wheel_builder 5/6] RUN --mount=type=secret,id=aws-web-identity-token,target=/run/secrets/aws-token     --mount=type=secret,id=aws-role-arn,env=AWS_ROLE_ARN     --mount=type=cache,target=/root/.cargo/registry,sharing=shared     --mount=type=cache,target=/root/.cargo/git,sharing=shared     --mount=type=cache,target=/root/.cache/uv,sharing=shared     export AWS_WEB_IDENTITY_TOKEN_FILE=/run/secrets/aws-token &&     export UV_CACHE_DIR=/root/.cache/uv &&     export SCCACHE_S3_KEY_PREFIX=${SCCACHE_S3_KEY_PREFIX:-arm64} &&     if [ "$USE_SCCACHE" = "true" ]; then         eval $(/tmp/use-sccache.sh setup-env cmake);     fi &&     mkdir -p /opt/dynamo/target &&     source /workspace/.venv/bin/activate &&     cd /opt/dynamo &&     uv build --wheel --out-dir /opt/dynamo/dist &&     cd /opt/dynamo/lib/bindings/python &&     if [ "false" = "true" ]; then         maturin build --release --features "media-ffmpeg,kv-indexer" --out /opt/dynamo/dist;     else         maturin build --release --features "kv-indexer" --out /opt/dynamo/dist;     fi &&     /tmp/use-sccache.sh show-stats "Dynamo Runtime":
0.127 Building wheel...
1.039 Successfully built dist/ai_dynamo-1.2.0-py3-none-any.whl
1.101     Updating crates.io index
7.651  Downloading crates ...
7.882   Downloaded aligned v0.4.3
7.898   Downloaded aligned-vec v0.6.4
7.904   Downloaded crunchy v0.2.4
7.906   Downloaded anstream v1.0.0
7.910   Downloaded android_system_properties v0.1.5
7.915   Downloaded adler2 v2.0.1
7.920   Downloaded anstyle v1.0.14
7.931   Downloaded ahash v0.8.12
7.937   Downloaded allocator-api2 v0.2.21
7.941   Downloaded arrayref v0.3.9
7.944   Downloaded axum-core v0.5.6
7.949   Downloaded async-trait v0.1.89
7.954   Downloaded backon v1.6.0
7.958   Downloaded async-stream v0.3.6
7.962   Downloaded avif-serialize v0.8.8
7.965   Downloaded bincode v1.3.3
7.969   Downloaded crossbeam v0.8.4
7.972   Downloaded crossbeam-deque v0.8.6
7.976   Downloaded crossbeam-channel v0.5.15
7.982   Downloaded cpufeatures v0.3.0
7.985   Downloaded darling_macro v0.23.0
7.987   Downloaded bincode_derive v2.0.1
7.990   Downloaded clap_lex v1.1.0
7.993   Downloaded autocfg v1.5.0
7.996   Downloaded color_quant v1.1.0
7.999   Downloaded const-random-macro v0.1.16
8.002   Downloaded byteorder-lite v0.1.0
8.005   Downloaded cpufeatures v0.2.17
8.008   Downloaded crossbeam-queue v0.3.12
8.011   Downloaded bit-set v0.8.0
8.014   Downloaded darling_macro v0.20.11
8.016   Downloaded colored v3.1.1
8.021   Downloaded gloo-timers v0.3.0
8.024   Downloaded byteorder v1.5.0
8.027   Downloaded core-foundation v0.9.4
8.031   Downloaded fixedbitset v0.5.7
8.035   Downloaded core-foundation v0.10.1
8.038   Downloaded cmake v0.1.58
8.041   Downloaded cexpr v0.6.0
8.045   Downloaded either v1.15.0
8.048   Downloaded getset v0.1.6
8.051   Downloaded futures-core v0.3.32
8.055   Downloaded fax_derive v0.2.0
8.057   Downloaded const-oid v0.9.6
8.061   Downloaded hex v0.4.3
8.064   Downloaded futures-macro v0.3.32
8.067   Downloaded hashlink v0.10.0
8.070   Downloaded dirs v6.0.0
8.073   Downloaded hermit-abi v0.5.2
8.076   Downloaded clap v4.6.1
8.087   Downloaded half v2.7.1
8.091   Downloaded enum-ordinalize v4.3.2
8.094   Downloaded bumpalo v3.20.2
8.098   Downloaded daachorse v1.0.1
8.103   Downloaded darling v0.23.0
8.110   Downloaded http-body v1.0.1
8.112   Downloaded home v0.5.12
8.115   Downloaded humantime v2.3.0
8.118   Downloaded enum-ordinalize-derive v4.3.2
8.121   Downloaded ident_case v1.0.1
8.123   Downloaded hyper-rustls v0.27.9
8.126   Downloaded hashbrown v0.12.3
8.131   Downloaded event-listener-strategy v0.5.4
8.134   Downloaded iana-time-zone v0.1.65
8.138   Downloaded hf-hub v0.4.3
8.142   Downloaded derive_builder_macro v0.20.2
8.145   Downloaded hostname v0.4.2
8.148   Downloaded heck v0.5.0
8.151   Downloaded darling v0.20.11
8.157   Downloaded is_terminal_polyfill v1.70.2
8.160   Downloaded glob v0.3.3
8.163   Downloaded inventory v0.3.24
8.167   Downloaded is-macro v0.3.7
8.169   Downloaded find-msvc-tools v0.1.9
8.172   Downloaded itoa v1.0.18
8.175   Downloaded json5 v0.4.1
8.178   Downloaded icu_properties v2.2.0
8.182   Downloaded equator v0.4.2
8.185   Downloaded h2 v0.4.13
8.193   Downloaded json-patch v4.1.0
8.198   Downloaded leb128fmt v0.1.0
8.200   Downloaded indexmap v1.9.3
8.204   Downloaded kqueue v1.1.1
8.208   Downloaded malachite-bigint v0.2.3
8.211   Downloaded jsonpath-rust v0.7.5
8.215   Downloaded futures-executor v0.3.32
8.218   Downloaded deranged v0.5.8
8.220   Downloaded hashbrown v0.16.1
8.227   Downloaded jsonptr v0.7.1
8.231   Downloaded macro_rules_attribute v0.2.2
8.234   Downloaded jwalk v0.8.1
8.238   Downloaded memo-map v0.3.3
8.241   Downloaded malachite v0.4.22
8.243   Downloaded image-webp v0.2.4
8.247   Downloaded maybe-rayon v0.1.1
8.249   Downloaded matrixmultiply v0.3.10
8.254   Downloaded indicatif v0.17.11
8.259   Downloaded log v0.4.29
8.263   Downloaded libredox v0.1.16
8.265   Downloaded loop9 v0.1.5
8.267   Downloaded indicatif v0.18.4
8.272   Downloaded jiff-static v0.2.24
8.276   Downloaded indexmap v2.14.0
8.282   Downloaded local-ip-address v0.6.12
8.285   Downloaded icu_properties_data v2.2.0
8.297   Downloaded mime_guess v2.0.5
8.300   Downloaded kube-client v2.0.1
8.306   Downloaded event-listener v5.4.1
8.309   Downloaded num-conv v0.2.1
8.311   Downloaded memmap2 v0.9.10
8.314   Downloaded darling_core v0.21.3
8.321   Downloaded number_prefix v0.4.0
8.323   Downloaded monostate-impl v0.1.18
8.325   Downloaded monostate v0.1.18
8.328   Downloaded mime v0.3.17
8.331   Downloaded json-five v0.3.1
8.334   Downloaded onig v6.5.1
8.337   Downloaded objc2-quartz-core v0.3.2
8.341   Downloaded num-derive v0.4.2
8.344   Downloaded new_debug_unreachable v1.0.6
8.346   Downloaded openssl-probe v0.1.6
8.349   Downloaded libm v0.2.16
8.361   Downloaded option-ext v0.2.0
8.363   Downloaded kube-derive v2.0.1
8.366   Downloaded os_info v3.14.0
8.370   Downloaded percent-encoding v2.3.2
8.373   Downloaded paste v1.0.15
8.377   Downloaded pest_generator v2.8.6
8.380   Downloaded pem-rfc7468 v0.7.0
8.383   Downloaded pear_codegen v0.2.9
8.385   Downloaded pear v0.2.9
8.388   Downloaded num-complex v0.4.6
8.391   Downloaded phf v0.11.3
8.393   Downloaded pkcs8 v0.10.2
8.397   Downloaded objc2-io-surface v0.3.2
8.400   Downloaded once_cell_polyfill v1.70.2
8.402   Downloaded potential_utf v0.1.5
8.404   Downloaded getrandom v0.4.2
8.409   Downloaded num-bigint v0.4.6
8.415   Downloaded prost v0.13.5
8.418   Downloaded proc-macro2 v1.0.106
8.422   Downloaded objc2-core-text v0.3.2
8.426   Downloaded pulldown-cmark-to-cmark v22.0.0
8.429   Downloaded mio v1.1.1
8.436   Downloaded prost-types v0.14.3
8.438   Downloaded objc2-cloud-kit v0.3.2
8.445   Downloaded prost v0.14.3
8.447   Downloaded pyo3-build-config v0.23.5
8.450   Downloaded phf_codegen v0.11.3
8.452   Downloaded quote v1.0.45
8.456   Downloaded rand_chacha v0.9.0
8.458   Downloaded async-nats v0.45.0
8.470   Downloaded rayon-cond v0.4.0
8.472   Downloaded profiling-procmacros v1.0.17
8.474   Downloaded objc2-core-foundation v0.3.2
8.482   Downloaded redox_syscall v0.7.4
8.485   Downloaded objc2 v0.6.4
8.497   Downloaded rand_chacha v0.3.1
8.499   Downloaded object_store v0.12.5
8.508   Downloaded rustls-native-certs v0.8.3
8.512   Downloaded rmp-serde v1.3.1
8.515   Downloaded num_threads v0.1.7
8.517   Downloaded rustpython-parser-vendored v0.4.0
8.519   Downloaded nix v0.30.1
8.532   Downloaded schemars_derive v1.2.1
8.535   Downloaded derive_more-impl v1.0.0
8.540   Downloaded protobuf v3.7.2
8.553   Downloaded ref-cast v1.0.25
8.557   Downloaded secrecy v0.10.3
8.559   Downloaded rustpython-ast v0.4.0
8.562   Downloaded parking_lot_core v0.9.12
8.564   Downloaded rustls-pemfile v2.2.0
8.568   Downloaded serde_urlencoded v0.7.1
8.570   Downloaded serde-value v0.7.0
8.572   Downloaded serde_spanned v0.6.9
8.575   Downloaded rustpython-parser-core v0.4.0
8.576   Downloaded rand_core v0.9.5
8.578   Downloaded semver v1.0.28
8.581   Downloaded rustversion v1.0.22
8.585   Downloaded opentelemetry-appender-tracing v0.31.1
8.587   Downloaded regex v1.12.3
8.593   Downloaded scopeguard v1.2.0
8.595   Downloaded reqwest v0.12.28
8.601   Downloaded derive_builder v0.20.2
8.608   Downloaded slotmap v1.1.1
8.611   Downloaded parking v2.2.1
8.612   Downloaded serde_nanos v0.1.4
8.614   Downloaded serde_spanned v1.1.1
8.616   Downloaded serde_repr v0.1.20
8.619   Downloaded static_assertions v1.1.0
8.621   Downloaded system-configuration v0.7.0
8.623   Downloaded thiserror v2.0.18
8.630   Downloaded quinn-udp v0.5.14
8.633   Downloaded opentelemetry-proto v0.31.0
8.637   Downloaded siphasher v1.0.2
8.639   Downloaded thread_local v1.1.9
8.641   Downloaded flate2 v1.1.9
8.647   Downloaded serde v1.0.228
8.651   Downloaded schemars v0.9.0
8.666   Downloaded tokio-macros v2.6.1
8.668   Downloaded serde_derive_internals v0.29.1
8.670   Downloaded serde_path_to_error v0.1.20
8.672   Downloaded sync_wrapper v1.0.2
8.674   Downloaded subtle v2.6.1
8.676   Downloaded toml_parser v1.1.2+spec-1.1.0
8.679   Downloaded icu_collections v2.2.0
8.686   Downloaded signatory v0.27.1
8.690   Downloaded toml v0.8.23
8.693   Downloaded tonic-prost v0.14.5
8.694   Downloaded pyo3-ffi v0.23.5
8.702   Downloaded ppv-lite86 v0.2.21
8.704   Downloaded rust-embed v8.11.0
8.713   Downloaded js-sys v0.3.95
8.716   Downloaded phf_shared v0.11.3
8.718   Downloaded malachite-nz v0.4.22
8.796   Downloaded unicode-general-category v1.1.0
8.800   Downloaded utf8parse v0.2.2
8.802   Downloaded utoipa-swagger-ui v9.0.2
8.804   Downloaded unic-ucd-ident v0.9.0
8.806   Downloaded uncased v0.9.10
8.807   Downloaded prettyplease v0.2.37
8.811   Downloaded unit-prefix v0.5.2
8.812   Downloaded unicode_names2_generator v1.3.0
8.814   Downloaded sharded-slab v0.1.7
8.817   Downloaded unty v0.0.4
8.819   Downloaded serde_yaml v0.9.34+deprecated
8.822   Downloaded unic-char-range v0.9.0
8.824   Downloaded tracing-attributes v0.1.31
8.827   Downloaded untrusted v0.9.0
8.829   Downloaded wasm-bindgen-shared v0.2.118
8.830   Downloaded unicase v2.9.0
8.832   Downloaded version_check v0.9.5
8.834   Downloaded socket2 v0.6.3
8.835   Downloaded socket2 v0.5.10
8.838   Downloaded webpki-roots v0.26.11
8.839   Downloaded web-time v1.1.0
8.841   Downloaded validator_derive v0.20.0
8.843   Downloaded version-compare v0.2.1
8.845   Downloaded tinyvec v1.11.0
8.847   Downloaded tracing-subscriber v0.3.23
8.856   Downloaded windows-core v0.62.2
8.859   Downloaded thiserror-impl v1.0.69
8.861   Downloaded synstructure v0.13.2
8.862   Downloaded simd-adler32 v0.3.9
8.864   Downloaded wasm-bindgen-macro v0.2.118
8.865   Downloaded wasm-bindgen-futures v0.4.68
8.866   Downloaded utf16_iter v1.0.5
8.867   Downloaded unicode-xid v0.2.6
8.869   Downloaded tonic-build v0.14.5
8.870   Downloaded tokio-tungstenite v0.26.2
8.872   Downloaded tokio-rayon v2.1.0
8.874   Downloaded toml_write v0.1.2
8.875   Downloaded rustls-webpki v0.103.13
8.878   Downloaded toml v1.1.2+spec-1.1.0
8.883   Downloaded winapi-util v0.1.11
8.884   Downloaded tonic-prost-build v0.14.5
8.886   Downloaded pcre2-sys v0.2.10
8.900   Downloaded windows-interface v0.59.3
8.901   Downloaded wasi v0.11.1+wasi-snapshot-preview1
8.903   Downloaded wasm-metadata v0.244.0
8.905   Downloaded unic-common v0.9.0
8.906   Downloaded tokio-timerfd v0.2.0
8.907   Downloaded pest v2.8.6
8.912   Downloaded tracing-core v0.1.36
8.915   Downloaded unicode-normalization-alignments v0.1.12
8.917   Downloaded futures-util v0.3.32
8.932   Downloaded walkdir v2.5.0
8.934   Downloaded unsafe-libyaml v0.2.11
8.937   Downloaded windows-strings v0.5.1
8.939   Downloaded unicode-ident v1.0.24
8.942   Downloaded typenum v1.20.0
8.945   Downloaded uuid v1.23.1
8.948   Downloaded yoke v0.8.2
8.950   Downloaded utf-8 v0.7.6
8.952   Downloaded unic-ucd-version v0.9.0
8.953   Downloaded tower-http v0.6.8
8.962   Downloaded wit-bindgen-rust-macro v0.51.0
8.963   Downloaded wasm-streams v0.4.2
8.968   Downloaded zmij v1.0.21
8.970   Downloaded windows-implement v0.60.2
8.971   Downloaded zeroize v1.8.2
8.973   Downloaded wasm-bindgen-macro-support v0.2.118
8.975   Downloaded utoipa-gen v5.4.0
8.980   Downloaded tungstenite v0.26.2
8.983   Downloaded weezl v0.1.12
8.986   Downloaded wasip3 v0.4.0+wasi-0.3.0-rc-2026-01-06
8.989   Downloaded windows-targets v0.53.5
8.991   Downloaded windows-targets v0.48.5
8.992   Downloaded wasmparser v0.244.0
9.000   Downloaded zmq-sys v0.12.0
9.001   Downloaded tokenizers v0.21.4
9.010   Downloaded zerovec-derive v0.11.3
9.011   Downloaded rustix v0.38.44
9.038   Downloaded xxhash-rust v0.8.15
9.040   Downloaded y4m v0.8.0
9.042   Downloaded zerofrom v0.1.7
9.043   Downloaded windows-registry v0.6.1
9.045   Downloaded tokio-util v0.7.18
9.053   Downloaded pulldown-cmark v0.13.3
9.058   Downloaded aws-lc-sys v0.40.0
9.278   Downloaded zune-inflate v0.2.54
9.281   Downloaded yansi v1.0.1
9.284   Downloaded zopfli v0.8.3
9.287   Downloaded wasip2 v1.0.3+wasi-0.2.9
9.291   Downloaded zip v2.4.2
9.296   Downloaded zip v3.0.0
9.301   Downloaded zerotrie v0.2.4
9.305   Downloaded zerovec v0.11.6
9.311   Downloaded tracing v0.1.44
9.324   Downloaded windows_i686_gnullvm v0.52.6
9.331   Downloaded winapi v0.3.9
9.366   Downloaded time v0.3.47
9.379   Downloaded winnow v1.0.2
9.388   Downloaded objc2-foundation v0.3.2
9.406   Downloaded unicode-width v0.2.2
9.412   Downloaded zlib-rs v0.6.3
9.417   Downloaded zerocopy-derive v0.8.48
9.426   Downloaded zune-jpeg v0.5.15
9.430   Downloaded wit-parser v0.244.0
9.467   Downloaded wit-component v0.244.0
9.523   Downloaded zerocopy v0.8.48
9.544   Downloaded unicode_names2 v1.3.0
9.550   Downloaded web-sys v0.3.95
9.653   Downloaded rustix v1.1.4
9.679   Downloaded windows_x86_64_gnullvm v0.52.6
9.686   Downloaded windows_x86_64_gnu v0.52.6
9.698   Downloaded fiat-crypto v0.2.9
9.706   Downloaded windows_x86_64_msvc v0.52.6
9.715   Downloaded windows_aarch64_gnullvm v0.52.6
9.722   Downloaded windows_aarch64_gnullvm v0.48.5
9.728   Downloaded cudarc v0.19.3
9.745   Downloaded rustls v0.23.39
9.757   Downloaded windows_x86_64_gnullvm v0.48.5
9.763   Downloaded onig_sys v69.9.1
9.779   Downloaded fastokens v0.1.1
9.787   Downloaded windows_i686_msvc v0.48.5
9.797   Downloaded syn v2.0.117
9.806   Downloaded winnow v0.7.15
9.815   Downloaded petgraph v0.7.1
9.830   Downloaded webpki-roots v1.0.7
9.834   Downloaded quinn-proto v0.11.14
9.840   Downloaded ndarray v0.16.1
9.853   Downloaded quick-xml v0.38.4
9.858   Downloaded ureq v2.12.1
9.862   Downloaded tracing-opentelemetry v0.32.1
9.867   Downloaded petgraph v0.8.3
9.884   Downloaded windows_x86_64_msvc v0.48.5
9.894   Downloaded windows_x86_64_gnullvm v0.53.1
9.903   Downloaded rustls-webpki v0.102.8
9.924   Downloaded windows_aarch64_msvc v0.48.5
9.933   Downloaded windows_aarch64_gnullvm v0.53.1
9.942   Downloaded windows_aarch64_msvc v0.52.6
9.952   Downloaded windows_x86_64_msvc v0.53.1
9.961   Downloaded windows_x86_64_gnu v0.48.5
9.972   Downloaded windows_i686_msvc v0.53.1
9.983   Downloaded windows_i686_gnullvm v0.53.1
9.993   Downloaded windows_i686_msvc v0.52.6
10.00   Downloaded pyo3 v0.23.5
10.03   Downloaded windows_x86_64_gnu v0.53.1
10.04   Downloaded windows_i686_gnu v0.52.6
10.05   Downloaded windows_i686_gnu v0.48.5
10.06   Downloaded windows_aarch64_msvc v0.53.1
10.07   Downloaded zeromq-src v0.2.6+4.3.4
10.14   Downloaded windows_i686_gnu v0.53.1
10.16   Downloaded curve25519-dalek v4.1.3
10.16   Downloaded zmq v0.10.0
10.17   Downloaded yaml-rust2 v0.10.4
10.17   Downloaded wit-bindgen v0.57.1
10.18   Downloaded wit-bindgen v0.51.0
10.18   Downloaded url v2.5.8
10.18   Downloaded tower v0.5.3
10.19   Downloaded exr v1.74.0
10.20   Downloaded wit-bindgen-rust v0.51.0
10.20   Downloaded encoding_rs v0.8.35
10.22   Downloaded spm_precompiled v0.1.4
10.23   Downloaded rustpython-parser v0.4.0
10.24   Downloaded zune-core v0.5.1
10.24   Downloaded wit-bindgen-core v0.51.0
10.24   Downloaded unicode_categories v0.1.1
10.24   Downloaded tonic v0.13.1
10.25   Downloaded tokio v1.48.0
10.29   Downloaded ring v0.17.14
10.32   Downloaded writeable v0.6.3
10.33   Downloaded write16 v1.0.0
10.33   Downloaded utoipa v5.4.0
10.33   Downloaded zerofrom-derive v0.1.7
10.33   Downloaded yoke-derive v0.8.2
10.33   Downloaded windows-result v0.4.1
10.33   Downloaded windows-link v0.2.1
10.34   Downloaded wasm-bindgen v0.2.118
10.34   Downloaded serde_with v3.18.0
10.35   Downloaded windows-targets v0.52.6
10.35   Downloaded wasm-encoder v0.244.0
10.35   Downloaded unicode-segmentation v1.13.2
10.36   Downloaded tokio-websockets v0.10.1
10.36   Downloaded serde_json v1.0.149
10.37   Downloaded winapi-i686-pc-windows-gnu v0.4.0
10.48   Downloaded virtue v0.0.18
10.48   Downloaded tokio-stream v0.1.18
10.49   Downloaded want v0.3.1
10.49   Downloaded valuable v0.1.1
10.49   Downloaded v_frame v0.3.9
10.49   Downloaded nom v8.0.0
10.50   Downloaded strum v0.27.2
10.50   Downloaded rustls-pki-types v1.14.1
10.50   Downloaded validator v0.20.0
10.50   Downloaded signal-hook-registry v1.4.8
10.50   Downloaded esaxx-rs v0.1.10
10.51   Downloaded tryhard v0.5.2
10.51   Downloaded utf8_iter v1.0.4
10.51   Downloaded rav1e v0.8.1
10.54   Downloaded prost-types v0.13.5
10.54   Downloaded linux-raw-sys v0.4.15
10.58   Downloaded tonic-build v0.13.1
10.58   Downloaded tonic v0.14.5
10.59   Downloaded png v0.18.1
10.59   Downloaded tokio-rustls v0.26.4
10.59   Downloaded pyo3-async-runtimes v0.23.0
10.60   Downloaded tracing-log v0.2.0
10.60   Downloaded unindent v0.2.4
10.60   Downloaded unic-char-property v0.9.0
10.60   Downloaded toml_edit v0.22.27
10.61   Downloaded toml_datetime v1.1.1+spec-1.1.0
10.61   Downloaded thiserror-impl v2.0.18
10.61   Downloaded system-configuration-sys v0.6.0
10.61   Downloaded strum_macros v0.27.2
10.61   Downloaded strsim v0.11.1
10.61   Downloaded smallvec v1.15.1
10.62   Downloaded slab v0.4.12
10.62   Downloaded shlex v1.3.0
10.62   Downloaded serde_with_macros v3.18.0
10.62   Downloaded security-framework v3.7.0
10.63   Downloaded ryu v1.0.23
10.63   Downloaded windows-sys v0.59.0
10.68   Downloaded rustc_version v0.4.1
10.68   Downloaded tiktoken-rs v0.9.1
10.72   Downloaded redox_syscall v0.5.18
10.72   Downloaded windows-sys v0.61.2
10.77   Downloaded windows-sys v0.60.2
10.83   Downloaded opentelemetry_sdk v0.31.0
10.83   Downloaded toml_datetime v0.6.11
10.84   Downloaded tmq v0.5.0
10.84   Downloaded tiff v0.11.3
10.84   Downloaded thiserror v1.0.69
10.85   Downloaded target-lexicon v0.12.16
10.85   Downloaded k8s-openapi v0.26.1
11.08   Downloaded stable_deref_trait v1.2.1
11.08   Downloaded windows-sys v0.48.0
11.15   Downloaded spin v0.9.8
11.15   Downloaded windows-sys v0.52.0
11.20   Downloaded signature v2.2.0
11.20   Downloaded serde_derive v1.0.228
11.21   Downloaded serde_core v1.0.228
11.21   Downloaded schemars v1.2.1
11.23   Downloaded rust-embed-impl v8.11.0
11.23   Downloaded regex-automata v0.4.14
11.24   Downloaded ref-cast-impl v1.0.25
11.24   Downloaded ravif v0.13.0
11.24   Downloaded r-efi v5.3.0
11.25   Downloaded quick-error v2.0.1
11.25   Downloaded pyo3-async-runtimes-macros v0.23.0
11.25   Downloaded powerfmt v0.2.0
11.25   Downloaded winapi-x86_64-pc-windows-gnu v0.4.0
11.36   Downloaded linux-raw-sys v0.12.1
11.42   Downloaded nixl-sys v0.10.1
11.42   Downloaded itertools v0.11.0
11.42   Downloaded etcd-client v0.17.0
11.43   Downloaded unic-emoji-char v0.9.0
11.43   Downloaded unchecked-index v0.2.2
11.43   Downloaded ucd-trie v0.1.7
11.43   Downloaded typeid v1.0.3
11.43   Downloaded try-lock v0.2.5
11.43   Downloaded tracing-serde v0.2.0
11.44   Downloaded tower-service v0.3.3
11.44   Downloaded tower-layer v0.3.3
11.44   Downloaded tinyvec_macros v0.1.1
11.44   Downloaded tinystr v0.8.3
11.44   Downloaded tiny-keccak v2.0.2
11.44   Downloaded time-macros v0.2.27
11.44   Downloaded system-deps v6.2.2
11.45   Downloaded spki v0.7.3
11.45   Downloaded sha2 v0.10.9
11.45   Downloaded schannel v0.1.29
11.45   Downloaded opentelemetry v0.31.0
11.46   Downloaded objc2-core-image v0.3.2
11.46   Downloaded minimal-lexical v0.2.1
11.46   Downloaded derive_more-impl v2.1.1
11.47   Downloaded fancy-regex v0.17.0
11.47   Downloaded pyo3-macros-backend v0.23.5
11.47   Downloaded rayon-core v1.13.0
11.48   Downloaded prost-build v0.14.3
11.48   Downloaded pem v3.0.6
11.48   Downloaded rmp v0.8.15
11.49   Downloaded rand v0.8.6
11.49   Downloaded quinn v0.11.9
11.49   Downloaded timerfd v1.6.0
11.49   Downloaded time-core v0.1.8
11.49   Downloaded socks v0.3.4
11.49   Downloaded pest_derive v2.8.6
11.50   Downloaded simd_helpers v0.1.0
11.50   Downloaded serde-untagged v0.1.9
11.50   Downloaded security-framework-sys v2.17.0
11.50   Downloaded pythonize v0.23.0
11.50   Downloaded pathdiff v0.2.3
11.50   Downloaded num-traits v0.2.19
11.51   Downloaded memchr v2.8.0
11.51   Downloaded portable-atomic-util v0.2.7
11.51   Downloaded pastey v0.1.1
11.51   Downloaded opentelemetry-otlp v0.31.1
11.52   Downloaded security-framework v2.11.1
11.52   Downloaded ed25519-dalek v2.2.0
11.52   Downloaded shell-words v1.1.1
11.52   Downloaded sha1 v0.10.6
11.53   Downloaded neli v0.7.4
11.53   Downloaded ndarray-interp v0.5.0
11.53   Downloaded once_cell v1.21.4
11.53   Downloaded tempfile v3.27.0
11.54   Downloaded rustls-native-certs v0.7.3
11.54   Downloaded rgb v0.8.53
11.54   Downloaded redox_users v0.5.2
11.54   Downloaded rust-ini v0.21.3
11.54   Downloaded ron v0.12.1
11.55   Downloaded pxfm v0.1.29
11.57   Downloaded rustc-hash v1.1.0
11.57   Downloaded regex-syntax v0.8.10
11.58   Downloaded miniz_oxide v0.8.9
11.58   Downloaded same-file v1.0.6
11.58   Downloaded r-efi v6.0.0
11.59   Downloaded kube-runtime v2.0.1
11.59   Downloaded fancy-regex v0.13.0
11.59   Downloaded objc2-user-notifications v0.3.2
11.59   Downloaded objc2-core-data v0.3.2
11.60   Downloaded malachite-base v0.4.22
11.67   Downloaded rustc-hash v2.1.2
11.67   Downloaded rust-embed-utils v8.11.0
11.67   Downloaded rayon v1.12.0
11.68   Downloaded opentelemetry-http v0.31.0
11.68   Downloaded nom v7.1.3
11.69   Downloaded imgref v1.12.0
11.69   Downloaded rand_core v0.6.4
11.69   Downloaded rand v0.9.4
11.69   Downloaded objc2-ui-kit v0.3.2
11.72   Downloaded libc v0.2.186
11.76   Downloaded modelexpress-common v0.3.0
11.76   Downloaded derive_more v2.1.1
11.77   Downloaded der v0.7.10
11.78   Downloaded rawpointer v0.2.1
11.78   Downloaded qoi v0.4.1
11.78   Downloaded prost-derive v0.13.5
11.78   Downloaded plain v0.2.3
11.78   Downloaded pkg-config v0.3.33
11.78   Downloaded pin-project-lite v0.2.17
11.79   Downloaded pin-project-internal v1.1.11
11.79   Downloaded modelexpress-client v0.3.0
11.80   Downloaded figment v0.10.19
11.80   Downloaded py_literal v0.4.0
11.80   Downloaded notify v6.1.1
11.80   Downloaded ndarray-npy v0.9.1
11.80   Downloaded jiff v0.2.24
11.82   Downloaded prometheus v0.14.0
11.82   Downloaded profiling v1.0.17
11.82   Downloaded portable-atomic v1.13.1
11.83   Downloaded pcre2 v0.2.11
11.83   Downloaded ordered-float v4.6.0
11.83   Downloaded openai-harmony v0.0.3
11.84   Downloaded objc2-encode v4.1.0
11.84   Downloaded pyo3-macros v0.23.5
11.84   Downloaded prost-derive v0.14.3
11.84   Downloaded prost-build v0.13.5
11.85   Downloaded proc-macro-error-attr2 v2.0.0
11.85   Downloaded ordered-multimap v0.7.3
11.85   Downloaded ordered-float v2.10.1
11.85   Downloaded protobuf-support v3.7.2
11.85   Downloaded pest_meta v2.8.6
11.85   Downloaded objc2-core-graphics v0.3.2
11.86   Downloaded nix v0.26.4
11.87   Downloaded icu_provider v2.2.0
11.87   Downloaded objc2-core-location v0.3.2
11.87   Downloaded matchit v0.8.4
11.87   Downloaded getrandom v0.3.4
11.88   Downloaded flume v0.12.0
11.88   Downloaded phf_generator v0.11.3
11.88   Downloaded num-rational v0.4.2
11.88   Downloaded futures v0.3.32
11.89   Downloaded litemap v0.8.2
11.89   Downloaded getrandom v0.2.17
11.89   Downloaded encode_unicode v1.0.0
11.89   Downloaded num-integer v0.1.46
11.89   Downloaded moxcms v0.8.1
11.90   Downloaded nu-ansi-term v0.50.3
11.91   Downloaded minijinja-contrib v2.19.0
11.91   Downloaded jobserver v0.1.34
11.91   Downloaded proc-macro2-diagnostics v0.10.1
11.91   Downloaded proc-macro-error2 v2.0.1
11.91   Downloaded openssl-probe v0.2.1
11.91   Downloaded nonmax v0.5.5
11.92   Downloaded memoffset v0.9.1
11.92   Downloaded kube v2.0.1
11.92   Downloaded pin-project v1.1.11
11.93   Downloaded num_cpus v1.17.0
11.93   Downloaded mio v0.8.11
11.94   Downloaded offset-allocator v0.2.0
11.94   Downloaded async-openai v0.34.0
11.96   Downloaded pin-utils v0.1.0
11.96   Downloaded minijinja v2.19.0
11.96   Downloaded dispatch2 v0.3.1
11.97   Downloaded malachite-q v0.4.22
11.99   Downloaded lru v0.12.5
11.99   Downloaded foldhash v0.2.0
11.99   Downloaded parking_lot v0.12.5
11.99   Downloaded image v0.25.10
12.00   Downloaded educe v0.6.0
12.00   Downloaded oneshot v0.1.13
12.01   Downloaded nkeys v0.4.5
12.01   Downloaded noop_proc_macro v0.3.0
12.01   Downloaded neli-proc-macros v0.2.2
12.01   Downloaded multimap v0.10.1
12.01   Downloaded inotify v0.9.6
12.01   Downloaded libfuzzer-sys v0.4.12
12.02   Downloaded lalrpop-util v0.20.2
12.02   Downloaded no_std_io2 v0.9.3
12.02   Downloaded itertools v0.14.0
12.03   Downloaded futures-channel v0.3.32
12.03   Downloaded av-scenechange v0.14.1
12.04   Downloaded nuid v0.5.0
12.04   Downloaded iri-string v0.7.12
12.05   Downloaded hyper v1.9.0
12.05   Downloaded bstr v1.12.1
12.06   Downloaded memoffset v0.7.1
12.06   Downloaded md-5 v0.10.6
12.06   Downloaded matchers v0.2.0
12.06   Downloaded macro_rules_attribute-proc_macro v0.2.2
12.06   Downloaded kube-core v2.0.1
12.07   Downloaded itertools v0.13.0
12.07   Downloaded hashbrown v0.17.0
12.08   Downloaded dialoguer v0.11.0
12.08   Downloaded derive_more v1.0.0
12.09   Downloaded hashbrown v0.15.5
12.09   Downloaded libloading v0.8.9
12.10   Downloaded foldhash v0.1.5
12.10   Downloaded filetime v0.2.27
12.10   Downloaded bs62 v0.1.4
12.10   Downloaded fdeflate v0.3.7
12.10   Downloaded idna v1.1.0
12.10   Downloaded hyper-timeout v0.5.2
12.11   Downloaded icu_normalizer_data v2.2.0
12.11   Downloaded lazy_static v1.5.0
12.11   Downloaded icu_locale_core v2.2.0
12.12   Downloaded crypto-common v0.1.7
12.12   Downloaded libloading v0.9.0
12.12   Downloaded lebe v0.5.3
12.12   Downloaded kqueue-sys v1.0.4
12.12   Downloaded darling_core v0.23.0
12.13   Downloaded darling_core v0.20.11
12.13   Downloaded jiff-tzdb v0.1.6
12.13   Downloaded displaydoc v0.2.5
12.13   Downloaded dircpy v0.3.20
12.14   Downloaded dlv-list v0.5.2
12.14   Downloaded lru v0.16.4
12.14   Downloaded hyper-util v0.1.20
12.14   Downloaded http v1.4.0
12.15   Downloaded chrono v0.4.44
12.15   Downloaded jiff-tzdb-platform v0.1.3
12.15   Downloaded icu_normalizer v2.2.0
12.16   Downloaded lru-slab v0.1.2
12.16   Downloaded lock_api v0.4.14
12.16   Downloaded erased-serde v0.4.10
12.16   Downloaded fs_extra v1.3.0
12.16   Downloaded fastrand v2.4.1
12.16   Downloaded digest v0.10.7
12.16   Downloaded blake3 v1.8.4
12.17   Downloaded derive_builder_core v0.20.2
12.17   Downloaded inotify-sys v0.1.5
12.17   Downloaded dyn-clone v1.0.20
12.18   Downloaded futures-sink v0.3.32
12.18   Downloaded aws-lc-rs v1.16.3
12.19   Downloaded form_urlencoded v1.2.2
12.19   Downloaded equivalent v1.0.2
12.19   Downloaded dunce v1.0.5
12.19   Downloaded ipnet v2.12.0
12.19   Downloaded fsevent-sys v4.1.0
12.19   Downloaded fax v0.2.6
12.19   Downloaded clap_builder v4.6.0
12.20   Downloaded fnv v1.0.7
12.20   Downloaded bindgen v0.71.1
12.20   Downloaded inlinable_string v0.1.15
12.21   Downloaded iana-time-zone-haiku v0.1.2
12.21   Downloaded http-body-util v0.1.3
12.21   Downloaded indoc v2.0.7
12.21   Downloaded httpdate v1.0.3
12.21   Downloaded futures-io v0.3.32
12.21   Downloaded darling v0.21.3
12.22   Downloaded idna_adapter v1.2.1
12.22   Downloaded id-arena v2.3.0
12.22   Downloaded getopts v0.2.24
12.22   Downloaded ed25519 v2.2.3
12.22   Downloaded interpolate_name v0.2.4
12.22   Downloaded hashbrown v0.14.5
12.23   Downloaded galil-seiferas v0.1.5
12.23   Downloaded fs-err v3.3.0
12.23   Downloaded axum v0.8.4
12.24   Downloaded defmac v0.1.3
12.24   Downloaded darling_macro v0.21.3
12.24   Downloaded errno v0.3.14
12.24   Downloaded equator-macro v0.4.2
12.24   Downloaded httparse v1.10.1
12.24   Downloaded crossbeam-utils v0.8.21
12.25   Downloaded arc-swap v1.9.1
12.25   Downloaded cc v1.2.61
12.25   Downloaded bytes v1.11.1
12.25   Downloaded compact_str v0.9.0
12.26   Downloaded cfg-expr v0.15.8
12.26   Downloaded base64 v0.22.1
12.26   Downloaded gif v0.14.2
12.27   Downloaded futures-task v0.3.32
12.27   Downloaded bytemuck v1.25.0
12.27   Downloaded bitflags v2.11.1
12.27   Downloaded bincode v2.0.1
12.28   Downloaded core-foundation-sys v0.8.7
12.28   Downloaded config v0.15.22
12.28   Downloaded axum-server v0.7.3
12.29   Downloaded derive-getters v0.5.0
12.29   Downloaded base64 v0.13.1
12.29   Downloaded bitstream-io v4.10.0
12.29   Downloaded derive_arbitrary v1.4.2
12.30   Downloaded data-encoding v2.11.0
12.30   Downloaded bitflags v1.3.2
12.30   Downloaded console v0.16.3
12.30   Downloaded console v0.15.11
12.30   Downloaded concurrent-queue v2.5.0
12.30   Downloaded clap_derive v4.6.1
12.31   Downloaded arbitrary v1.4.2
12.31   Downloaded dirs-sys v0.5.0
12.31   Downloaded crc32fast v1.5.0
12.31   Downloaded clang-sys v1.8.1
12.32   Downloaded built v0.8.0
12.32   Downloaded block2 v0.6.2
12.32   Downloaded crossbeam-epoch v0.9.18
12.32   Downloaded convert_case v0.6.0
12.32   Downloaded async-broadcast v0.7.2
12.32   Downloaded anstyle-query v1.1.5
12.32   Downloaded dashmap v6.1.0
12.33   Downloaded dary_heap v0.3.9
12.33   Downloaded constant_time_eq v0.4.2
12.33   Downloaded bs58 v0.5.1
12.33   Downloaded base64ct v1.8.3
12.33   Downloaded async-once-cell v0.5.4
12.33   Downloaded generic-array v0.14.7
12.34   Downloaded anyhow v1.0.102
12.34   Downloaded bit-vec v0.6.3
12.34   Downloaded av1-grain v0.2.5
12.34   Downloaded arrayvec v0.7.6
12.34   Downloaded curve25519-dalek-derive v0.1.1
12.35   Downloaded colorchoice v1.0.5
12.35   Downloaded block-buffer v0.10.4
12.35   Downloaded async-channel v2.5.0
12.35   Downloaded as-slice v0.2.1
12.35   Downloaded anstyle-wincon v3.0.11
12.35   Downloaded const-random v0.1.18
12.35   Downloaded bit_field v0.10.3
12.35   Downloaded anstyle-parse v1.0.0
12.35   Downloaded bit-vec v0.8.0
12.36   Downloaded axum-macros v0.5.1
12.37   Downloaded arg_enum_proc_macro v0.3.4
12.37   Downloaded cfg-if v1.0.4
12.37   Downloaded castaway v0.2.4
12.37   Downloaded atomic-waker v1.1.2
12.37   Downloaded cfg_aliases v0.2.1
12.37   Downloaded bit-set v0.5.3
12.37   Downloaded atomic v0.6.1
12.37   Downloaded async-stream-impl v0.3.6
12.37   Downloaded arraydeque v0.5.1
12.38   Downloaded aho-corasick v1.1.4
12.56 🍹 Building a mixed python/rust project
12.63 🐍 Found CPython 3.12 at /workspace/.venv/bin/python
12.63 🔗 Found pyo3 bindings with abi3-py3.10 support
13.03    Compiling proc-macro2 v1.0.106
13.03    Compiling quote v1.0.45
13.03    Compiling unicode-ident v1.0.24
13.03    Compiling libc v0.2.186
13.03    Compiling serde_core v1.0.228
13.03    Compiling cfg-if v1.0.4
13.03    Compiling serde v1.0.228
13.03    Compiling memchr v2.8.0
13.03    Compiling once_cell v1.21.4
13.03    Compiling version_check v0.9.5
13.03    Compiling log v0.4.29
13.03    Compiling smallvec v1.15.1
13.03    Compiling shlex v1.3.0
13.03    Compiling find-msvc-tools v0.1.9
13.03    Compiling pin-project-lite v0.2.17
13.03    Compiling equivalent v1.0.2
13.04    Compiling itoa v1.0.18
13.05    Compiling autocfg v1.5.0
13.05    Compiling hashbrown v0.17.0
13.07    Compiling scopeguard v1.2.0
13.09    Compiling lock_api v0.4.14
13.10    Compiling futures-core v0.3.32
13.12    Compiling parking_lot_core v0.9.12
13.13    Compiling zerocopy v0.8.48
13.13    Compiling crossbeam-utils v0.8.21
13.14    Compiling zmij v1.0.21
13.15    Compiling futures-sink v0.3.32
13.15    Compiling either v1.15.0
13.15    Compiling thiserror v2.0.18
13.16    Compiling tracing-core v0.1.36
13.17    Compiling slab v0.4.12
13.21    Compiling serde_json v1.0.149
13.23    Compiling futures-channel v0.3.32
13.23    Compiling futures-io v0.3.32
13.24    Compiling futures-task v0.3.32
13.25    Compiling getrandom v0.3.4
13.27    Compiling generic-array v0.14.7
13.29    Compiling zeroize v1.8.2
13.29    Compiling num-traits v0.2.19
13.31    Compiling heck v0.5.0
13.35    Compiling anyhow v1.0.102
13.36    Compiling percent-encoding v2.3.2
13.37    Compiling stable_deref_trait v1.2.1
13.37    Compiling base64 v0.22.1
13.38    Compiling ryu v1.0.23
13.39    Compiling rustls-pki-types v1.14.1
13.42    Compiling typenum v1.20.0
13.42    Compiling fs_extra v1.3.0
13.48    Compiling dunce v1.0.5
13.49    Compiling syn v2.0.117
13.50    Compiling rayon-core v1.13.0
13.51    Compiling icu_normalizer_data v2.2.0
13.52    Compiling icu_properties_data v2.2.0
13.53    Compiling httparse v1.10.1
13.57    Compiling fnv v1.0.7
13.57    Compiling form_urlencoded v1.2.2
13.58    Compiling tower-service v0.3.3
13.59    Compiling aws-lc-rs v1.16.3
13.60    Compiling ident_case v1.0.1
13.62    Compiling strsim v0.11.1
13.65    Compiling untrusted v0.9.0
13.65    Compiling atomic-waker v1.1.2
13.68    Compiling try-lock v0.2.5
13.68    Compiling subtle v2.6.1
13.69    Compiling httpdate v1.0.3
13.70    Compiling want v0.3.1
13.73    Compiling getrandom v0.4.2
13.76    Compiling aho-corasick v1.1.4
13.77    Compiling itertools v0.14.0
13.80    Compiling rustls v0.23.39
13.80    Compiling ipnet v2.12.0
13.84    Compiling target-lexicon v0.12.16
13.84    Compiling regex-syntax v0.8.10
13.86    Compiling sync_wrapper v1.0.2
13.87    Compiling bitflags v2.11.1
13.88    Compiling indexmap v2.14.0
13.89    Compiling tower-layer v0.3.3
13.92    Compiling mime v0.3.17
13.95    Compiling ahash v0.8.12
13.99    Compiling jobserver v0.1.34
14.00    Compiling pkg-config v0.3.33
14.05    Compiling errno v0.3.14
14.06    Compiling socket2 v0.6.3
14.09    Compiling cc v1.2.61
14.12    Compiling signal-hook-registry v1.4.8
14.15    Compiling parking_lot v0.12.5
14.19    Compiling mio v1.1.1
14.25    Compiling getrandom v0.2.17
14.27    Compiling crypto-common v0.1.7
14.29    Compiling block-buffer v0.10.4
14.34    Compiling digest v0.10.7
14.42    Compiling litemap v0.8.2
14.42    Compiling crc32fast v1.5.0
14.45    Compiling unicase v2.9.0
14.51    Compiling writeable v0.6.3
14.52    Compiling prettyplease v0.2.37
14.53    Compiling cpufeatures v0.2.17
14.54    Compiling utf8_iter v1.0.4
14.60    Compiling cmake v0.1.58
14.61    Compiling rustix v1.1.4
14.62    Compiling rand_core v0.9.5
14.65    Compiling write16 v1.0.0
14.65    Compiling utf16_iter v1.0.5
14.68    Compiling rustversion v1.0.22
14.69    Compiling crossbeam-epoch v0.9.18
14.70    Compiling webpki-roots v1.0.7
14.73    Compiling simd-adler32 v0.3.9
14.73    Compiling bytes v1.11.1
14.74    Compiling openssl-probe v0.2.1
14.79    Compiling rustls-native-certs v0.8.3
14.81    Compiling regex-automata v0.4.14
14.83    Compiling crossbeam-deque v0.8.6
14.87    Compiling num-integer v0.1.46
14.88    Compiling fixedbitset v0.5.7
14.96    Compiling iri-string v0.7.12
14.99    Compiling aws-lc-sys v0.40.0
15.01    Compiling ring v0.17.14
15.05    Compiling linux-raw-sys v0.12.1
15.14    Compiling sha1 v0.10.6
15.14    Compiling mime_guess v2.0.5
15.15    Compiling fastrand v2.4.1
15.23    Compiling thiserror v1.0.69
15.24    Compiling adler2 v2.0.1
15.29    Compiling data-encoding v2.11.0
15.30    Compiling ucd-trie v0.1.7
15.35    Compiling miniz_oxide v0.8.9
15.35    Compiling pest v2.8.6
15.49    Compiling encoding_rs v0.8.35
15.54    Compiling same-file v1.0.6
15.58    Compiling synstructure v0.13.2
16.03    Compiling darling_core v0.20.11
16.06    Compiling regex v1.12.3
16.22    Compiling tempfile v3.27.0
16.35    Compiling multimap v0.10.1
16.41    Compiling pest_meta v2.8.6
16.41    Compiling walkdir v2.5.0
16.53    Compiling serde_derive v1.0.228
16.54    Compiling zerocopy-derive v0.8.48
16.59    Compiling zerofrom-derive v0.1.7
16.75    Compiling yoke-derive v0.8.2
16.87    Compiling tokio-macros v2.6.1
16.90    Compiling thiserror-impl v2.0.18
17.09    Compiling futures-macro v0.3.32
17.13    Compiling tracing-attributes v0.1.31
17.27    Compiling displaydoc v0.2.5
17.32    Compiling zerovec-derive v0.11.3
17.34    Compiling thiserror-impl v1.0.69
17.37    Compiling zerofrom v0.1.7
17.41    Compiling darling_macro v0.20.11
17.43    Compiling yoke v0.8.2
17.51    Compiling pin-project-internal v1.1.11
17.56    Compiling futures-util v0.3.32
17.59    Compiling utf-8 v0.7.6
17.66    Compiling crunchy v0.2.4
17.71    Compiling zerotrie v0.2.4
17.73    Compiling darling v0.20.11
17.73    Compiling allocator-api2 v0.2.21
17.91    Compiling pest_generator v2.8.6
17.95    Compiling async-trait v0.1.89
17.95    Compiling prost-derive v0.14.3
17.96    Compiling tracing v0.1.44
18.00    Compiling zerovec v0.11.6
18.14    Compiling flate2 v1.1.9
18.35    Compiling pin-project v1.1.11
18.36    Compiling tiny-keccak v2.0.2
18.39    Compiling pest_derive v2.8.6
18.49    Compiling tinystr v0.8.3
18.65    Compiling icu_locale_core v2.2.0
18.66    Compiling potential_utf v0.1.5
18.73    Compiling icu_collections v2.2.0
19.07    Compiling serde_urlencoded v0.7.1
19.15    Compiling rayon v1.12.0
19.23    Compiling derive_builder_core v0.20.2
19.24    Compiling axum-macros v0.5.1
19.25    Compiling crossbeam-channel v0.5.15
19.38    Compiling crossbeam-queue v0.3.12
19.44    Compiling tokio v1.48.0
19.46    Compiling http v1.4.0
19.60    Compiling icu_provider v2.2.0
19.77    Compiling futures-executor v0.3.32
19.85    Compiling icu_properties v2.2.0
19.93    Compiling icu_normalizer v2.2.0
19.95    Compiling futures v0.3.32
19.99    Compiling serde_path_to_error v0.1.20
20.01    Compiling lazy_static v1.5.0
20.04    Compiling portable-atomic v1.13.1
20.14    Compiling http-body v1.0.1
20.21    Compiling ppv-lite86 v0.2.21
20.23    Compiling http-body-util v0.1.3
20.36    Compiling rand_chacha v0.9.0
20.39    Compiling paste v1.0.15
20.45    Compiling hashbrown v0.14.5
20.46    Compiling rand v0.9.4
20.47    Compiling axum-core v0.5.6
20.49    Compiling byteorder v1.5.0
20.53    Compiling matchit v0.8.4
20.66    Compiling idna_adapter v1.2.1
20.72    Compiling idna v1.1.0
21.05    Compiling url v2.5.8
21.07    Compiling tungstenite v0.26.2
21.08    Compiling derive_builder_macro v0.20.2
21.10    Compiling crossbeam v0.8.4
21.16    Compiling serde_spanned v0.6.9
21.16    Compiling toml_datetime v0.6.11
21.20    Compiling prost-derive v0.13.5
21.20    Compiling num-bigint v0.4.6
21.29    Compiling rand_core v0.6.4
21.38    Compiling pyo3-build-config v0.23.5
21.40    Compiling arrayvec v0.7.6
21.46    Compiling iana-time-zone v0.1.65
21.46    Compiling winnow v0.7.15
21.53    Compiling cfg_aliases v0.2.1
21.54    Compiling foldhash v0.1.5
21.58    Compiling chrono v0.4.44
21.63    Compiling hashbrown v0.15.5
21.76    Compiling rand_chacha v0.3.1
21.84    Compiling derive_builder v0.20.2
22.09    Compiling sha2 v0.10.9
22.12    Compiling siphasher v1.0.2
22.16    Compiling unicode-width v0.2.2
22.17    Compiling pulldown-cmark v0.13.3
22.19    Compiling phf_shared v0.11.3
22.21    Compiling rand v0.8.6
22.28    Compiling equator-macro v0.4.2
22.31    Compiling cfg-expr v0.15.8
22.34    Compiling concurrent-queue v2.5.0
22.52    Compiling jwalk v0.8.1
22.53    Compiling toml_edit v0.22.27
22.56    Compiling base64ct v1.8.3
22.64    Compiling dircpy v0.3.20
22.64    Compiling version-compare v0.2.1
22.66    Compiling ref-cast v1.0.25
22.67    Compiling parking v2.2.1
22.68    Compiling powerfmt v0.2.0
22.73    Compiling libm v0.2.16
22.74    Compiling glob v0.3.3
22.76    Compiling semver v1.0.28
22.78    Compiling zeromq-src v0.2.6+4.3.4
22.81    Compiling deranged v0.5.8
22.85    Compiling event-listener v5.4.1
22.90    Compiling rustc_version v0.4.1
22.91    Compiling pem-rfc7468 v0.7.0
22.92    Compiling clang-sys v1.8.1
22.99    Compiling equator v0.4.2
23.03    Compiling phf_generator v0.11.3
23.05    Compiling tokio-util v0.7.18
23.10    Compiling tokio-tungstenite v0.26.2
23.10    Compiling prost v0.13.5
23.22    Compiling prost v0.14.3
23.25    Compiling opentelemetry v0.31.0
23.30    Compiling ref-cast-impl v1.0.25
23.43    Compiling serde_derive_internals v0.29.1
23.47    Compiling proc-macro-error-attr2 v2.0.0
23.55    Compiling const-oid v0.9.6
23.57    Compiling time-core v0.1.8
23.61    Compiling unsafe-libyaml v0.2.11
23.63    Compiling num_threads v0.1.7
23.66    Compiling h2 v0.4.13
23.69    Compiling tower v0.5.3
23.71    Compiling tokio-stream v0.1.18
23.84    Compiling toml v0.8.23
23.93    Compiling k8s-openapi v0.26.1
24.01    Compiling num-conv v0.2.1
24.06    Compiling system-deps v6.2.2
24.10    Compiling utf8parse v0.2.2
24.12    Compiling anstyle-parse v1.0.0
24.16    Compiling time v0.3.47
24.21    Compiling serde_yaml v0.9.34+deprecated
24.27    Compiling schemars_derive v1.2.1
24.48    Compiling tower-http v0.6.8
24.50    Compiling zmq-sys v0.12.0
24.54    Compiling proc-macro-error2 v2.0.1
24.60    Compiling der v0.7.10
24.63    Compiling pulldown-cmark-to-cmark v22.0.0
24.67    Compiling prost-types v0.14.3
24.77    Compiling prost-types v0.13.5
24.81    Compiling petgraph v0.8.3
24.86    Compiling aligned-vec v0.6.4
24.89    Compiling phf_codegen v0.11.3
24.93    Compiling curve25519-dalek v4.1.3
24.96    Compiling event-listener-strategy v0.5.4
25.02    Compiling nix v0.30.1
25.13    Compiling uuid v1.23.1
25.17    Compiling itertools v0.11.0
25.27    Compiling jsonptr v0.7.1
25.38    Compiling derive_more-impl v2.1.1
25.48    Compiling petgraph v0.7.1
25.48    Compiling signature v2.2.0
25.52    Compiling ordered-float v2.10.1
25.56    Compiling proc-macro2-diagnostics v0.10.1
25.60    Compiling typeid v1.0.3
25.63    Compiling anstyle v1.0.14
25.65    Compiling colorchoice v1.0.5
25.68    Compiling bitflags v1.3.2
25.69    Compiling bytemuck v1.25.0
25.69    Compiling dyn-clone v1.0.20
25.73    Compiling malachite-nz v0.4.22
25.75    Compiling is_terminal_polyfill v1.70.2
25.76    Compiling anstyle-query v1.1.5
25.77    Compiling minimal-lexical v0.2.1
25.78    Compiling anstream v1.0.0
25.80    Compiling schemars v1.2.1
25.83    Compiling prost-build v0.14.3
25.87    Compiling nom v7.1.3
26.05    Compiling derive_more v2.1.1
26.06    Compiling malachite-base v0.4.22
26.07    Compiling serde-value v0.7.0
26.15    Compiling json-patch v4.1.0
26.20    Compiling spki v0.7.3
26.24    Compiling prost-build v0.13.5
26.31    Compiling v_frame v0.3.9
26.33    Compiling hyper v1.9.0
26.61    Compiling console v0.15.11
26.66    Compiling num-rational v0.4.2
26.76    Compiling const-random-macro v0.1.16
26.90    Compiling sharded-slab v0.1.7
27.14    Compiling tracing-serde v0.2.0
27.20    Compiling matchers v0.2.0
27.20    Compiling async-stream-impl v0.3.6
27.24    Compiling enum-ordinalize-derive v4.3.2
27.24    Compiling tonic-build v0.14.5
27.24    Compiling darling_core v0.21.3
27.28    Compiling rustls-pemfile v2.2.0
27.41    Compiling hyper-util v0.1.20
27.47    Compiling tracing-log v0.2.0
27.53    Compiling as-slice v0.2.1
27.54    Compiling libloading v0.8.9
27.55    Compiling thread_local v1.1.9
27.61    Compiling clap_lex v1.1.0
27.68    Compiling bindgen v0.71.1
27.69    Compiling av-scenechange v0.14.1
27.70    Compiling option-ext v0.2.0
27.72    Compiling yansi v1.0.1
27.76    Compiling protobuf v3.7.2
27.77    Compiling built v0.8.0
27.80    Compiling unicode-segmentation v1.13.2
27.86    Compiling nu-ansi-term v0.50.3
28.02    Compiling rav1e v0.8.1
28.11    Compiling tracing-subscriber v0.3.23
28.17    Compiling clap_builder v4.6.0
28.18    Compiling dirs-sys v0.5.0
28.19    Compiling getopts v0.2.24
28.28    Compiling enum-ordinalize v4.3.2
28.48    Compiling hyper-timeout v0.5.2
28.48    Compiling axum v0.8.4
28.56    Compiling aligned v0.4.3
28.59    Compiling async-stream v0.3.6
28.63    Compiling tonic-prost-build v0.14.5
28.79    Compiling darling_macro v0.21.3
28.83    Compiling const-random v0.1.18
28.84    Compiling cexpr v0.6.0
29.23    Compiling tonic-build v0.13.1
29.60    Compiling pkcs8 v0.10.2
29.76    Compiling ed25519 v2.2.3
29.84    Compiling socks v0.3.4
29.85    Compiling jsonpath-rust v0.7.5
30.04    Compiling protobuf-support v3.7.2
30.05    Compiling profiling-procmacros v1.0.17
30.09    Compiling arg_enum_proc_macro v0.3.4
30.10    Compiling clap_derive v4.6.1
30.27    Compiling darling_core v0.23.0
30.37    Compiling webpki-roots v0.26.11
30.39    Compiling socket2 v0.5.10
30.44    Compiling pem v3.0.6
30.47    Compiling secrecy v0.10.3
30.51    Compiling no_std_io2 v0.9.3
30.52    Compiling nom v8.0.0
30.53    Compiling matrixmultiply v0.3.10
30.60    Compiling itertools v0.13.0
30.77    Compiling uncased v0.9.10
30.83    Compiling pastey v0.1.1
30.86    Compiling zmq v0.10.0
30.92    Compiling rustc-hash v2.1.2
30.95    Compiling unicode-xid v0.2.6
30.98    Compiling static_assertions v1.1.0
31.00    Compiling bit-vec v0.6.3
31.03    Compiling number_prefix v0.4.0
31.06    Compiling erased-serde v0.4.10
31.07    Compiling quick-error v2.0.1
31.11    Compiling prometheus v0.14.0
31.12    Compiling y4m v0.8.0
31.15    Compiling toml_write v0.1.2
31.17    Compiling home v0.5.12
31.26    Compiling clap v4.6.1
31.28    Compiling bit-set v0.5.3
31.28    Compiling indicatif v0.17.11
31.34    Compiling derive_more-impl v1.0.0
31.80    Compiling darling_macro v0.23.0
31.87    Compiling bitstream-io v4.10.0
32.01    Compiling profiling v1.0.17
32.19    Compiling ed25519-dalek v2.2.0
32.43    Compiling av1-grain v0.2.5
32.46    Compiling os_info v3.14.0
32.54    Compiling signatory v0.27.1
32.71    Compiling darling v0.21.3
32.75    Compiling dlv-list v0.5.2
32.88    Compiling etcd-client v0.17.0
32.97    Compiling unicode_names2_generator v1.3.0
33.17    Compiling educe v0.6.0
33.34    Compiling pear_codegen v0.2.9
33.34    Compiling dirs v6.0.0
33.40    Compiling async-broadcast v0.7.2
33.44    Compiling getset v0.1.6
33.49    Compiling opentelemetry_sdk v0.31.0
33.52    Compiling malachite-q v0.4.22
33.59    Compiling kube-core v2.0.1
33.82    Compiling backon v1.6.0
33.82    Compiling dashmap v6.1.0
33.96    Compiling maybe-rayon v0.1.1
33.98    Compiling half v2.7.1
34.01    Compiling neli-proc-macros v0.2.2
34.16    Compiling bincode v1.3.3
34.18    Compiling derive-getters v0.5.0
34.24    Compiling num-derive v0.4.2
34.43    Compiling fax_derive v0.2.0
34.54    Compiling blake3 v1.8.4
34.57    Compiling pcre2-sys v0.2.10
34.60    Compiling onig_sys v69.9.1
34.65    Compiling inotify-sys v0.1.5
34.68    Compiling num_cpus v1.17.0
34.73    Compiling hostname v0.4.2
34.75    Compiling rmp v0.8.15
34.76    Compiling num-complex v0.4.6
34.78    Compiling simd_helpers v0.1.0
34.79    Compiling figment v0.10.19
34.79    Compiling rustix v0.38.44
34.85    Compiling winnow v1.0.2
34.90    Compiling zune-core v0.5.1
34.91    Compiling openssl-probe v0.1.6
34.98    Compiling rawpointer v0.2.1
35.00    Compiling bumpalo v3.20.2
35.02    Compiling rustc-hash v1.1.0
35.03    Compiling unic-common v0.9.0
35.05    Compiling new_debug_unreachable v1.0.6
35.11    Compiling noop_proc_macro v0.3.0
35.12    Compiling weezl v0.1.12
35.13    Compiling zlib-rs v0.6.3
35.19    Compiling inlinable_string v0.1.15
35.24    Compiling imgref v1.12.0
35.31    Compiling xxhash-rust v0.8.15
35.34    Compiling unic-char-range v0.9.0
35.34    Compiling loop9 v0.1.5
35.37    Compiling unic-char-property v0.9.0
35.40    Compiling pear v0.2.9
35.78    Compiling toml_parser v1.1.2+spec-1.1.0
35.85    Compiling zopfli v0.8.3
35.93    Compiling unic-ucd-version v0.9.0
35.94    Compiling zune-jpeg v0.5.15
36.20    Compiling rustls-native-certs v0.7.3
36.41    Compiling rmp-serde v1.3.1
36.65    Compiling fax v0.2.6
36.90    Compiling inotify v0.9.6
36.91    Compiling nixl-sys v0.10.1
36.94    Compiling neli v0.7.4
37.12    Compiling malachite v0.4.22
37.25    Compiling unicode_names2 v1.3.0
37.38    Compiling ordered-multimap v0.7.3
37.54    Compiling derive_more v1.0.0
37.56    Compiling kube-derive v2.0.1
37.87    Compiling nkeys v0.4.5
38.28    Compiling darling v0.23.0
38.38    Compiling fancy-regex v0.13.0
38.97    Compiling nuid v0.5.0
39.25    Compiling validator_derive v0.20.0
39.25    Compiling tryhard v0.5.2
39.27    Compiling pyo3-macros-backend v0.23.5
39.31    Compiling pyo3-ffi v0.23.5
39.34    Compiling hashlink v0.10.0
39.43    Compiling avif-serialize v0.8.8
39.53    Compiling serde_nanos v0.1.4
39.57    Compiling bstr v1.12.1
39.90    Compiling is-macro v0.3.7
40.00    Compiling serde_repr v0.1.20
40.24    Compiling arc-swap v1.9.1
40.29    Compiling esaxx-rs v0.1.10
40.38    Compiling fdeflate v0.3.7
40.42    Compiling zune-inflate v0.2.54
40.71    Compiling serde_spanned v1.1.1
40.73    Compiling toml_datetime v1.1.1+spec-1.1.0
40.76    Compiling filetime v0.2.27
40.85    Compiling memmap2 v0.9.10
40.94    Compiling mio v0.8.11
40.95    Compiling rustls-webpki v0.102.8
40.99    Compiling rustpython-parser-vendored v0.4.0
41.09    Compiling pxfm v0.1.29
41.17    Compiling byteorder-lite v0.1.0
41.17    Compiling lebe v0.5.3
41.24    Compiling foldhash v0.2.0
41.25    Compiling zip v2.4.2
41.31    Compiling bit_field v0.10.3
41.31    Compiling constant_time_eq v0.4.2
41.35    Compiling arrayref v0.3.9
41.36    Compiling virtue v0.0.18
41.37    Compiling color_quant v1.1.0
41.43    Compiling bs58 v0.5.1
41.46    Compiling bit-vec v0.8.0
41.52    Compiling linux-raw-sys v0.4.15
41.60    Compiling rgb v0.8.53
41.67    Compiling humantime v2.3.0
41.69    Compiling arraydeque v0.5.1
41.70    Compiling bincode_derive v2.0.1
41.77    Compiling ravif v0.13.0
41.78    Compiling yaml-rust2 v0.10.4
41.90    Compiling bit-set v0.8.0
41.97    Compiling dynamo-tokens v1.2.0 (/opt/dynamo/lib/tokens)
42.01    Compiling gif v0.14.2
42.68    Compiling moxcms v0.8.1
42.91    Compiling exr v1.74.0
43.05    Compiling ron v0.12.1
43.22    Compiling image-webp v0.2.4
43.76    Compiling hashbrown v0.16.1
44.45    Compiling rustpython-parser-core v0.4.0
44.60    Compiling notify v6.1.1
45.29    Compiling toml v1.1.2+spec-1.1.0
45.45    Compiling png v0.18.1
45.96    Compiling validator v0.20.0
46.03    Compiling serde-untagged v0.1.9
46.29    Compiling local-ip-address v0.6.12
46.99    Compiling serde_with_macros v3.18.0
47.35    Compiling malachite-bigint v0.2.3
47.74    Compiling rust-ini v0.21.3
47.96    Compiling zip v3.0.0
48.36    Compiling rust-embed-utils v8.11.0
48.44    Compiling tiff v0.11.3
48.56    Compiling ndarray v0.16.1
48.64    Compiling phf v0.11.3
48.66    Compiling modelexpress-common v0.3.0
48.72    Compiling tracing-opentelemetry v0.32.1
48.85    Compiling opentelemetry-appender-tracing v0.31.1
48.88    Compiling convert_case v0.6.0
48.89    Compiling qoi v0.4.1
48.90    Compiling rustpython-parser v0.4.0
48.99    Compiling tokio-rayon v2.1.0
49.03    Compiling lru v0.12.5
49.12    Compiling json5 v0.4.1
49.27    Compiling monostate-impl v0.1.18
49.33    Compiling strum_macros v0.27.2
49.35    Compiling dynamo-config v1.2.0 (/opt/dynamo/lib/config)
49.37    Compiling castaway v0.2.4
49.44    Compiling fs-err v3.3.0
49.46    Compiling memoffset v0.9.1
49.48    Compiling memoffset v0.7.1
49.51    Compiling spin v0.9.8
49.54    Compiling slotmap v1.1.1
49.55    Compiling base64 v0.13.1
49.61    Compiling async-once-cell v0.5.4
49.61    Compiling unicode-general-category v1.1.0
49.64    Compiling macro_rules_attribute-proc_macro v0.2.2
49.74    Compiling unty v0.0.4
49.76    Compiling cudarc v0.19.3
49.78    Compiling pathdiff v0.2.3
49.80    Compiling config v0.15.22
49.83    Compiling macro_rules_attribute v0.2.2
49.84    Compiling bincode v2.0.1
49.89    Compiling spm_precompiled v0.1.4
50.03    Compiling flume v0.12.0
50.11    Compiling monostate v0.1.18
50.19    Compiling compact_str v0.9.0
50.23    Compiling image v0.25.10
50.59    Compiling strum v0.27.2
50.59    Compiling tonic v0.13.1
50.63    Compiling rustpython-ast v0.4.0
50.80    Compiling utoipa-swagger-ui v9.0.2
50.86    Compiling rust-embed-impl v8.11.0
50.92    Compiling serde_with v3.18.0
50.93    Compiling onig v6.5.1
51.25    Compiling lru v0.16.4
51.33    Compiling timerfd v1.6.0
51.38    Compiling fancy-regex v0.17.0
51.40    Compiling unic-ucd-ident v0.9.0
51.48    Compiling unic-emoji-char v0.9.0
51.59    Compiling py_literal v0.4.0
51.62    Compiling rayon-cond v0.4.0
51.80    Compiling pyo3 v0.23.5
51.90    Compiling console v0.16.3
52.29    Compiling async-openai v0.34.0
52.78    Compiling dary_heap v0.3.9
52.86    Compiling utoipa-gen v5.4.0
53.15    Compiling jiff v0.2.24
53.29    Compiling ordered-float v4.6.0
53.45    Compiling unicode-normalization-alignments v0.1.12
53.47    Compiling libloading v0.9.0
53.58    Compiling unicode_categories v0.1.1
53.65    Compiling memo-map v0.3.3
53.73    Compiling daachorse v1.0.1
53.81    Compiling lalrpop-util v0.20.2
53.89    Compiling nonmax v0.5.5
54.10    Compiling unit-prefix v0.5.2
54.13    Compiling offset-allocator v0.2.0
54.14    Compiling indicatif v0.18.4
54.26    Compiling tokenizers v0.21.4
54.34    Compiling minijinja v2.19.0
54.60    Compiling pyo3-macros v0.23.5
55.02    Compiling ndarray-npy v0.9.1
55.77    Compiling rust-embed v8.11.0
56.25    Compiling tokio-timerfd v0.2.0
56.37    Compiling kvbm-logical v1.2.0 (/opt/dynamo/lib/kvbm-logical)
56.82    Compiling utoipa v5.4.0
56.85    Compiling ndarray-interp v0.5.0
58.50    Compiling tiktoken-rs v0.9.1
58.75    Compiling dynamo-llm v1.2.0 (/opt/dynamo/lib/llm)
59.39    Compiling quick-xml v0.38.4
59.91    Compiling dynamo-protocols v1.2.0 (/opt/dynamo/lib/protocols)
60.14    Compiling pcre2 v0.2.11
60.59    Compiling md-5 v0.10.6
60.70    Compiling indoc v2.0.7
60.74    Compiling defmac v0.1.3
60.76    Compiling colored v3.1.1
60.84    Compiling shell-words v1.1.1
60.88    Compiling unindent v0.2.4
60.95    Compiling pin-utils v0.1.0
60.96    Compiling unchecked-index v0.2.2
61.00    Compiling galil-seiferas v0.1.5
61.00    Compiling nix v0.26.4
61.16    Compiling dialoguer v0.11.0
61.47    Compiling dynamo-memory v1.2.0 (/opt/dynamo/lib/memory)
61.59 warning: dynamo-llm@1.2.0: Building with CUDA KV off
61.59 warning: dynamo-llm@1.2.0: Found FATBIN at default location: ./src/block_manager/block/transfer/kernels/vectorized_copy.fatbin
61.59 warning: dynamo-llm@1.2.0: CUDA FATBIN found at: ./src/block_manager/block/transfer/kernels/vectorized_copy.fatbin - copied to OUT_DIR
62.56    Compiling json-five v0.3.1
62.70    Compiling minijinja-contrib v2.19.0
62.75    Compiling bs62 v0.1.4
62.97    Compiling oneshot v0.1.13
63.04    Compiling async-channel v2.5.0
63.13    Compiling pyo3-async-runtimes-macros v0.23.0
63.46    Compiling inventory v0.3.24
63.48    Compiling dynamo-py3 v1.2.0 (/opt/dynamo/lib/bindings/python)
63.54    Compiling pyo3-async-runtimes v0.23.0
63.93    Compiling pythonize v0.23.0
70.02    Compiling tmq v0.5.0
71.10    Compiling rustls-webpki v0.103.13
74.09    Compiling tokio-rustls v0.26.4
74.09    Compiling ureq v2.12.1
74.24    Compiling hyper-rustls v0.27.9
74.24    Compiling tonic v0.14.5
74.24    Compiling async-nats v0.45.0
74.24    Compiling axum-server v0.7.3
74.52    Compiling reqwest v0.12.28
74.54    Compiling kube-client v2.0.1
75.90    Compiling hf-hub v0.4.3
75.90    Compiling opentelemetry-http v0.31.0
75.90    Compiling object_store v0.12.5
75.93    Compiling tonic-prost v0.14.5
75.98    Compiling opentelemetry-proto v0.31.0
76.89    Compiling kube-runtime v2.0.1
77.04    Compiling opentelemetry-otlp v0.31.1
77.06    Compiling fastokens v0.1.1
78.29    Compiling kube v2.0.1
78.58    Compiling dynamo-tokenizers v1.2.0 (/opt/dynamo/lib/tokenizers)
78.78    Compiling modelexpress-client v0.3.0
79.17    Compiling dynamo-runtime v1.2.0 (/opt/dynamo/lib/runtime)
80.48    Compiling openai-harmony v0.0.3
83.95    Compiling dynamo-parsers v1.2.0 (/opt/dynamo/lib/parsers)
94.69    Compiling dynamo-kv-router v1.2.0 (/opt/dynamo/lib/kv-router)
100.1    Compiling dynamo-mocker v1.2.0 (/opt/dynamo/lib/mocker)
110.7 error[E0599]: no method named `get_model_entries` found for reference `&ModelManager` in the current scope
110.7    --> /opt/dynamo/lib/llm/src/http/service/clear_kv_blocks.rs:31:41
110.7     |
110.7  31 |     let model_entries = state.manager().get_model_entries();
110.7     |                                         ^^^^^^^^^^^^^^^^^
110.7     |
110.7 help: there is a method `get_model` with a similar name, but with different arguments
110.7    --> /opt/dynamo/lib/llm/src/discovery/model_manager.rs:119:5
110.7     |
110.7 119 |     pub fn get_model(&self, model_name: &str) -> Option<Arc<Model>> {
110.7     |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
110.7
110.7 error[E0599]: no method named `runtime` found for struct `std::sync::Arc<service_v2::State>` in the current scope
110.7   --> /opt/dynamo/lib/llm/src/http/service/clear_kv_blocks.rs:40:35
110.7    |
110.7 40 |     let distributed = match state.runtime() {
110.7    |                                   ^^^^^^^ method not found in `std::sync::Arc<service_v2::State>`
110.7
110.7 error[E0282]: type annotations needed
110.7   --> /opt/dynamo/lib/llm/src/http/service/clear_kv_blocks.rs:40:9
110.7    |
110.7 40 |     let distributed = match state.runtime() {
110.7    |         ^^^^^^^^^^^
110.7 ...
110.7 85 |         let namespace_obj = match distributed.namespace(namespace) {
110.7    |                                   ----------- type must be known at this point
110.7    |
110.7 help: consider giving `distributed` an explicit type
110.7    |
110.7 40 |     let distributed: /* Type */ = match state.runtime() {
110.7    |                    ++++++++++++
110.7
110.7 error[E0282]: type annotations needed
110.7   --> /opt/dynamo/lib/llm/src/http/service/clear_kv_blocks.rs:94:26
110.7    |
110.7 94 |                     Some(e.to_string()),
110.7    |                          ^ cannot infer type
110.7
110.7 error[E0282]: type annotations needed
110.7    --> /opt/dynamo/lib/llm/src/http/service/clear_kv_blocks.rs:85:13
110.7     |
110.7  85 |         let namespace_obj = match distributed.namespace(namespace) {
110.7     |             ^^^^^^^^^^^^^
110.7 ...
110.7 100 |         let component_obj = match namespace_obj.component(component) {
110.7     |                                   ------------- type must be known at this point
110.7     |
110.7 help: consider giving `namespace_obj` an explicit type
110.7     |
110.7  85 |         let namespace_obj: /* Type */ = match distributed.namespace(namespace) {
110.7     |                          ++++++++++++
110.7
110.7 error[E0282]: type annotations needed
110.7    --> /opt/dynamo/lib/llm/src/http/service/clear_kv_blocks.rs:109:26
110.7     |
110.7 109 |                     Some(e.to_string()),
110.7     |                          ^ cannot infer type
110.7
110.7 error[E0282]: type annotations needed
110.7    --> /opt/dynamo/lib/llm/src/http/service/clear_kv_blocks.rs:100:13
110.7     |
110.7 100 |         let component_obj = match namespace_obj.component(component) {
110.7     |             ^^^^^^^^^^^^^
110.7 ...
110.7 116 |             component_obj.endpoint(CLEAR_KV_ENDPOINT);
110.7     |             ------------- type must be known at this point
110.7     |
110.7 help: consider giving `component_obj` an explicit type
110.7     |
110.7 100 |         let component_obj: /* Type */ = match namespace_obj.component(component) {
110.7     |                          ++++++++++++
110.7
110.7 error[E0282]: type annotations needed
110.7    --> /opt/dynamo/lib/llm/src/http/service/clear_kv_blocks.rs:127:26
110.7     |
110.7 127 |                     Some(e.to_string()),
110.7     |                          ^ cannot infer type
110.7
110.7 error[E0599]: the function or associated item `from_client` exists for struct `PushRouter<(), serde_json::Value>`, but its trait bounds were not satisfied
110.7    --> /opt/dynamo/lib/llm/src/http/service/clear_kv_blocks.rs:133:65
110.7     |
110.7 133 |         let router = match PushRouter::<(), serde_json::Value>::from_client(
110.7     |                                                                 ^^^^^^^^^^^ function or associated item cannot be called on `PushRouter<(), serde_json::Value>` due to unsatisfied trait bounds
110.7     |
110.7    ::: /usr/local/cargo/registry/src/index.crates.io-1949cf8c6b5b557f/serde_json-1.0.149/src/value/mod.rs:116:1
110.7     |
110.7 116 | pub enum Value {
110.7     | -------------- doesn't satisfy `_: MaybeError`
110.7     |
110.7     = note: the following trait bounds were not satisfied:
110.7             `serde_json::Value: dynamo_runtime::protocols::maybe_error::MaybeError`
110.7
110.7 error[E0282]: type annotations needed
110.7    --> /opt/dynamo/lib/llm/src/http/service/clear_kv_blocks.rs:118:13
110.7     |
110.7 118 |         let client = match endpoint.client().await {
110.7     |             ^^^^^^
110.7 ...
110.7 134 |             client.clone(),
110.7     |             ------ type must be known at this point
110.7     |
110.7 help: consider giving `client` an explicit type
110.7     |
110.7 118 |         let client: /* Type */ = match endpoint.client().await {
110.7     |                   ++++++++++++
110.7
110.7 error[E0282]: type annotations needed
110.7    --> /opt/dynamo/lib/llm/src/http/service/clear_kv_blocks.rs:147:26
110.7     |
110.7 147 |                     Some(e.to_string()),
110.7     |                          ^ cannot infer type
110.7
110.7 error[E0282]: type annotations needed
110.7    --> /opt/dynamo/lib/llm/src/http/service/clear_kv_blocks.rs:169:26
110.7     |
110.7 169 |                     Some(e.to_string()),
110.7     |                          ^ cannot infer type
110.7
110.7 error[E0282]: type annotations needed
110.7    --> /opt/dynamo/lib/llm/src/http/service/clear_kv_blocks.rs:160:13
110.7     |
110.7 160 |         let discovery_instances = match discovery_client.list(discovery_key).await {
110.7     |             ^^^^^^^^^^^^^^^^^^^
110.7 ...
110.7 175 |         if discovery_instances.is_empty() {
110.7     |            ------------------- type must be known at this point
110.7     |
110.7 help: consider giving `discovery_instances` an explicit type
110.7     |
110.7 160 |         let discovery_instances: /* Type */ = match discovery_client.list(discovery_key).await {
110.7     |                                ++++++++++++
110.7
110.7 error[E0282]: type annotations needed
110.7    --> /opt/dynamo/lib/llm/src/http/service/clear_kv_blocks.rs:196:71
110.7     |
110.7 196 |             let instance_name = format!("{}-instance-{}", entry.name, instance.id());
110.7     |                                                                       ^^^^^^^^ cannot infer type
110.7
110.7 error[E0282]: type annotations needed
110.7    --> /opt/dynamo/lib/llm/src/http/service/clear_kv_blocks.rs:133:13
110.7     |
110.7 133 |         let router = match PushRouter::<(), serde_json::Value>::from_client(
110.7     |             ^^^^^^
110.7 ...
110.7 197 |             match router.direct(().into(), instance.id()).await {
110.7     |                   ------ type must be known at this point
110.7     |
110.7 help: consider giving `router` an explicit type
110.7     |
110.7 133 |         let router: /* Type */ = match PushRouter::<(), serde_json::Value>::from_client(
110.7     |                   ++++++++++++
110.7
110.7 error[E0282]: type annotations needed
110.7    --> /opt/dynamo/lib/llm/src/http/service/clear_kv_blocks.rs:198:41
110.7     |
110.7 198 |                 Ok(mut stream) => match stream.next().await {
110.7     |                                         ^^^^^^ cannot infer type
110.7
110.7 error[E0282]: type annotations needed
110.7    --> /opt/dynamo/lib/llm/src/http/service/clear_kv_blocks.rs:206:34
110.7     |
110.7 206 | ...                   Some(response.to_string()),
110.7     |                            ^^^^^^^^ cannot infer type
110.7
110.7 error[E0282]: type annotations needed
110.7    --> /opt/dynamo/lib/llm/src/http/service/clear_kv_blocks.rs:227:30
110.7     |
110.7 227 |                         Some(e.to_string()),
110.7     |                              ^ cannot infer type
110.7
129.7 Some errors have detailed explanations: E0282, E0599.
129.7 For more information about an error, try `rustc --explain E0282`.
129.7 warning: dynamo-llm@1.2.0: Building with CUDA KV off
129.7 warning: dynamo-llm@1.2.0: Found FATBIN at default location: ./src/block_manager/block/transfer/kernels/vectorized_copy.fatbin
129.7 warning: dynamo-llm@1.2.0: CUDA FATBIN found at: ./src/block_manager/block/transfer/kernels/vectorized_copy.fatbin - copied to OUT_DIR
129.7 error: could not compile `dynamo-llm` (lib) due to 18 previous errors
129.7 💥 maturin failed
129.7   Caused by: Failed to build a native library through cargo
129.7   Caused by: Cargo build finished with "exit status: 101": `env -u CARGO PYO3_BUILD_EXTENSION_MODULE="1" PYO3_ENVIRONMENT_SIGNATURE="cpython-3.12-64bit" PYO3_PYTHON="/workspace/.venv/bin/python" PYTHON_SYS_EXECUTABLE="/workspace/.venv/bin/python" "cargo" "rustc" "--profile" "release" "--features" "kv-indexer" "--message-format" "json-render-diagnostics" "--manifest-path" "/opt/dynamo/lib/bindings/python/Cargo.toml" "--lib" "--crate-type" "cdylib"`
------
ERROR: failed to solve: process "/bin/sh -c export AWS_WEB_IDENTITY_TOKEN_FILE=/run/secrets/aws-token &&     export UV_CACHE_DIR=/root/.cache/uv &&     export SCCACHE_S3_KEY_PREFIX=${SCCACHE_S3_KEY_PREFIX:-${TARGETARCH}} &&     if [ \"$USE_SCCACHE\" = \"true\" ]; then         eval $(/tmp/use-sccache.sh setup-env cmake);     fi &&     mkdir -p ${CARGO_TARGET_DIR} &&     source ${VIRTUAL_ENV}/bin/activate &&     cd /opt/dynamo &&     uv build --wheel --out-dir /opt/dynamo/dist &&     cd /opt/dynamo/lib/bindings/python &&     if [ \"$ENABLE_MEDIA_FFMPEG\" = \"true\" ]; then         maturin build --release --features \"media-ffmpeg,kv-indexer\" --out /opt/dynamo/dist;     else         maturin build --release --features \"kv-indexer\" --out /opt/dynamo/dist;     fi &&     /tmp/use-sccache.sh show-stats \"Dynamo Runtime\"" did not complete successfully: exit code: 1
ojaiyeob@gracehopper:~/kv_cache_offloading$ dynamo-llm` (lib) due to 18 previous errors
129.7 💥 maturin failed
129.7   Caused by: Failed to build a native library through cargo
129.7   Caused by: Cargo build finished with "exit status: 101": `env -u CARGO PYO3_BUILD_EXTENSION_MODULE="1" PYO3_ENVIRONMENT_SIGNATURE="cpython-3.12-64bit" PYO3_PYTHON="/workspace/.venv/bin/python" PYTHON_SYS_EXECUTABLE="/workspace/.venv/bin/python" "cargo" "rustc" "--profile" "release" "--features" "kv-indexer" "--message-format" "json-render-diagnostics" "--manifest-path" "/opt/dynamo/lib/bindings/python/Cargo.toml" "--lib" "--crate-type" "cdylib"`
------
ERROR: failed to solve: process "/bin/sh -c export AWS_WEB_IDENTITY_TOKEN_FILE=/run/secrets/aws-token &&     export UV_CACHE_DIR=/root/.cache/uv &&     export SCCACHE_S3_KEY_PREFIX=${SCCACHE_S3_KEY_PREFIX:-${TARGETARCH}} &&     if [ \"$USE_SCCACHE\" = \"true\" ]; then         eval $(/tmp/use-sccache.sh setup-env cmake);     fi &&     mkdir -p ${CARGO_TARGET_DIR} &&     source ${VIRTUAL_ENV}/bin/activate &&     cd /opt/dynamo &&     uv build --wheel --out-dir /opt/dynamo/dist &&     cd /opt/dynamo/lib/bindings/python &&     if [ \"$ENABLE_MEDIA_FFMPEG\" = \"true\" ]; then         maturin build --release --features \"media-ffmpeg,kv-indexer\" --out /opt/dynamo/dist;     else         maturin build --release --features \"kv-indexer\" --out /opt/dynamo/dist;     fi &&     /tmp/use-sccache.sh show-stats \"Dynamo Runtime\"" did not complete successfully: exit code: 1
ojaiyeob@gracehopper:~/kv_cache_offloading$
^C
ojaiyeob@gracehopper:~/kv_cache_offloading$ ^C
ojaiyeob@gracehopper:~/kv_cache_offloading$
