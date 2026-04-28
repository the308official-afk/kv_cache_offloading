#!/bin/bash

# echo "[INIT] Running transfer-sglang-files.sh..."
# ssh -J ojaiyeob@falcon.7elements.com:1337 ojaiyeob@gracehopper
# ojaiyeob@gracehopper:~/sglang$ ./run_docker_sglang.sh storage test
# ojaiyeob@gracehopper:~/sglang$ ./run_docker_sglang.sh storage pg1184
# ojaiyeob@gracehopper:~/sglang$ ./run_docker_sglang.sh storage pg1184_wflush
# ojaiyeob@gracehopper:~/sglang$ ./run_docker_sglang.sh storage pg1184_wflush_aggressive
# ojaiyeob@gracehopper:~/sglang$ ./run_docker_sglang.sh storage synthetic_prefix_repeat
# ojaiyeob@gracehopper:~/sglang$ nohup ./run_docker_sglang.sh storage main
# ojaiyeob@gracehopper:~/sglang$ nohup ./run_docker_sglang.sh host main
# ojaiyeob@gracehopper:~/sglang$ nohup ./run_docker_sglang.sh hbm main
# ojaiyeob@gracehopper:~/sglang$ ./run_docker_sglang.sh shrink test
# ojaiyeob@gracehopper:~/sglang$ ./run_docker_sglang.sh storage force_s2h_transfs

HOST_HOME_DIR="${HOST_HOME_DIR:-$HOME}"
SGLANG_ROOT="${SGLANG_ROOT:-${HOST_HOME_DIR}/kv_cache_offloading/sglang}"
SGLANG_CACHE_DIR="${SGLANG_CACHE_DIR:-${HOST_HOME_DIR}/kv_cache_offloading/sglang_cache}"
STUDY_ROOT="${STUDY_ROOT:-${HOST_HOME_DIR}/kv_cache_offloading/output}"
VLLM_ROOT="${VLLM_ROOT:-${HOST_HOME_DIR}/kv_cache_offloading/vllm}"
VLLM_CLIENT_DIR="${VLLM_CLIENT_DIR:-${VLLM_ROOT}/kv_cache_offloading/vllm/vllm_client}"
VLLM_CACHE_DIR="${VLLM_CACHE_DIR:-${HOST_HOME_DIR}/kv_cache_offloading/vllm/vllm_cache}"
HICACHE_HOST_DIR="${HICACHE_HOST_DIR:-/hicache_disk}"

HICACHE_DISK_PATH="/workspace/hicache_disk"
# HICACHE_DISK_PATH="/workspace/data/hicache_disk"
SGLANG_PYTHONPATH="/workspace/sglang/python"

echo "------------------- Clearing out hicache_disk contents... -------------------"
sudo rm -rf ${HICACHE_HOST_DIR} && sudo mkdir ${HICACHE_HOST_DIR} && sudo chmod 777 ${HICACHE_HOST_DIR}

IS_TEST=${2:-default}

# models and datasets
# LLM_MODELS=('deepseek-ai/deepseek-llm-7b-chat' 'meta-llama/Llama-3.2-1B' 'meta-llama/Llama-2-7b-chat-hf' 'hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4')
# LLM_MODEL_NAMES=('deepseek-llm-7b-chat' 'Llama-3.2-1B' 'Llama-2-7b-chat-hf' 'Meta-Llama-3.1-70B-Instruct-AWQ-INT4')
# DATASETS=('ultrachat_200k' 'symbolic_instruction_tuning_800k' 'toucan_1pt5m')

LLM_MODELS=('meta-llama/Llama-2-7b-chat-hf')
LLM_MODEL_NAMES=('Llama-2-7b-chat-hf')
# LLM_MODELS=('deepseek-ai/deepseek-llm-7b-chat')
# LLM_MODEL_NAMES=('deepseek-llm-7b-chat')
# LLM_MODELS=('meta-llama/Llama-3.2-1B')
# LLM_MODEL_NAMES=('Llama-3.2-1B')
DATASETS=('ultrachat_200k')

# important: these allow the switch to enable/disable transfer statistics (e.g., bytes transferred, token IDs transferred, bandwidth etc)
MEM_POOL_BANDWIDTH=1 # DEVICE->HOST, HOST->DEVICE transfer tracking 
MEM_POOL_NODETOKENIDS=1 # DEVICE->HOST, HOST->DEVICE transfer tracking 
HIRADIX_CACHE_NODETOKENIDS=1 # DEVICE->HOST, HOST->DEVICE transfer tracking 
CACHE_CONTROLLER_LANDMARKS=1 # Notifications for backup operations from host memory to storage backend.
HICACHESTORAGE_NODETOKENIDS_H2S=1 # HOST->STORAGE transfer tracking 
HICACHESTORAGE_NODETOKENIDS_S2H=1 # STORAGE->HOST transfer tracking 
HICACHESTORAGE_BANDWIDTH_H2S=1 # HOST->STORAGE transfer tracking 
HICACHESTORAGE_BANDWIDTH_S2H=1 # STORAGE->HOST transfer tracking 

