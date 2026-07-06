cd ~/kv_cache_offloading
source runtime_instrumentation/cache_pinning_profile.sh
docker rmi "$CACHE_PINNING_FRONTEND_IMAGE" "$CACHE_PINNING_WORKER_IMAGE" 2>/dev/null || true
