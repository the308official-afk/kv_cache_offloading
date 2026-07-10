Experiment Contracts
====================

This folder holds experiment contract files.

A contract is split into two files:

- machine-readable shell contract:
  - `*.contract.sh`
- human-readable contract doc:
  - `*.contract.md`
- worked success examples:
  - `examples/*.md`

Together, they define the agreement for a benchmark or experiment:

- exact upstream repos, pull refs, and pinned commits
- machine/runtime prerequisites
- required flags and environment variables
- expected proof signals
- expected reports
- known failure signatures

Purpose
-------

Contracts make experiments reproducible.

If someone else wants to rerun an experiment, they should be able to start from
the contract file instead of reconstructing hidden assumptions from shell
history or chat logs.

Rules
-----

1. One shell contract and one doc contract per experiment or microbenchmark.
2. The shell contract is the real source of truth for default variables.
3. The doc contract explains the same experiment in plain language.
4. Worked examples should show a real success pattern and the exact columns to
   trust first.
5. Prefer exact paths, exact refs, exact flags, and exact success criteria.
6. When the experiment changes in a meaningful way, update both files.
7. If the success pattern changes, update the worked example too.
8. If an experiment has a public wrapper, the wrapper should print the contract
   paths near the start of the run.

Current contracts
-----------------

- `cache_pinning_microbenchmark.contract.sh`
- `cache_pinning_microbenchmark.contract.md`
- `kv_retention_microbenchmark.contract.sh`
- `kv_retention_microbenchmark.contract.md`
- `priority_scheduling_microbenchmark.contract.sh`
- `priority_scheduling_microbenchmark.contract.md`
- `speculative_prefill_microbenchmark.contract.sh`
- `speculative_prefill_microbenchmark.contract.md`

Worked examples
---------------

- `examples/exp9_kv_retention_success.md`
- `examples/exp10_cache_pinning_success.md`
- `examples/exp11_priority_scheduling_success.md`
- `examples/exp12_speculative_prefill_success.md`