# other parameters set:
BANDWIDTHS___WRITEBACK=(10000) # 1000000, 1000 # NB: these are in MB/s # throttling memory bandwidths
BANDWIDTHS___LOADBACK=(10000)
BANDWIDTHS___WRITETHROUGH=(1000000000) # throttling storage bandwidths
BANDWIDTHS___PREFETCH=(1000000000)
STORAGE_WRITE_POLICY=('write_through_selective') # ('write_through' 'write_through_selective')
WRITE_THROUGH_THRESHOLD=4 #8*, 16 # wasn't exposed by sglang developers yet (found in hiradix_cache/_inc_hit_count)
LINK_CHANNEL_THRESHOLD_MB___WRITEBACK=(60) #(20 50 100) # throttling memory bandwidths
LINK_CHANNEL_THRESHOLD_MB___LOADBACK=(60) #(20 50 100)
LINK_CHANNEL_THRESHOLD_MB___WRITETHROUGH=(0) #(20 50 100) # throttling storage bandwidths
LINK_CHANNEL_THRESHOLD_MB___PREFETCH=(0) #(20 50 100)
NEW_SKIP_PRINT_FREQ__HBM_HOST=1
NEW_SKIP_PRINT_FREQ__HOST_STORAGE=1

# use these to prevent sglang from overwhelming the single GH200 with excessive concurrent request thereby breaking the code and dramatically slowing down performance:
MAX_TOTAL_TOKENS=40000
CHUNKED_PREFILL_SIZE=1024
MAX_PREFILL_TOKENS=8192
MAX_QUEUED_REQUESTS=128
LOG_LEVEL="debug" # debug, critical
# LOG_LEVEL="critical"

# docker/log files cleanup
docker stop docker-sglang-server
docker stop docker-sglang-client
rm -rf ${STUDY_ROOT}/output_server--*
rm -rf ${STUDY_ROOT}/output_client--*
rm -rf ${SGLANG_ROOT}/sglang_traffic*

# Clear nohup file
# > ${SGLANG_ROOT}/nohup.out

