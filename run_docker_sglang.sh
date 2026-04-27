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

HICACHE_DISK_PATH="/workspace/hicache_disk"
# HICACHE_DISK_PATH="/workspace/data/hicache_disk"

echo "------------------- Clearing out hicache_disk contents... -------------------"
sudo rm -rf /hicache_disk && sudo mkdir /hicache_disk && sudo chmod 777 /hicache_disk

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
# LOG_LEVEL="debug" # debug, critical
LOG_LEVEL="critical"

# docker/log files cleanup
docker stop docker-sglang-server
docker stop docker-sglang-client
rm -rf /home/central/ojaiyeob/GH200-studies/output_server--*
rm -rf /home/central/ojaiyeob/GH200-studies/output_client--*
rm -rf /home/central/ojaiyeob/sglang/sglang_traffic*

# Clear nohup file
# > /home/central/ojaiyeob/sglang/nohup.out

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
					sed -i "s|^mem_pool_host__debug__bandwidth=.*|mem_pool_host__debug__bandwidth=${MEM_POOL_BANDWIDTH}|" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/memory_pool_host.py
					sed -i "s|^mem_pool_host__debug__nodetokenids=.*|mem_pool_host__debug__nodetokenids=${MEM_POOL_NODETOKENIDS}|" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/memory_pool_host.py
					sed -i "s|^hiradix_cache__debug__nodetokenids=.*|hiradix_cache__debug__nodetokenids=${HIRADIX_CACHE_NODETOKENIDS}|" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/hiradix_cache.py
					sed -i "s|^cachecontroller__debug__landmarks=.*|cachecontroller__debug__landmarks=${CACHE_CONTROLLER_LANDMARKS}|" /home/central/ojaiyeob/sglang/python/sglang/srt/managers/cache_controller.py
					sed -i "s|^hicache_storage__debug__nodetokenids_h2s=.*|hicache_storage__debug__nodetokenids_h2s=${HICACHESTORAGE_NODETOKENIDS_H2S}|" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/hicache_storage.py
					sed -i "s|^hicache_storage__debug__nodetokenids_s2h=.*|hicache_storage__debug__nodetokenids_s2h=${HICACHESTORAGE_NODETOKENIDS_S2H}|" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/hicache_storage.py
					sed -i "s|^hicache_storage__debug__bandwidth_h2s=.*|hicache_storage__debug__bandwidth_h2s=${HICACHESTORAGE_BANDWIDTH_H2S}|" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/hicache_storage.py
					sed -i "s|^hicache_storage__debug__bandwidth_s2h=.*|hicache_storage__debug__bandwidth_s2h=${HICACHESTORAGE_BANDWIDTH_S2H}|" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/hicache_storage.py
					
					# Replace the model in the sample.py file
					sed -i "s|LLM_MODEL=\".*\"|LLM_MODEL=\"${LLM_MODELS[model]}\"|" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/hiradix_cache.py
					sed -i "s|LLM_MODEL=\".*\"|LLM_MODEL=\"${LLM_MODELS[model]}\"|" /home/central/ojaiyeob/sglang/python/sglang/srt/managers/cache_controller.py
					sed -i "s/max_bw__writeback=[0-9]*/max_bw__writeback=${BANDWIDTHS___WRITEBACK[bw]}/g" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/memory_pool_host.py
					sed -i "s/max_bw__loadback=[0-9]*/max_bw__loadback=${BANDWIDTHS___LOADBACK[bw]}/g" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/memory_pool_host.py
					sed -i "s/max_bw__stwritethrough=[0-9]*/max_bw__stwritethrough=${BANDWIDTHS___WRITETHROUGH[bw]}/g" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/hicache_storage.py
					sed -i "s/max_bw__stprefetch=[0-9]*/max_bw__stprefetch=${BANDWIDTHS___PREFETCH[bw]}/g" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/hicache_storage.py
					sed -i -E "s/(^|[^=%])SKIP_PRINT_FREQ=([0-9]+)/\1SKIP_PRINT_FREQ=${NEW_SKIP_PRINT_FREQ__HBM_HOST}/g" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/hiradix_cache.py
					sed -i -E "s/(^|[^=%])SKIP_PRINT_FREQ=([0-9]+)/\1SKIP_PRINT_FREQ=${NEW_SKIP_PRINT_FREQ__HBM_HOST}/g" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/memory_pool_host.py
					sed -i -E "s/(^|[^=%])SKIP_PRINT_FREQ=([0-9]+)/\1SKIP_PRINT_FREQ=${NEW_SKIP_PRINT_FREQ__HOST_STORAGE}/g" /home/central/ojaiyeob/sglang/python/sglang/srt/managers/cache_controller.py
					sed -i -E "s/(^|[^=%])SKIP_PRINT_FREQ=([0-9]+)/\1SKIP_PRINT_FREQ=${NEW_SKIP_PRINT_FREQ__HOST_STORAGE}/g" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/hicache_storage.py
					sed -i -E "s/(^|[^=%])LINK_CHANNEL_THRESHOLD_MB___WRITEBACK=([0-9]+)/\1LINK_CHANNEL_THRESHOLD_MB___WRITEBACK=${LINK_CHANNEL_THRESHOLD_MB___WRITEBACK[linkthreshold]}/g" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/memory_pool_host.py
					sed -i -E "s/(^|[^=%])LINK_CHANNEL_THRESHOLD_MB___LOADBACK=([0-9]+)/\1LINK_CHANNEL_THRESHOLD_MB___LOADBACK=${LINK_CHANNEL_THRESHOLD_MB___LOADBACK[linkthreshold]}/g" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/memory_pool_host.py
					sed -i -E "s/(^|[^=%])LINK_CHANNEL_THRESHOLD_MB___WRITETHROUGH=([0-9]+)/\1LINK_CHANNEL_THRESHOLD_MB___WRITETHROUGH=${LINK_CHANNEL_THRESHOLD_MB___WRITETHROUGH[linkthreshold]}/g" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/hicache_storage.py
					sed -i -E "s/(^|[^=%])LINK_CHANNEL_THRESHOLD_MB___PREFETCH=([0-9]+)/\1LINK_CHANNEL_THRESHOLD_MB___PREFETCH=${LINK_CHANNEL_THRESHOLD_MB___PREFETCH[linkthreshold]}/g" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/hicache_storage.py
					sed -i -E "s/(^|[^=%])WRITE_THROUGH_THRESHOLD=([0-9]+)/\1WRITE_THROUGH_THRESHOLD=${WRITE_THROUGH_THRESHOLD}/g" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/hiradix_cache.py
			
					# Print the modified line sd
					grep "LLM_MODEL=" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/hiradix_cache.py
					grep "max_bw=" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/memory_pool_host.py
					grep "LLM_MODEL=" /home/central/ojaiyeob/sglang/python/sglang/srt/managers/cache_controller.py
					grep "SKIP_PRINT_FREQ=" /home/central/ojaiyeob/sglang/python/sglang/srt/managers/cache_controller.py
					grep "max_bw__writeback=" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/memory_pool_host.py
					grep "max_bw__stwritethrough=" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/hicache_storage.py
					grep "LINK_CHANNEL_THRESHOLD_MB___WRITEBACK=" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/memory_pool_host.py
					grep "WRITE_THROUGH_THRESHOLD=" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/hiradix_cache.py
					
					grep "^mem_pool_host__debug__bandwidth=" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/memory_pool_host.py
					grep "^mem_pool_host__debug__nodetokenids=" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/memory_pool_host.py
					grep "^hiradix_cache__debug__nodetokenids=" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/hiradix_cache.py
					grep "^cachecontroller__debug__landmarks=" /home/central/ojaiyeob/sglang/python/sglang/srt/managers/cache_controller.py
					grep "^hicache_storage__debug__nodetokenids_h2s=" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/hicache_storage.py
					grep "^hicache_storage__debug__nodetokenids_s2h=" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/hicache_storage.py
					grep "^hicache_storage__debug__bandwidth_h2s=" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/hicache_storage.py
					grep "^hicache_storage__debug__bandwidth_s2h=" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/hicache_storage.py
					
					# sed -i "s|^mem_pool_host__debug__bandwidth=.*|mem_pool_host__debug__bandwidth=${YOUR_BANDWIDTH_VALUE}|" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/memory_pool_host.py
					# sed -i "s|^mem_pool_host__debug__nodetokenids=.*|mem_pool_host__debug__nodetokenids=${YOUR_NODETOKENIDS_VALUE}|" /home/central/ojaiyeob/sglang/python/sglang/srt/mem_cache/memory_pool_host.py

					sleep 2
				
					# clear SSD storage 
					echo "------------------- Clearing out hicache_disk contents... -------------------"
					sudo rm -rf /hicache_disk && sudo mkdir /hicache_disk && sudo chmod 777 /hicache_disk
					sudo rm -rf /home/central/ojaiyeob/sglang/sglang_traffic.csv
			
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
						-v /home/central/ojaiyeob/sglang_cache:/models/hfcache \
						-v /home/central/ojaiyeob/sglang:/workspace/sglang \
						-v /hicache_disk:${HICACHE_DISK_PATH} \
						-v /home/central/ojaiyeob/GH200-studies:/workspace/GH200-studies \
						-w /workspace/sglang \
						--network host \
						--name docker-sglang-server \
						lmsysorg/sglang:latest \
						bash -lc '
								pwd 
								
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
									| tee /workspace/GH200-studies/output_server--sglang.log

									' \ &
					fi 
					if [ "$SERVER_TYPE" = "host" ]; then 
						echo "------------------- Invoking basic sglang server (last level=host, hicache enabled)... -------------------"
						docker run \
							--env "HF_TOKEN=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" \
							-e HF_HOME=/models/hfcache \
							-e SGLANG_TRAFFIC_LOG=/workspace/sglang/sglang_traffic.csv \
							-e SGLANG_TRAFFIC_FLUSH_EVERY=16 \
							-v /home/central/ojaiyeob/sglang_cache:/models/hfcache \
							-v /home/central/ojaiyeob/sglang:/workspace/sglang \
							-v /home/central/ojaiyeob/GH200-studies:/workspace/GH200-studies \
							-w /workspace/sglang \
							--network host \
							--name docker-sglang-server \
							lmsysorg/sglang:latest \
							bash -lc '
									pwd 
									
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
										| tee /workspace/GH200-studies/output_server--'"${LLM_MODEL_NAMES[model]}"'--'"${DATASETS[dataset]}"'--'"${STORAGE_WRITE_POLICY[policy]}"'--bw'"${bw}"'--linkthresh'"${LINK_CHANNEL_THRESHOLD_MB___WRITEBACK[linkthreshold]}"'.log' \ &
					fi 
					if [ "$SERVER_TYPE" = "hbm" ]; then 
						echo "------------------- Invoking basic sglang server (last level=HBM, hicache disabled)... -------------------"
						docker run \
							--env "HF_TOKEN=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" \
							-e HF_HOME=/models/hfcache \
							-e SGLANG_TRAFFIC_LOG=/workspace/sglang/sglang_traffic.csv \
							-e SGLANG_TRAFFIC_FLUSH_EVERY=16 \
							-v /home/central/ojaiyeob/sglang_cache:/models/hfcache \
							-v /home/central/ojaiyeob/sglang:/workspace/sglang \
							-v /home/central/ojaiyeob/GH200-studies:/workspace/GH200-studies \
							-w /workspace/sglang \
							--network host \
							--name docker-sglang-server \
							lmsysorg/sglang:latest \
							bash -lc '
									pwd 

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
										| tee /workspace/GH200-studies/output_server--'"${LLM_MODEL_NAMES[model]}"'--'"${DATASETS[dataset]}"'--'"${STORAGE_WRITE_POLICY[policy]}"'--bw'"${bw}"'--linkthresh'"${LINK_CHANNEL_THRESHOLD_MB___WRITEBACK[linkthreshold]}"'.log' \ &
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
						python3 /workspace/sglang/python/sglang/launch_server.py \
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
							| tee /workspace/GH200-studies/output_server--'"${LLM_MODEL_NAMES[model]}"'--'"${DATASETS[dataset]}"'--write-through.log
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
					if [ "$RUN_DOCKER_TEST" = "test" ]; then
						echo "------------------- Invoking test run for client... -------------------"
						docker run \
							--env "HF_TOKEN=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" \
							-e HF_HOME=/models/hfcache \
							-e SGLANG_TRAFFIC_LOG=/workspace/sglang/sglang_traffic.csv \
							-v /home/central/ojaiyeob/sglang_cache:/models/hfcache \
							-v /home/central/ojaiyeob/sglang:/workspace/sglang \
							-v /home/central/ojaiyeob/GH200-studies:/workspace/GH200-studies \
							-v /home/central/ojaiyeob/sglang/benchmark/hicache:/workspace/sglang/benchmark/hicache \
							-w /workspace/sglang/benchmark/hicache \
							--network host \
							--name docker-sglang-client \
							lmsysorg/sglang:latest \
							bash -lc '/workspace/sglang/./transfer-sglang-files.sh && \
									  python3 -m sglang.bench_serving \
										--backend sglang \
										--dataset-name '"${DATASETS[dataset]}"' \
										--num-prompts 10 \
										--host 127.0.0.1 \
										--port 30000 \
										--random-input 256 \
										--random-output 256 \
										--random-range-ratio 0.5 \
										--row-index-start 0 \
										--row-index-end 1000 | tee /workspace/GH200-studies/output_client--'"${LLM_MODEL_NAMES[model]}"'--'"${DATASETS[dataset]}"'--'"${STORAGE_WRITE_POLICY[policy]}"'--bw'"${bw}"'--linkthresh'"${LINK_CHANNEL_THRESHOLD_MB___WRITEBACK[linkthreshold]}"'.log'
					fi
					if [ "$RUN_DOCKER_TEST" = "main" ]; then
						echo "------------------- Invoking main run for client... -------------------"
						docker run \
							--env "HF_TOKEN=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" \
							-e HF_HOME=/models/hfcache \
							-e SGLANG_TRAFFIC_LOG=/workspace/sglang/sglang_traffic.csv \
							-v /home/central/ojaiyeob/sglang_cache:/models/hfcache \
							-v /home/central/ojaiyeob/sglang:/workspace/sglang \
							-v /home/central/ojaiyeob/GH200-studies:/workspace/GH200-studies \
							-v /home/central/ojaiyeob/sglang/benchmark/hicache:/workspace/sglang/benchmark/hicache \
							-w /workspace/sglang/benchmark/hicache \
							--network host \
							--name docker-sglang-client \
							lmsysorg/sglang:latest \
							bash -lc '
								echo "[INIT-CLIENT] Running transfer-sglang-files.sh..."
								cp -rf /workspace/sglang/python/sglang/bench_serving.py /sgl-workspace/sglang/python/sglang/bench_serving.py
								STRIDE=1000
								if false; then
									for i in {0..0}; do
										python3 -m sglang.bench_serving --backend sglang --dataset-name random --num-prompts 100 --host 127.0.0.1 --port 30000
										sleep 2
									done
								fi
								if false; then
									for i in {0..0}; do
										python3 -m sglang.bench_serving --backend sglang --dataset-name '"${DATASETS[dataset]}"' --num-prompts 100 --host 127.0.0.1 --port 30000 --random-input 256 --random-output 256 --row-index-start $((i*${STRIDE})) --row-index-end $((i*${STRIDE} + ${STRIDE})) 
										sleep 2
									done
								fi
								if true; then
									for i in {0..1000}; do
										if [ $i -eq 0 ]; then
											python3 -m sglang.bench_serving --backend sglang --dataset-name '"${DATASETS[dataset]}"' --num-prompts ${STRIDE} --host 127.0.0.1 --port 30000 --random-input 256 --random-output 256 --random-range-ratio 0.5 --row-index-start $((i*${STRIDE})) --row-index-end $((i*${STRIDE} + ${STRIDE})) | tee /workspace/GH200-studies/output_client--'"${LLM_MODEL_NAMES[model]}"'--'"${DATASETS[dataset]}"'--'"${STORAGE_WRITE_POLICY[policy]}"'--bw'"${bw}"'--linkthresh'"${LINK_CHANNEL_THRESHOLD_MB___WRITEBACK[linkthreshold]}"'.log
										else
											python3 -m sglang.bench_serving --backend sglang --dataset-name '"${DATASETS[dataset]}"' --num-prompts ${STRIDE} --host 127.0.0.1 --port 30000 --random-input 256 --random-output 256 --random-range-ratio 0.5 --row-index-start $((i*${STRIDE})) --row-index-end $((i*${STRIDE} + ${STRIDE})) | tee -a /workspace/GH200-studies/output_client--'"${LLM_MODEL_NAMES[model]}"'--'"${DATASETS[dataset]}"'--'"${STORAGE_WRITE_POLICY[policy]}"'--bw'"${bw}"'--linkthresh'"${LINK_CHANNEL_THRESHOLD_MB___WRITEBACK[linkthreshold]}"'.log				
										fi
										sleep 2
									done
								fi 
							'
					fi 
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
							-v /data/ojaiyeob/vllm_cache:/models/hfcache \
							-v /home/central/ojaiyeob/GH200-studies:/vllm-workspace/GH200-studies \
							-v /home/central/ojaiyeob/vllm/vllm_client:/vllm-workspace/vllm_client \
							-v /home/central/ojaiyeob/vllm/vllm_client/benchmark_serving_multi_turn.py:/vllm-workspace/benchmarks/multi_turn/benchmark_serving_multi_turn.py:ro \
							-v /home/central/ojaiyeob/vllm/vllm_client/bench_dataset.py:/vllm-workspace/benchmarks/multi_turn/bench_dataset.py:ro \
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
					if [ "$RUN_DOCKER_TEST" = "pg1184_wflush" ]; then
						echo "------------------- Invoking pg1184_wflush dataset for client (this dataset encourages s2h transfers)... -------------------"
						# Here's the adapted multi-turn client with the same 3-phase STORAGE→HOST forcing strategy:

						export HF_TOKEN="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"
						export HF_DATASET="HuggingFaceH4/ultrachat_200k"
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
							-v /data/ojaiyeob/vllm_cache:/models/hfcache \
							-v /home/central/ojaiyeob/vllm/vllm_client:/vllm-workspace/vllm_client \
							-v /home/central/ojaiyeob/vllm/vllm_client/benchmark_serving_multi_turn.py:/vllm-workspace/benchmarks/multi_turn/benchmark_serving_multi_turn.py:ro \
							-v /home/central/ojaiyeob/vllm/vllm_client/bench_dataset.py:/vllm-workspace/benchmarks/multi_turn/bench_dataset.py:ro \
							-v /home/central/ojaiyeob/GH200-studies:/workspace/GH200-studies \
							vllm/vllm-openai:latest \
							-lc '

								set -e
								BASE_URL="http://localhost:30000"
								MODEL='"${LLM_MODELS[model]}"'
								LOG_DIR="/workspace/GH200-studies"
								BENCH_DIR="/vllm-workspace/benchmarks/multi_turn"

								cd "$BENCH_DIR"
								cp -rf /vllm-workspace/vllm_client/pg1184.txt "$BENCH_DIR/pg1184.txt"
								pip install pandas -q

								# ─────────────────────────────────────────────────────────────
								# HELPER: wait for server
								# ─────────────────────────────────────────────────────────────
								wait_for_server() {
									echo "[CLIENT] Waiting for SGLang server at $BASE_URL ..."
									for i in $(seq 1 60); do
										if curl -sf "$BASE_URL/health" > /dev/null 2>&1; then
											echo "[CLIENT] Server is ready."
											return 0
										fi
										sleep 5
									done
									echo "[CLIENT] ERROR: Server not ready after 5 minutes."
									exit 1
								}

								# ─────────────────────────────────────────────────────────────
								# HELPER: flush host KV cache
								# ─────────────────────────────────────────────────────────────
								flush_host_cache() {
									echo "[CLIENT] Flushing HOST KV cache via /flush_cache ..."
									curl -sf -X POST "$BASE_URL/flush_cache" \
										-H "Content-Type: application/json" \
										&& echo "[CLIENT] /flush_cache OK" \
										|| echo "[CLIENT] WARNING: /flush_cache failed (endpoint may not exist)"
								}

								# ─────────────────────────────────────────────────────────────
								# Generate two input JSON files from the same config structure:
								#   phase1_input.json  — fixed conversations (same prefixes,
								#                        many turns) → populates STORAGE
								#   phase2_input.json  — many unique conversations (lots of
								#                        distinct prefixes) → evicts HOST
								# We reuse the provided generate_multi_turn.json for phase 3
								# (the real benchmark).
								# ─────────────────────────────────────────────────────────────
								echo "[CLIENT] Generating phase input files..."

								# PHASE 1: fewer unique conversations, many turns each
								# → builds up large KV state that gets written to STORAGE
								cat > /tmp/phase1_input.json << '"'"'JSONEOF'"'"'
{
  "filetype": "generate_conversations",
  "num_conversations": 256,
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

								# PHASE 2: many unique conversations with varied prefixes
								# → displaces phase-1 KV pages from HOST memory
								cat > /tmp/phase2_input.json << '"'"'JSONEOF'"'"'
{
  "filetype": "generate_conversations",
  "num_conversations": 2048,
  "text_files": ["pg1184.txt"],
  "print_stats": true,
  "prompt_input": {
	"num_turns": {
	  "distribution": "uniform",
	  "min": 2,
	  "max": 4
	},
	"common_prefix_num_tokens": {
	  "distribution": "constant",
	  "value": 0
	},
	"prefix_num_tokens": {
	  "distribution": "lognormal",
	  "average": 500,
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

								# PHASE 3: 
								cat > /tmp/phase3_input.json << '"'"'JSONEOF'"'"'
{
  "filetype": "generate_conversations",
  "num_conversations": 1024,
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
								wait_for_server

								# ─────────────────────────────────────────────────────────────
								# PHASE 1 — WARM STORAGE
								# Run the multi-turn benchmark with fixed common_prefix so the
								# KV pages are written through to the file backend (STORAGE).
								# Low concurrency / moderate rate → clean sequential writes.
								# ─────────────────────────────────────────────────────────────
								echo ""
								echo "════════════════════════════════════════════════════════"
								echo " PHASE 1 — WARM STORAGE (HOST → STORAGE write)"
								echo "════════════════════════════════════════════════════════"

								python3 benchmark_serving_multi_turn.py \
									--model "$MODEL" \
									--url "$BASE_URL" \
									--input-file /tmp/phase1_input.json \
									--num-clients 4 \
									--max-active-conversations 16 \
									| tee "$LOG_DIR/phase1_warm_storage.log"

								echo "[CLIENT] Phase 1 done. Sleeping 15s to let async writes flush to STORAGE..."
								sleep 15

								# ─────────────────────────────────────────────────────────────
								# PHASE 2 — EVICT HOST CACHE
								# Flood with brand-new diverse conversations so HOST KV pool
								# is completely displaced. Phase-1 KV pages now only live in
								# STORAGE (file backend).
								# ─────────────────────────────────────────────────────────────
								echo ""
								echo "════════════════════════════════════════════════════════"
								echo " PHASE 2 — EVICT HOST CACHE"
								echo "════════════════════════════════════════════════════════"

								flush_host_cache

								python3 benchmark_serving_multi_turn.py \
									--model "$MODEL" \
									--url "$BASE_URL" \
									--input-file /tmp/phase2_input.json \
									--num-clients 16 \
									--max-active-conversations 64 \
									| tee "$LOG_DIR/phase2_evict_host.log"

								echo "[CLIENT] Phase 2 done. Sleeping 5s..."
								sleep 5

								# Verify cache state
								echo ""
								echo "[CLIENT] Cache state after eviction:"
								curl -sf "$BASE_URL/get_server_info" \
									| python3 -m json.tool 2>/dev/null \
									|| curl -sf "$BASE_URL/metrics" \
									| grep -iE "cache|hicache|host|storage" \
									|| echo "[CLIENT] Could not query cache metrics."

								# ─────────────────────────────────────────────────────────────
								# PHASE 3 — FORCE STORAGE → HOST TRANSFERS
								# Replay conversations whose KV pages match phase-1 prefixes.
								# Those pages are no longer in HOST → SGLang fetches them from
								# STORAGE (file backend) → HOST memory.
								# Use the real benchmark JSON (same common_prefix_num_tokens=1024
								# as phase 1, so prefix hashes collide → guaranteed cache hits
								# from STORAGE).
								# ─────────────────────────────────────────────────────────────
								echo ""
								echo "════════════════════════════════════════════════════════"
								echo " PHASE 3 — FORCE STORAGE→HOST (replay with same prefixes)"
								echo "════════════════════════════════════════════════════════"

								python3 benchmark_serving_multi_turn.py \
									--model "$MODEL" \
									--url "$BASE_URL" \
									--input-file /tmp/phase3_input.json \
									--num-clients 4 \
									--max-active-conversations 32 \
									| tee "$LOG_DIR/phase3_storage_to_host.log"

								echo ""
								echo "[CLIENT] Phase 3 complete."

								# ─────────────────────────────────────────────────────────────
								# FINAL METRICS
								# ─────────────────────────────────────────────────────────────
								echo ""
								echo "════════════════════════════════════════════════════════"
								echo " FINAL METRICS"
								echo "════════════════════════════════════════════════════════"
								if true; then
									curl -sf "$BASE_URL/metrics" \
										| grep -iE "cache|hicache|storage|host|prefetch|hit|miss" \
										| tee "$LOG_DIR/final_metrics_multiturn.log" \
										|| echo "[CLIENT] Could not retrieve /metrics."

									curl -sf "$BASE_URL/get_server_info" \
										| python3 -m json.tool \
										| tee "$LOG_DIR/final_server_info_multiturn.log" \
										|| true

									echo "[CLIENT] Done."
									echo "  STORAGE→HOST transfers visible in: $LOG_DIR/phase3_storage_to_host.log"
									echo "  Cache metrics in:                  $LOG_DIR/final_metrics_multiturn.log"
								fi
							'

: <<'COMMENT'
What Changed vs the `prefix_repetition` Version

| Aspect | `prefix_repetition` client | `multi_turn` client |
|---|---|---|
| **Phase 1 tool** | `vllm bench serve --dataset-name prefix_repetition` | `benchmark_serving_multi_turn.py` with `num_conversations=256`, `common_prefix=1024` |
| **Phase 2 tool** | `vllm bench serve --prefix-repetition-num-prefixes 512` | `benchmark_serving_multi_turn.py` with `num_conversations=2048`, `common_prefix=0`, high prefix variance |
| **Phase 3 tool** | Same `prefix_repetition` 48-prefix run | Same `generate_multi_turn.json` you already use (`common_prefix=1024` matches Phase 1) |
| **Eviction mechanism** | More unique prefix IDs than HOST pool capacity | More unique conversations + zero common prefix → no hash collisions with Phase 1 KV pages |
| **STORAGE→HOST trigger** | Prefix hash match in STORAGE but not HOST | `common_prefix_num_tokens=1024` in Phase 3 matches Phase 1 → hash hit in STORAGE, HOST miss |

---

Why `common_prefix_num_tokens=1024` is the Key

```
Phase 1 writes to STORAGE:
  [common_prefix 1024 tokens] → hash H₀ → KV pages → STORAGE file

Phase 2 evicts from HOST:
  [no common prefix, random prefixes] → different hashes → HOST full → H₀ evicted from HOST

Phase 3 triggers STORAGE→HOST:
  [same common_prefix 1024 tokens] → same hash H₀ → HOST miss → STORAGE hit
																	↑
														  STORAGE→HOST transfer
```
COMMENT

					fi 
					if [ "$RUN_DOCKER_TEST" = "pg1184_wflush_aggressive" ]; then
						echo "------------------- Invoking pg1184_wflush_aggressive dataset for client (this dataset encourages s2h transfers)... -------------------"
						# Here's the adapted multi-turn client with the same 3-phase STORAGE→HOST forcing strategy:

						# export HF_TOKEN="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"
						# export HF_DATASET="HuggingFaceH4/ultrachat_200k"
						# export HF_SPLIT="train"
						# export LIMIT="50"
						# export MAX_TOKENS="128"
						# export TEMPERATURE="0.2"
						# export VLLM_MODEL=${LLM_MODELS[model]}
						
						export HF_TOKEN="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"
						export VLLM_MODEL=${LLM_MODELS[model]}
						export LOG_DIR="/workspace/GH200-studies"

						docker run --name docker-vllm-client \
							--entrypoint bash \
							--network host \
							-e HF_TOKEN="$HF_TOKEN" \
							-e HF_DATASETS_CACHE="/models/hfcache" \
							-v /data/ojaiyeob/vllm_cache:/models/hfcache \
							-v /home/central/ojaiyeob/vllm/vllm_client:/vllm-workspace/vllm_client \
							-v /home/central/ojaiyeob/vllm/vllm_client/benchmark_serving_multi_turn.py:/vllm-workspace/benchmarks/multi_turn/benchmark_serving_multi_turn.py:ro \
							-v /home/central/ojaiyeob/vllm/vllm_client/bench_dataset.py:/vllm-workspace/benchmarks/multi_turn/bench_dataset.py:ro \
							-v /home/central/ojaiyeob/GH200-studies:/workspace/GH200-studies \
							vllm/vllm-openai:latest \
							-lc '

							set -e
							BASE_URL="http://localhost:30000"
							MODEL='"${LLM_MODELS[model]}"'
							LOG_DIR="/workspace/GH200-studies"
							BENCH_DIR="/vllm-workspace/benchmarks/multi_turn"

							cd "$BENCH_DIR"
							cp -rf /vllm-workspace/vllm_client/pg1184.txt "$BENCH_DIR/pg1184.txt"
							pip install pandas -q

							# ── wait for server ──────────────────────────────────────────────
							wait_for_server() {
								echo "[CLIENT] Waiting for server..."
								for i in $(seq 1 60); do
									curl -sf "$BASE_URL/health" > /dev/null 2>&1 \
										&& echo "[CLIENT] Server ready." && return 0
									sleep 5
								done
								echo "[CLIENT] ERROR: server never became ready"; exit 1
							}

							# ── flush host KV cache ──────────────────────────────────────────
							flush_host_cache() {
								echo "[CLIENT] Calling /flush_cache ..."
								curl -sf -X POST "$BASE_URL/flush_cache" \
									-H "Content-Type: application/json" \
									&& echo "[CLIENT] flush_cache OK" \
									|| echo "[CLIENT] WARNING: flush_cache failed"
							}

							# ════════════════════════════════════════════════════════════════
							# Write the three JSON configs we need
							# ════════════════════════════════════════════════════════════════

							# ── PHASE 1: warm STORAGE ────────────────────────────────────────
							# Same common_prefix=1024 as your real benchmark.
							# Many conversations repeated enough times that the write-back
							# policy flushes KV pages to the file backend (STORAGE).
							# Fewer unique conversations (128) so each one gets many repeats.
							cat > /tmp/phase1_warm.json << '"'"'EOF'"'"'
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
EOF

							# ── PHASE 2: evict HOST ──────────────────────────────────────────
							# CRITICAL DIFFERENCES vs Phase 1:
							#   common_prefix_num_tokens = 0   → no shared prefix → no hash overlap
							#   prefix_num_tokens average=4000 → large unique prefixes fill HOST fast
							#   num_conversations = 4096       → massive variety = nothing reused
							#   num_turns = 1-2                → short = maximise eviction throughput
							cat > /tmp/phase2_evict.json << '"'"'EOF'"'"'
{
  "filetype": "generate_conversations",
  "num_conversations": 8192,
  "text_files": ["pg1184.txt"],
  "print_stats": true,
  "prompt_input": {
    "num_turns": {
      "distribution": "uniform",
      "min": 1,
      "max": 1
    },
    "common_prefix_num_tokens": {
      "distribution": "constant",
      "value": 0
    },
    "prefix_num_tokens": {
      "distribution": "lognormal",
      "average": 256,
      "max": 512
    },
    "num_tokens": {
      "distribution": "uniform",
      "min": 32,
      "max": 64
    }
  },
  "prompt_output": {
    "num_tokens": {
      "distribution": "uniform",
      "min": 1,
      "max": 4
    }
  }
}
EOF

							# ── PHASE 3: replay → STORAGE→HOST ──────────────────────────────
							# Identical common_prefix=1024 as Phase 1 → hash match in STORAGE.
							# HOST is empty after Phase 2 → every prefix hit comes from STORAGE.
							# Same as your real generate_multi_turn.json but we inline it here
							# so the three phases are self-contained.
							cat > /tmp/phase3_replay.json << '"'"'EOF'"'"'
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
EOF

							wait_for_server

							# ════════════════════════════════════════════════════════════════
							# PHASE 1 — WARM STORAGE
							# Run the same 128 conversations multiple times so write-back
							# policy has enough hits to flush pages to the file backend.
							# Low concurrency = sequential, clean write-backs.
							# ════════════════════════════════════════════════════════════════
							echo ""
							echo "════════════════════════════════════════════════════════════"
							echo " PHASE 1 — WARM STORAGE (write common_prefix pages to disk)"
							echo "════════════════════════════════════════════════════════════"

							python3 benchmark_serving_multi_turn.py \
								--model "$MODEL" \
								--url "$BASE_URL" \
								--input-file /tmp/phase1_warm.json \
								--num-clients 2 \
								--max-active-conversations 8 \
								2>&1 | tee "$LOG_DIR/phase1_warm_storage.log"

							echo "[CLIENT] Phase 1 done. Sleeping 30s for async write-backs to flush to STORAGE..."
							sleep 30

							# ════════════════════════════════════════════════════════════════
							# PHASE 2 — EVICT HOST
							# Flood with 4096 unique conversations that share NO common prefix
							# with Phase 1. Every page they generate is a different hash →
							# Phase 1 pages get LRU-evicted from HOST but survive in STORAGE.
							# ════════════════════════════════════════════════════════════════
							echo ""
							echo "════════════════════════════════════════════════════════════"
							echo " PHASE 2 — EVICT HOST (zero common_prefix, massive variety)"
							echo "════════════════════════════════════════════════════════════"

							# First try the API flush (free, instant)
							flush_host_cache
							sleep 2

							# Then flood with unique traffic to displace any remaining pages
							python3 benchmark_serving_multi_turn.py \
								--model "$MODEL" \
								--url "$BASE_URL" \
								--input-file /tmp/phase2_evict.json \
								--num-clients 16 \
								--max-active-conversations 64 \
								2>&1 | tee "$LOG_DIR/phase2_evict_host.log"

							# Flush again — clear whatever the eviction flood itself cached
							flush_host_cache
							sleep 5

							echo "[CLIENT] Phase 2 done. HOST cache is now empty."
							echo "[CLIENT] Phase 1 pages only exist in STORAGE (file backend)."

							# Quick sanity check
							echo ""
							echo "[CLIENT] Cache state (should show HOST near-empty):"
							curl -sf "$BASE_URL/get_server_info" \
								| python3 -c "
						import sys, json
						try:
							d = json.load(sys.stdin)
							for k, v in sorted(d.items()):
								if any(x in k.lower() for x in ['cache','hicache','host','storage','mem','pool']):
									print(f'  {k}: {v}')
						except:
							pass
						" 2>/dev/null || true

							# ════════════════════════════════════════════════════════════════
							# PHASE 3 — FORCE STORAGE→HOST
							# Replay the same 128 conversations from Phase 1.
							# common_prefix=1024 → same hash → STORAGE hit, HOST miss
							#                    → SGLang must fetch from STORAGE → HOST
							# wait_complete policy means TTFT is dominated by the transfer.
							# Low concurrency = one transfer at a time = clean measurement.
							# ════════════════════════════════════════════════════════════════
							echo ""
							echo "════════════════════════════════════════════════════════════"
							echo " PHASE 3 — FORCE STORAGE→HOST (same conversations as Ph1)"
							echo "════════════════════════════════════════════════════════════"

							python3 benchmark_serving_multi_turn.py \
								--model "$MODEL" \
								--url "$BASE_URL" \
								--input-file /tmp/phase3_replay.json \
								--num-clients 2 \
								--max-active-conversations 8 \
								2>&1 | tee "$LOG_DIR/phase3_storage_to_host.log"

							# ════════════════════════════════════════════════════════════════
							# FINAL METRICS
							# ════════════════════════════════════════════════════════════════
							echo ""
							echo "════════════════════════════════════════════════════════════"
							echo " FINAL METRICS"
							echo "════════════════════════════════════════════════════════════"
							curl -sf "$BASE_URL/metrics" \
								| grep -iE "cache|hicache|storage|host|prefetch|hit|miss|transfer|load" \
								| tee "$LOG_DIR/final_metrics_multiturn.log" \
								|| echo "[CLIENT] /metrics not available"

							curl -sf "$BASE_URL/get_server_info" \
								| python3 -m json.tool \
								| tee "$LOG_DIR/final_server_info_multiturn.log" \
								|| true

							echo ""
							echo "[CLIENT] ══════════════════════════════════════════════════"
							echo "[CLIENT] Check TTFT difference between phases:"
							echo "  Phase 1 TTFT (HOST hit):      fast  (~50-100ms)"
							echo "  Phase 3 TTFT (STORAGE→HOST):  slow  (~500ms+)"
							echo ""
							echo "[CLIENT] Logs:"
							echo "  $LOG_DIR/phase1_warm_storage.log"
							echo "  $LOG_DIR/phase2_evict_host.log"
							echo "  $LOG_DIR/phase3_storage_to_host.log"
							echo "  $LOG_DIR/final_metrics_multiturn.log"
							'

					fi 
					if [ "$RUN_DOCKER_TEST" = "synthetic_prefix_repeat" ]; then
						echo "------------------- Invoking synthetic_prefix_repeat dataset for client (this dataset encourages s2h transfers)... -------------------"
						# --num-prompts 50000 \
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
							-v /data/ojaiyeob/vllm_cache:/models/hfcache \
							-v /home/central/ojaiyeob/vllm/vllm_client:/vllm-workspace/vllm_client \
							vllm/vllm-openai:latest \
							-lc '

								vllm bench serve \
									--backend openai \
									--model '"${LLM_MODELS[model]}"' \
									--base-url http://localhost:30000 \
									--dataset-name prefix_repetition \
									--num-prompts 500 \
									--prefix-repetition-prefix-len 6144 \
									--prefix-repetition-suffix-len 64 \
									--prefix-repetition-num-prefixes 48 \
									--prefix-repetition-output-len 32 \
									--request-rate 16 \
									--burstiness 0.3 \
									--max-concurrency 96
								  
							'
					fi 
					if [ "$RUN_DOCKER_TEST" = "synthetic_prefix_repeat_wflush" ]; then
						echo "------------------- Invoking synthetic_prefix_repeat_wflush dataset for client (this dataset encourages s2h transfers)... -------------------"
						# The key insight is that to force STORAGE→HOST transfers, you need to:
						# 1. **First warm the storage** with requests that populate the file cache
						# 2. **Then evict from HOST memory** by sending many *different* prefixes to fill up host KV cache
						# 3. **Then replay the original prefixes** — forcing SGLang to fetch from STORAGE→HOST

						export HF_TOKEN="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"
						export HF_SPLIT="train"
						export LIMIT="50"
						export MAX_TOKENS="128"
						export TEMPERATURE="0.2"
						export VLLM_MODEL=${LLM_MODELS[model]}
						export SGLANG_BASE_URL="http://localhost:30000"

						docker run --name docker-vllm-client \
							--entrypoint bash \
							--network host \
							-e HF_TOKEN="$HF_TOKEN" \
							-e HF_DATASETS_CACHE="/models/hfcache" \
							-e SGLANG_BASE_URL="$SGLANG_BASE_URL" \
							-v /data/ojaiyeob/vllm_cache:/models/hfcache \
							-v /home/central/ojaiyeob/vllm/vllm_client:/vllm-workspace/vllm_client \
							-v /home/central/ojaiyeob/GH200-studies:/workspace/GH200-studies \
							vllm/vllm-openai:latest \
							-lc '

								set -e
								BASE_URL="http://localhost:30000"
								MODEL='"${LLM_MODELS[model]}"'
								LOG_DIR="/workspace/GH200-studies"

								# ─────────────────────────────────────────────────────────────
								# HELPER: wait for server
								# ─────────────────────────────────────────────────────────────
								wait_for_server() {
									echo "[CLIENT] Waiting for SGLang server at $BASE_URL ..."
									for i in $(seq 1 60); do
										if curl -sf "$BASE_URL/health" > /dev/null 2>&1; then
											echo "[CLIENT] Server is ready."
											return 0
										fi
										sleep 5
									done
									echo "[CLIENT] ERROR: Server not ready after 5 minutes."
									exit 1
								}

								# ─────────────────────────────────────────────────────────────
								# HELPER: flush host KV cache via SGLang /flush_cache endpoint
								# ─────────────────────────────────────────────────────────────
								flush_host_cache() {
									echo "[CLIENT] Flushing HOST KV cache via /flush_cache ..."
									curl -sf -X POST "$BASE_URL/flush_cache" \
										-H "Content-Type: application/json" \
										&& echo "[CLIENT] /flush_cache OK" \
										|| echo "[CLIENT] WARNING: /flush_cache failed (endpoint may not exist)"
								}

								# ─────────────────────────────────────────────────────────────
								# PHASE 1 — WARM STORAGE
								# Send requests with fixed prefixes so they get written to
								# STORAGE (file backend). Use low concurrency + write-back
								# friendly settings. 48 unique prefixes × enough prompts.
								# ─────────────────────────────────────────────────────────────
								wait_for_server

								echo ""
								echo "════════════════════════════════════════════════════════"
								echo " PHASE 1 — WARM STORAGE (HOST → STORAGE write)"
								echo "════════════════════════════════════════════════════════"

								vllm bench serve \
									--backend openai \
									--model "$MODEL" \
									--base-url "$BASE_URL" \
									--dataset-name prefix_repetition \
									--num-prompts 480 \
									--prefix-repetition-prefix-len 6144 \
									--prefix-repetition-suffix-len 64 \
									--prefix-repetition-num-prefixes 48 \
									--prefix-repetition-output-len 32 \
									--request-rate 8 \
									--burstiness 1.0 \
									--max-concurrency 48 \
									2>&1 | tee "$LOG_DIR/phase1_warm_storage.log"

								echo "[CLIENT] Phase 1 complete. Sleeping 10s to allow async writes to flush..."
								sleep 10

								# ─────────────────────────────────────────────────────────────
								# PHASE 2 — EVICT HOST CACHE
								# Flood with DIFFERENT, never-seen prefixes so that the host
								# KV pool is completely displaced. The 48 original prefixes
								# should now only live in STORAGE (file backend).
								# Use a very large num-prefixes so each request is unique.
								# ─────────────────────────────────────────────────────────────
								echo ""
								echo "════════════════════════════════════════════════════════"
								echo " PHASE 2 — EVICT HOST CACHE (fill with new prefixes)"
								echo "════════════════════════════════════════════════════════"

								# First try the API flush (fastest, if available)
								flush_host_cache

								# Then also send eviction traffic with brand-new prefixes
								# 512 unique prefixes ensures the original 48 are evicted
								vllm bench serve \
									--backend openai \
									--model "$MODEL" \
									--base-url "$BASE_URL" \
									--dataset-name prefix_repetition \
									--num-prompts 512 \
									--prefix-repetition-prefix-len 6144 \
									--prefix-repetition-suffix-len 64 \
									--prefix-repetition-num-prefixes 512 \
									--prefix-repetition-output-len 8 \
									--request-rate 32 \
									--burstiness 2.0 \
									--max-concurrency 96 \
									2>&1 | tee "$LOG_DIR/phase2_evict_host.log"

								echo "[CLIENT] Phase 2 complete. Sleeping 5s ..."
								sleep 5

								# ─────────────────────────────────────────────────────────────
								# VERIFY: check cache state via /get_server_info or /metrics
								# ─────────────────────────────────────────────────────────────
								echo ""
								echo "[CLIENT] Cache state after eviction:"
								curl -sf "$BASE_URL/get_server_info" \
									| python3 -m json.tool 2>/dev/null \
									|| curl -sf "$BASE_URL/metrics" | grep -i "cache\|hicache\|host\|storage" \
									|| echo "[CLIENT] Could not query cache metrics endpoint."

								# ─────────────────────────────────────────────────────────────
								# PHASE 3 — FORCE STORAGE → HOST TRANSFERS
								# Replay the original 48 prefixes. They are no longer in HOST
								# memory, only in STORAGE. SGLang must prefetch them from the
								# file backend → HOST memory (STORAGE→HOST transfer).
								# ─────────────────────────────────────────────────────────────
								echo ""
								echo "════════════════════════════════════════════════════════"
								echo " PHASE 3 — FORCE STORAGE→HOST (replay original prefixes)"
								echo "════════════════════════════════════════════════════════"

								vllm bench serve \
									--backend openai \
									--model "$MODEL" \
									--base-url "$BASE_URL" \
									--dataset-name prefix_repetition \
									--num-prompts 500 \
									--prefix-repetition-prefix-len 6144 \
									--prefix-repetition-suffix-len 64 \
									--prefix-repetition-num-prefixes 48 \
									--prefix-repetition-output-len 32 \
									--request-rate 16 \
									--burstiness 0.3 \
									--max-concurrency 96 \
									2>&1 | tee "$LOG_DIR/phase3_storage_to_host.log"

								echo ""
								echo "[CLIENT] Phase 3 complete."

								# ─────────────────────────────────────────────────────────────
								# FINAL: dump metrics to confirm storage→host hit count
								# ─────────────────────────────────────────────────────────────
								echo ""
								echo "════════════════════════════════════════════════════════"
								echo " FINAL METRICS"
								echo "════════════════════════════════════════════════════════"
								curl -sf "$BASE_URL/metrics" \
									| grep -E "cache|hicache|storage|host|prefetch|hit|miss" \
									| tee "$LOG_DIR/final_metrics.log" \
									|| echo "[CLIENT] Could not retrieve metrics."

								curl -sf "$BASE_URL/get_server_info" \
									| python3 -m json.tool \
									| tee "$LOG_DIR/final_server_info.log" \
									|| true

								echo "[CLIENT] Done. Check $LOG_DIR/phase3_storage_to_host.log for TTFT/throughput."
								echo "[CLIENT] STORAGE→HOST hits should be visible in final_metrics.log"
							'

						# How This Forces STORAGE→HOST

						# ```
						# PHASE 1                    PHASE 2                    PHASE 3
						# ─────────────────────      ─────────────────────      ─────────────────────
						# 48 fixed prefixes     →    512 NEW prefixes       →    48 original prefixes
						# sent repeatedly            fill HOST KV pool          must come from STORAGE
												   
						# HOST:  [P1..P48 ✓]         HOST:  [Q1..Q512 ✓]        HOST:  [miss → fetch]
						# STOR:  [P1..P48 ✓]         STOR:  [P1..P48 ✓]         STOR:  [P1..P48 → HOST]
												   # (P1..P48 EVICTED from HOST)  ↑ STORAGE→HOST transfer
						# ```

						# ---

						# Key Parameters Explained

						# | Parameter | Phase 1 | Phase 2 | Phase 3 |
						# |---|---|---|---|
						# | `num-prefixes` | 48 | **512** (forces unique, evicts old) | 48 (same as P1) |
						# | `request-rate` | 8 (slow write) | 32 (fast evict) | 16 (measure) |
						# | `burstiness` | 1.0 | 2.0 | 0.3 (controlled) |
						# | Purpose | Write to STORAGE | Evict HOST | **Trigger STORAGE→HOST** |

						# > **Note:** If `--hicache-storage-prefetch-policy wait_complete` is set on the server, Phase 3 requests will **block** until the STORAGE→HOST prefetch completes, making the transfer effect directly measurable via TTFT latency.
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




