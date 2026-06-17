window.RETENTION_STORY_DATA = {
  "generated_at": "2026-06-17T12:23:43",
  "report_path": "/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/reports/retention_threshold_matrix.csv",
  "model": "Qwen/Qwen2.5-Coder-7B-Instruct",
  "kv_tier_mode": "gpu_only",
  "control_profile": "none",
  "protected_profile": "high-priority",
  "profiles": {
    "none": {
      "label": "None",
      "is_control": true,
      "distractor_counts": [
        2,
        10,
        20,
        40,
        60,
        80,
        100,
        200
      ],
      "a_first_latency_ms": [
        131.0,
        134.0,
        131.0,
        131.0,
        131.0,
        132.0,
        131.0,
        131.0
      ],
      "a_replay_latency_ms": [
        72.0,
        72.0,
        72.0,
        72.0,
        72.0,
        147.0,
        147.0,
        147.0
      ],
      "a_first_prompt_tokens": [
        267.0,
        267.0,
        267.0,
        267.0,
        267.0,
        267.0,
        267.0,
        267.0
      ],
      "a_replay_cached_tokens": [
        256.0,
        256.0,
        256.0,
        256.0,
        256.0,
        null,
        null,
        null
      ],
      "thresholds": {
        "last_survived_distractor_count": 60,
        "first_evicted_distractor_count": 80
      }
    },
    "high-priority": {
      "label": "High Priority",
      "is_control": false,
      "distractor_counts": [
        2,
        10,
        20,
        40,
        60,
        80,
        100,
        200
      ],
      "a_first_latency_ms": [
        132.0,
        131.0,
        131.0,
        132.0,
        131.0,
        132.0,
        131.0,
        131.0
      ],
      "a_replay_latency_ms": [
        72.0,
        72.0,
        72.0,
        72.0,
        71.0,
        72.0,
        72.0,
        72.0
      ],
      "a_first_prompt_tokens": [
        267.0,
        267.0,
        267.0,
        267.0,
        267.0,
        267.0,
        267.0,
        267.0
      ],
      "a_replay_cached_tokens": [
        256.0,
        256.0,
        256.0,
        256.0,
        256.0,
        256.0,
        256.0,
        256.0
      ],
      "thresholds": {
        "last_survived_distractor_count": 200,
        "first_evicted_distractor_count": null
      }
    }
  },
  "capacity": {
    "worker_kv_capacity_tokens": 17152,
    "worker_context_len": 32768,
    "a_prompt_tokens": 267,
    "distractor_prompt_tokens": 272,
    "max_distractor_count_tested": 200
  },
  "attribution": {
    "worker_hint_status": "full",
    "worker_hint_profile_seen": "high-priority",
    "worker_priority_mechanism_ready": true,
    "worker_priority_scheduling_enabled": true,
    "worker_radix_eviction_policy": "priority",
    "request_top_level_priority_status": "none",
    "worker_top_level_priority_status": "none",
    "request_agent_hints_priority_status": "full",
    "hint_runtime_effect_first_observed_at": 80
  }
};