for ((model = 0; model < ${#LLM_MODELS[@]}; model++))
do
    for ((dataset = 0; dataset < ${#DATASETS[@]}; dataset++))
    do
		for ((bw = 0; bw < ${#BANDWIDTHS___WRITEBACK[@]}; bw++))
		do
			for ((linkthreshold = 0; linkthreshold < ${#LINK_CHANNEL_THRESHOLD_MB___WRITEBACK[@]}; linkthreshold++))
			do
				for ((policy = 0; policy < ${#STORAGE_WRITE_POLICY[@]}; policy++))
				do
					echo "Running ${DATASETS[dataset]} dataset on ${LLM_MODELS[model]} model..." # if node.hit_count >= self.write_through_threshold:
					
					# Remove existing containers
					docker container rm docker-sglang-server -f 2>/dev/null
					docker container rm docker-sglang-client -f 2>/dev/null
					docker container rm docker-vllm-client -f 2>/dev/null
					docker ps
					
					# Enabling functionality to print out bytes transferred/token IDs transferred/ etc
					sed -i "s|^mem_pool_host__debug__bandwidth=.*|mem_pool_host__debug__bandwidth=${MEM_POOL_BANDWIDTH}|" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/memory_pool_host.py
					sed -i "s|^mem_pool_host__debug__nodetokenids=.*|mem_pool_host__debug__nodetokenids=${MEM_POOL_NODETOKENIDS}|" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/memory_pool_host.py
					sed -i "s|^hiradix_cache__debug__nodetokenids=.*|hiradix_cache__debug__nodetokenids=${HIRADIX_CACHE_NODETOKENIDS}|" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/hiradix_cache.py
					sed -i "s|^cachecontroller__debug__landmarks=.*|cachecontroller__debug__landmarks=${CACHE_CONTROLLER_LANDMARKS}|" ${SGLANG_ROOT}/python/sglang/srt/managers/cache_controller.py
					sed -i "s|^hicache_storage__debug__nodetokenids_h2s=.*|hicache_storage__debug__nodetokenids_h2s=${HICACHESTORAGE_NODETOKENIDS_H2S}|" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/hicache_storage.py
					sed -i "s|^hicache_storage__debug__nodetokenids_s2h=.*|hicache_storage__debug__nodetokenids_s2h=${HICACHESTORAGE_NODETOKENIDS_S2H}|" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/hicache_storage.py
					sed -i "s|^hicache_storage__debug__bandwidth_h2s=.*|hicache_storage__debug__bandwidth_h2s=${HICACHESTORAGE_BANDWIDTH_H2S}|" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/hicache_storage.py
					sed -i "s|^hicache_storage__debug__bandwidth_s2h=.*|hicache_storage__debug__bandwidth_s2h=${HICACHESTORAGE_BANDWIDTH_S2H}|" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/hicache_storage.py
					
					# Replace the model in the sample.py file
					sed -i "s|LLM_MODEL=\".*\"|LLM_MODEL=\"${LLM_MODELS[model]}\"|" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/hiradix_cache.py
					sed -i "s|LLM_MODEL=\".*\"|LLM_MODEL=\"${LLM_MODELS[model]}\"|" ${SGLANG_ROOT}/python/sglang/srt/managers/cache_controller.py
					sed -i "s/max_bw__writeback=[0-9]*/max_bw__writeback=${BANDWIDTHS___WRITEBACK[bw]}/g" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/memory_pool_host.py
					sed -i "s/max_bw__loadback=[0-9]*/max_bw__loadback=${BANDWIDTHS___LOADBACK[bw]}/g" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/memory_pool_host.py
					sed -i "s/max_bw__stwritethrough=[0-9]*/max_bw__stwritethrough=${BANDWIDTHS___WRITETHROUGH[bw]}/g" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/hicache_storage.py
					sed -i "s/max_bw__stprefetch=[0-9]*/max_bw__stprefetch=${BANDWIDTHS___PREFETCH[bw]}/g" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/hicache_storage.py
					sed -i -E "s/(^|[^=%])SKIP_PRINT_FREQ=([0-9]+)/\1SKIP_PRINT_FREQ=${NEW_SKIP_PRINT_FREQ__HBM_HOST}/g" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/hiradix_cache.py
					sed -i -E "s/(^|[^=%])SKIP_PRINT_FREQ=([0-9]+)/\1SKIP_PRINT_FREQ=${NEW_SKIP_PRINT_FREQ__HBM_HOST}/g" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/memory_pool_host.py
					sed -i -E "s/(^|[^=%])SKIP_PRINT_FREQ=([0-9]+)/\1SKIP_PRINT_FREQ=${NEW_SKIP_PRINT_FREQ__HOST_STORAGE}/g" ${SGLANG_ROOT}/python/sglang/srt/managers/cache_controller.py
					sed -i -E "s/(^|[^=%])SKIP_PRINT_FREQ=([0-9]+)/\1SKIP_PRINT_FREQ=${NEW_SKIP_PRINT_FREQ__HOST_STORAGE}/g" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/hicache_storage.py
					sed -i -E "s/(^|[^=%])LINK_CHANNEL_THRESHOLD_MB___WRITEBACK=([0-9]+)/\1LINK_CHANNEL_THRESHOLD_MB___WRITEBACK=${LINK_CHANNEL_THRESHOLD_MB___WRITEBACK[linkthreshold]}/g" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/memory_pool_host.py
					sed -i -E "s/(^|[^=%])LINK_CHANNEL_THRESHOLD_MB___LOADBACK=([0-9]+)/\1LINK_CHANNEL_THRESHOLD_MB___LOADBACK=${LINK_CHANNEL_THRESHOLD_MB___LOADBACK[linkthreshold]}/g" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/memory_pool_host.py
					sed -i -E "s/(^|[^=%])LINK_CHANNEL_THRESHOLD_MB___WRITETHROUGH=([0-9]+)/\1LINK_CHANNEL_THRESHOLD_MB___WRITETHROUGH=${LINK_CHANNEL_THRESHOLD_MB___WRITETHROUGH[linkthreshold]}/g" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/hicache_storage.py
					sed -i -E "s/(^|[^=%])LINK_CHANNEL_THRESHOLD_MB___PREFETCH=([0-9]+)/\1LINK_CHANNEL_THRESHOLD_MB___PREFETCH=${LINK_CHANNEL_THRESHOLD_MB___PREFETCH[linkthreshold]}/g" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/hicache_storage.py
					sed -i -E "s/(^|[^=%])WRITE_THROUGH_THRESHOLD=([0-9]+)/\1WRITE_THROUGH_THRESHOLD=${WRITE_THROUGH_THRESHOLD}/g" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/hiradix_cache.py
			
					# Print the modified line sd
					grep "LLM_MODEL=" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/hiradix_cache.py
					grep "max_bw=" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/memory_pool_host.py
					grep "LLM_MODEL=" ${SGLANG_ROOT}/python/sglang/srt/managers/cache_controller.py
					grep "SKIP_PRINT_FREQ=" ${SGLANG_ROOT}/python/sglang/srt/managers/cache_controller.py
					grep "max_bw__writeback=" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/memory_pool_host.py
					grep "max_bw__stwritethrough=" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/hicache_storage.py
					grep "LINK_CHANNEL_THRESHOLD_MB___WRITEBACK=" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/memory_pool_host.py
					grep "WRITE_THROUGH_THRESHOLD=" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/hiradix_cache.py
					
					grep "^mem_pool_host__debug__bandwidth=" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/memory_pool_host.py
					grep "^mem_pool_host__debug__nodetokenids=" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/memory_pool_host.py
					grep "^hiradix_cache__debug__nodetokenids=" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/hiradix_cache.py
					grep "^cachecontroller__debug__landmarks=" ${SGLANG_ROOT}/python/sglang/srt/managers/cache_controller.py
					grep "^hicache_storage__debug__nodetokenids_h2s=" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/hicache_storage.py
					grep "^hicache_storage__debug__nodetokenids_s2h=" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/hicache_storage.py
					grep "^hicache_storage__debug__bandwidth_h2s=" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/hicache_storage.py
					grep "^hicache_storage__debug__bandwidth_s2h=" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/hicache_storage.py
					
					# sed -i "s|^mem_pool_host__debug__bandwidth=.*|mem_pool_host__debug__bandwidth=${YOUR_BANDWIDTH_VALUE}|" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/memory_pool_host.py
					# sed -i "s|^mem_pool_host__debug__nodetokenids=.*|mem_pool_host__debug__nodetokenids=${YOUR_NODETOKENIDS_VALUE}|" ${SGLANG_ROOT}/python/sglang/srt/mem_cache/memory_pool_host.py

					sleep 2
				
					# clear SSD storage 
					echo "------------------- Clearing out hicache_disk contents... -------------------"
					sudo rm -rf ${HICACHE_HOST_DIR} && sudo mkdir ${HICACHE_HOST_DIR} && sudo chmod 777 ${HICACHE_HOST_DIR}
					sudo rm -rf ${SGLANG_ROOT}/sglang_traffic.csv

					# -----------------------------
					# Run SERVER (interractive mode)
					# -----------------------------
					if false; then
						docker container rm docker-sglang-server -f 2>/dev/null
						HOST_HOME_DIR="${HOST_HOME_DIR:-$HOME}"
						SGLANG_ROOT="${SGLANG_ROOT:-${HOST_HOME_DIR}/kv_cache_offloading/sglang}"
						SGLANG_CACHE_DIR="${SGLANG_CACHE_DIR:-${HOST_HOME_DIR}/kv_cache_offloading/sglang_cache}"
						STUDY_ROOT="${STUDY_ROOT:-${HOST_HOME_DIR}/kv_cache_offloading/output}"
						HICACHE_HOST_DIR="${HICACHE_HOST_DIR:-${HOST_HOME_DIR}/kv_cache_offloading/hicache_disk}"
						HICACHE_DISK_PATH="${HICACHE_DISK_PATH:-/workspace/hicache_disk}"
						mkdir -p "$SGLANG_CACHE_DIR" "$STUDY_ROOT" "$HICACHE_HOST_DIR"
						docker run -it \
							--gpus all \
							--env "HF_TOKEN=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" \
							-e HF_HOME=/models/hfcache \
							-e SGLANG_TRAFFIC_LOG=/workspace/sglang/sglang_traffic.csv \
							-e SGLANG_TRAFFIC_FLUSH_EVERY=16 \
							-v "${SGLANG_CACHE_DIR}:/models/hfcache" \
							-v "${SGLANG_ROOT}:/workspace/sglang" \
							-v "${HICACHE_HOST_DIR}:${HICACHE_DISK_PATH}" \
							-v "${STUDY_ROOT}:/workspace/output" \
							-w /workspace/sglang \
							--network host \
							--name docker-sglang-server \
							lmsysorg/sglang:latest \
							bash -i

						PYTHONPATH="/workspace/sglang/python" python3 /workspace/sglang/python/sglang/launch_server.py \
							--model-path 'meta-llama/Llama-2-7b-chat-hf' \
							--host 127.0.0.1 \
							--port 30000 \
							--page-size 32 \
							--mem-fraction-static 0.25 \
							--max-running-requests 96 \
							--enable-hierarchical-cache \
							--hicache-ratio 1.5 \
							--hicache-write-policy write_through_selective \
							--max-total-tokens 40000 \
							--chunked-prefill-size 1024 \
							--max-prefill-tokens 8192 \
							--max-queued-requests 128 \
							--hicache-storage-backend file \
							--hicache-storage-prefetch-policy best_effort \
							--file-storage-path /workspace/hicache_disk \
							--enable-cache-report \
							--enable-metrics \
							--log-level debug \
							--log-level-http debug
					fi 
			
					# -----------------------------
					# Run SERVER (non-interractive mode)
					# -----------------------------
					# [--max-queued-requests MAX_QUEUED_REQUESTS] [--max-total-tokens MAX_TOTAL_TOKENS] [--chunked-prefill-size CHUNKED_PREFILL_SIZE] [--max-prefill-tokens MAX_PREFILL_TOKENS]
					SERVER_TYPE=${1:-default}
					if [ "$SERVER_TYPE" = "storage" ]; then
						echo "------------------- Invoking special sglang server run (last level=storage, hicache enabled)... -------------------"
						docker run \
						--env "HF_TOKEN=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" \
						-e HF_HOME=/models/hfcache \
						-e SGLANG_TRAFFIC_LOG=/workspace/sglang/sglang_traffic.csv \
						-e SGLANG_TRAFFIC_FLUSH_EVERY=16 \
						-v ${SGLANG_CACHE_DIR}:/models/hfcache \
						-v ${SGLANG_ROOT}:/workspace/sglang \
						-v ${HICACHE_HOST_DIR}:${HICACHE_DISK_PATH} \
						-v ${STUDY_ROOT}:/workspace/output \
						-w /workspace/sglang \
						--network host \
						--name docker-sglang-server \
						lmsysorg/sglang:latest \
						bash -lc '
								pwd 
								export PYTHONPATH=/workspace/sglang/python
								
								echo "hello" > ${HICACHE_DISK_PATH}/test_file.txt
								export SGLANG_HICACHE_FILE_BACKEND_STORAGE_DIR='"${HICACHE_DISK_PATH}"'
								
								echo "[-INIT-] Running transfer-sglang-files.sh (FIXME)..."
								if true; then
									cp -rf /workspace/sglang/python/sglang/launch_server.py /sgl-workspace/sglang/python/sglang/launch_server.py
									cp -rf /workspace/sglang/python/sglang/bench_serving.py /sgl-workspace/sglang/python/sglang/bench_serving.py
									cp -rf /workspace/sglang/python/sglang/srt/mem_cache/hiradix_cache.py /sgl-workspace/sglang/python/sglang/srt/mem_cache/hiradix_cache.py
									cp -rf /workspace/sglang/python/sglang/srt/managers/cache_controller.py /sgl-workspace/sglang/python/sglang/srt/managers/cache_controller.py
									cp -rf /workspace/sglang/python/sglang/srt/mem_cache/memory_pool_host.py /sgl-workspace/sglang/python/sglang/srt/mem_cache/memory_pool_host.py
									cp -rf /workspace/sglang/python/sglang/srt/mem_cache/hicache_storage.py /sgl-workspace/sglang/python/sglang/srt/mem_cache/hicache_storage.py
									cp -rf /workspace/sglang/python/sglang/srt/managers/schedule_policy.py /sgl-workspace/sglang/python/sglang/srt/managers/schedule_policy.py
									cp -rf /workspace/sglang/python/sglang/srt/managers/scheduler.py /sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py
									cp -rf /workspace/sglang/python/sglang/srt/managers/schedule_batch.py /sgl-workspace/sglang/python/sglang/srt/managers/schedule_batch.py
									cp -rf /workspace/sglang/python/sglang/srt/entrypoints/http_server.py /sgl-workspace/sglang/python/sglang/srt/entrypoints/http_server.py
								fi
						
								python3 /workspace/sglang/python/sglang/launch_server.py \
									--model-path '"${LLM_MODELS[model]}"' \
									--host 127.0.0.1 \
									--port 30000 \
									--page-size 32 \
									--mem-fraction-static 0.25 \
									--max-running-requests 96 \
									--enable-hierarchical-cache \
									--hicache-ratio 1.5 \
									--hicache-write-policy '"${STORAGE_WRITE_POLICY[policy]}"' \
									--max-total-tokens '"${MAX_TOTAL_TOKENS}"' \
									--chunked-prefill-size '"${CHUNKED_PREFILL_SIZE}"' \
									--max-prefill-tokens '"${MAX_PREFILL_TOKENS}"' \
									--max-queued-requests '"${MAX_QUEUED_REQUESTS}"' \
									--hicache-storage-backend file \
									--hicache-storage-prefetch-policy best_effort \
									--file-storage-path /workspace/hicache_disk \
									--enable-cache-report \
									--enable-metrics \
									--log-level '"${LOG_LEVEL}"' \
									--log-level-http '"${LOG_LEVEL}"' \
									| tee /workspace/output/output_server--sglang.log

									' \ &
					fi 
					if [ "$SERVER_TYPE" = "host" ]; then 
						echo "------------------- Invoking basic sglang server (last level=host, hicache enabled)... -------------------"
						docker run \
							--env "HF_TOKEN=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" \
							-e HF_HOME=/models/hfcache \
							-e SGLANG_TRAFFIC_LOG=/workspace/sglang/sglang_traffic.csv \
							-e SGLANG_TRAFFIC_FLUSH_EVERY=16 \
							-v ${SGLANG_CACHE_DIR}:/models/hfcache \
							-v ${SGLANG_ROOT}:/workspace/sglang \
							-v ${STUDY_ROOT}:/workspace/output \
							-w /workspace/sglang \
							--network host \
						--name docker-sglang-server \
						lmsysorg/sglang:latest \
						bash -lc '
									pwd 
									export PYTHONPATH=/workspace/sglang/python
									
									echo "[INIT] Running transfer-sglang-files.sh..."
									if true; then
										cp -rf /workspace/sglang/python/sglang/launch_server.py /sgl-workspace/sglang/python/sglang/launch_server.py
										cp -rf /workspace/sglang/python/sglang/bench_serving.py /sgl-workspace/sglang/python/sglang/bench_serving.py
										cp -rf /workspace/sglang/python/sglang/srt/mem_cache/hiradix_cache.py /sgl-workspace/sglang/python/sglang/srt/mem_cache/hiradix_cache.py
										cp -rf /workspace/sglang/python/sglang/srt/managers/cache_controller.py /sgl-workspace/sglang/python/sglang/srt/managers/cache_controller.py
										cp -rf /workspace/sglang/python/sglang/srt/mem_cache/memory_pool_host.py /sgl-workspace/sglang/python/sglang/srt/mem_cache/memory_pool_host.py
										cp -rf /workspace/sglang/python/sglang/srt/mem_cache/hicache_storage.py /sgl-workspace/sglang/python/sglang/srt/mem_cache/hicache_storage.py
										cp -rf /workspace/sglang/python/sglang/srt/managers/schedule_policy.py /sgl-workspace/sglang/python/sglang/srt/managers/schedule_policy.py
										cp -rf /workspace/sglang/python/sglang/srt/managers/scheduler.py /sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py
										cp -rf /workspace/sglang/python/sglang/srt/managers/schedule_batch.py /sgl-workspace/sglang/python/sglang/srt/managers/schedule_batch.py
										cp -rf /workspace/sglang/python/sglang/srt/entrypoints/http_server.py /sgl-workspace/sglang/python/sglang/srt/entrypoints/http_server.py
									fi
								
									python3 /workspace/sglang/python/sglang/launch_server.py \
										--watchdog-timeout 600 \
										--model-path '"${LLM_MODELS[model]}"' \
										--host 127.0.0.1 \
										--port 30000 \
										--page-size 32 \
										--log-level '"${LOG_LEVEL}"' \
										--log-level-http '"${LOG_LEVEL}"' \
										--enable-hierarchical-cache \
										--hicache-write-policy '"${STORAGE_WRITE_POLICY[policy]}"' \
										--max-total-tokens '"${MAX_TOTAL_TOKENS}"' \
										--chunked-prefill-size '"${CHUNKED_PREFILL_SIZE}"' \
										--max-prefill-tokens '"${MAX_PREFILL_TOKENS}"' \
										--max-queued-requests '"${MAX_QUEUED_REQUESTS}"' \
										| tee /workspace/output/output_server--'"${LLM_MODEL_NAMES[model]}"'--'"${DATASETS[dataset]}"'--'"${STORAGE_WRITE_POLICY[policy]}"'--bw'"${bw}"'--linkthresh'"${LINK_CHANNEL_THRESHOLD_MB___WRITEBACK[linkthreshold]}"'.log' \ &
					fi 
					if [ "$SERVER_TYPE" = "hbm" ]; then 
						echo "------------------- Invoking basic sglang server (last level=HBM, hicache disabled)... -------------------"
						docker run \
							--env "HF_TOKEN=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" \
							-e HF_HOME=/models/hfcache \
							-e SGLANG_TRAFFIC_LOG=/workspace/sglang/sglang_traffic.csv \
							-e SGLANG_TRAFFIC_FLUSH_EVERY=16 \
							-v ${SGLANG_CACHE_DIR}:/models/hfcache \
							-v ${SGLANG_ROOT}:/workspace/sglang \
							-v ${STUDY_ROOT}:/workspace/output \
							-w /workspace/sglang \
							--network host \
						--name docker-sglang-server \
						lmsysorg/sglang:latest \
						bash -lc '
									pwd 
									export PYTHONPATH=/workspace/sglang/python

									echo "[INIT] Running transfer-sglang-files.sh..."
									if true; then
										cp -rf /workspace/sglang/python/sglang/launch_server.py /sgl-workspace/sglang/python/sglang/launch_server.py
										cp -rf /workspace/sglang/python/sglang/bench_serving.py /sgl-workspace/sglang/python/sglang/bench_serving.py
										cp -rf /workspace/sglang/python/sglang/srt/mem_cache/hiradix_cache.py /sgl-workspace/sglang/python/sglang/srt/mem_cache/hiradix_cache.py
										cp -rf /workspace/sglang/python/sglang/srt/managers/cache_controller.py /sgl-workspace/sglang/python/sglang/srt/managers/cache_controller.py
										cp -rf /workspace/sglang/python/sglang/srt/mem_cache/memory_pool_host.py /sgl-workspace/sglang/python/sglang/srt/mem_cache/memory_pool_host.py
										cp -rf /workspace/sglang/python/sglang/srt/mem_cache/hicache_storage.py /sgl-workspace/sglang/python/sglang/srt/mem_cache/hicache_storage.py
										cp -rf /workspace/sglang/python/sglang/srt/managers/schedule_policy.py /sgl-workspace/sglang/python/sglang/srt/managers/schedule_policy.py
										cp -rf /workspace/sglang/python/sglang/srt/managers/scheduler.py /sgl-workspace/sglang/python/sglang/srt/managers/scheduler.py
										cp -rf /workspace/sglang/python/sglang/srt/managers/schedule_batch.py /sgl-workspace/sglang/python/sglang/srt/managers/schedule_batch.py
										cp -rf /workspace/sglang/python/sglang/srt/entrypoints/http_server.py /sgl-workspace/sglang/python/sglang/srt/entrypoints/http_server.py
									fi
									
									python3 /workspace/sglang/python/sglang/launch_server.py \
										--watchdog-timeout 600 \
										--model-path '"${LLM_MODELS[model]}"' \
										--host 127.0.0.1 \
										--port 30000 \
										--page-size 32 \
										--log-level '"${LOG_LEVEL}"' \
										--log-level-http '"${LOG_LEVEL}"' \
										--max-total-tokens '"${MAX_TOTAL_TOKENS}"' \
										--chunked-prefill-size '"${CHUNKED_PREFILL_SIZE}"' \
										--max-prefill-tokens '"${MAX_PREFILL_TOKENS}"' \
										--max-queued-requests '"${MAX_QUEUED_REQUESTS}"' \
										| tee /workspace/output/output_server--'"${LLM_MODEL_NAMES[model]}"'--'"${DATASETS[dataset]}"'--'"${STORAGE_WRITE_POLICY[policy]}"'--bw'"${bw}"'--linkthresh'"${LINK_CHANNEL_THRESHOLD_MB___WRITEBACK[linkthreshold]}"'.log' \ &
					fi 
					if [ "$SERVER_TYPE" = "README" ]; then
						# --mem-fraction-static MEM_FRACTION_STATIC: The fraction of the memory used for static allocation (model weights and KV cache memory pool). Use a smaller value if you see out-of-memory errors.
						# --hicache-ratio HICACHE_RATIO: The ratio of the size of host KV cache memory pool to the size of device pool.
						# --hicache-size HICACHE_SIZE: The size of host KV cache memory pool in gigabytes, which will override the hicache_ratio if set.
						# export SGLANG_HICACHE_FILE_BACKEND_STORAGE_DIR=/workspace/sglang/hicache_disk
						# --mem-fraction-static 0.3 \
						# --hicache-ratio 1.1 \
						# --hicache-write-policy {write_back,write_through,write_through_selective}
							# The write policy of hierarchical cache.
						# echo "hello" > /workspace/data/hicache_disk/test_file.txt
						# --hicache-size 250 \
						# --log-level debug \
						# def watchdog_thread(self): (scheduler.py)
						PYTHONPATH="${SGLANG_PYTHONPATH}" python3 /workspace/sglang/python/sglang/launch_server.py \
							--watchdog-timeout 1200 \
							--model-path '"${LLM_MODELS[model]}"' \
							--host 127.0.0.1 \
							--port 30000 \
							--log-level debug \
							--log-level-http critical \
							--enable-hierarchical-cache \
							--hicache-size 250 \
							--hicache-storage-backend file \
							--file-storage-path /workspace/hicache_disk \
							--hicache-write-policy write_through \
							| tee /workspace/output/output_server--'"${LLM_MODEL_NAMES[model]}"'--'"${DATASETS[dataset]}"'--write-through.log
					fi
					
					SERVER_PID=$!
					echo "Server PID: $SERVER_PID"
					# Wait for server readiness (up to 20 minutes)
					echo "Waiting for server to become ready on http://127.0.0.1:30000 ..."
					READY=0
					for i in $(seq 1 240); do
					  if curl -sf http://127.0.0.1:30000/v1/models >/dev/null; then
						READY=1
						break
					  fi
					  sleep 5
					done
					if [ "$READY" -ne 1 ]; then
					  echo "Server did not become ready. Last logs:"
					  docker logs --tail 200 docker-sglang-server || true
					  kill $SERVER_PID 2>/dev/null || true
					  wait $SERVER_PID 2>/dev/null || true
					  exit 1
					fi
					echo "Server is ready. Starting client in 10 secs..."
					sleep 10

					# -----------------------------
					# Run CLIENT (foreground) | 10,10000 | 10,1000 | 100,1000*
					# -----------------------------
					RUN_DOCKER_TEST=${2:-default}
					if [ "$RUN_DOCKER_TEST" = "pg1184" ]; then
						echo "------------------- Invoking pg1184 dataset for client (this dataset encourages s2h transfers)... -------------------"
						export HF_TOKEN="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" 
						export HF_SPLIT="train"
						export LIMIT="50"
						export MAX_TOKENS="128"
						export TEMPERATURE="0.2"
						export VLLM_MODEL=${LLM_MODELS[model]}
						docker run --name docker-vllm-client \
							--entrypoint bash \
							--network host \
							-e HF_TOKEN="$HF_TOKEN" \
							-e HF_DATASETS_CACHE="/models/hfcache" \
							-v ${VLLM_CACHE_DIR}:/models/hfcache \
							-v ${STUDY_ROOT}:/vllm-workspace/output \
							-v ${VLLM_CLIENT_DIR}:/vllm-workspace/vllm_client \
							-v ${VLLM_CLIENT_DIR}/benchmark_serving_multi_turn.py:/vllm-workspace/benchmarks/multi_turn/benchmark_serving_multi_turn.py:ro \
							-v ${VLLM_CLIENT_DIR}/bench_dataset.py:/vllm-workspace/benchmarks/multi_turn/bench_dataset.py:ro \
							vllm/vllm-openai:latest \
							-lc '
								cd /vllm-workspace/benchmarks/multi_turn/
								export MODEL_PATH='"${LLM_MODELS[model]}"'
								cp -rf /vllm-workspace/vllm_client/pg1184.txt /vllm-workspace/benchmarks/multi_turn/pg1184.txt
								pip install pandas
								
								cat > /tmp/phase1_input.json << '"'"'JSONEOF'"'"'
{
  "filetype": "generate_conversations",
  "num_conversations": 128,
  "text_files": ["pg1184.txt"],
  "print_stats": true,
  "prompt_input": {
    "num_turns": {
      "distribution": "uniform",
      "min": 14,
      "max": 26
    },
    "common_prefix_num_tokens": {
      "distribution": "constant",
      "value": 1024
    },
    "prefix_num_tokens": {
      "distribution": "lognormal",
      "average": 100,
      "max": 1000
    },
    "num_tokens": {
      "distribution": "uniform",
      "min": 64,
      "max": 160
    }
  },
  "prompt_output": {
    "num_tokens": {
      "distribution": "uniform",
      "min": 16,
      "max": 64
    }
  }
}
JSONEOF

								python3 benchmark_serving_multi_turn.py \
								  --model '"${LLM_MODELS[model]}"' \
								  --url http://localhost:30000 \
								  --served-model-name '"${LLM_MODELS[model]}"' \
								  --input-file /tmp/phase1_input.json \
								  --num-clients 4 \
								  --max-active-conversations 32
							'
					fi 
					
					SLEEP_TIME=30 # 60
					echo "Sleeping for ${SLEEP_TIME} seconds (to allow all host->storage operations to complete)..."
					sleep $SLEEP_TIME
					
					# -----------------------------
					# Stop SERVER cleanly
					# -----------------------------
					echo "Client completed. Stopping server..."
					docker container rm docker-sglang-server -f 2>/dev/null
					docker container rm docker-sglang-client -f 2>/dev/null
					docker container rm docker-vllm-client -f 2>/dev/null
					
					# -----------------------------
					# Plot throughput chart
					# -----------------------------
					echo "Client completed. Plotting throughput chart..."
					python3 monitor_traffic.py --chart-name "sglang_traffic--${LLM_MODEL_NAMES[model]}--${DATASETS[dataset]}--${STORAGE_WRITE_POLICY[policy]}--bw${bw}--linkthresh${LINK_CHANNEL_THRESHOLD_MB___WRITEBACK[linkthreshold]}.pdf"

					echo "Sleeping for 5 seconds..."
					sleep 5
				done
			done
		done
    done
done

echo FINISH

