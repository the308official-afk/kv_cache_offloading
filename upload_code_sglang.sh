#!/bin/bash

# HOME=/home/ojaiyeob
HOME=/home/central/ojaiyeob  

scp -J ojaiyeob@falcon.7elements.com:1337 ./run_docker_sglang.sh ojaiyeob@gracehopper:$HOME/sglang/run_docker_sglang.sh
# scp -J ojaiyeob@falcon.7elements.com:1337 ./modified_files/bench_serving.py ojaiyeob@gracehopper:$HOME/sglang/python/sglang/bench_serving.py
scp -J ojaiyeob@falcon.7elements.com:1337 ./modified_files/memory_pool_host.py ojaiyeob@gracehopper:$HOME/sglang/python/sglang/srt/mem_cache/memory_pool_host.py
scp -J ojaiyeob@falcon.7elements.com:1337 ./modified_files/hiradix_cache.py ojaiyeob@gracehopper:$HOME/sglang/python/sglang/srt/mem_cache/hiradix_cache.py
scp -J ojaiyeob@falcon.7elements.com:1337 ./modified_files/cache_controller.py ojaiyeob@gracehopper:$HOME/sglang/python/sglang/srt/managers/cache_controller.py
scp -J ojaiyeob@falcon.7elements.com:1337 ./modified_files/hicache_storage.py ojaiyeob@gracehopper:$HOME/sglang/python/sglang/srt/mem_cache/hicache_storage.py

