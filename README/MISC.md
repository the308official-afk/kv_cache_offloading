

```bash
turn_a_ms	turn_b_ms
571	291
451	337

```


```bash
# Speculative Prefill Probe: speculative_prefill_microbenchmark_20260710_163720__probe

- Model: `Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8`
- Attribution mode: `precise`
- Turn A words: `4000`
- Turn B words: `512`
- Output tokens: `64`
- Warmup wait ms: `500`

## Result

- Control turn B latency ms: `291`
- Protected turn B latency ms: `337`
- Turn B latency delta ms (control - protected): `-46`
- Control turn B cached tokens: `8128`
- Protected turn B cached tokens: `8128`
- Turn B cached-token delta (protected - control): `0`
- Protected prefill evidence status: `direct_prefill_seen`
- Protected prefill completed: `True`
- Protected target seen in prefill events: `True`
- Protected anonymous warmup seen: `True`
- Overall effect verdict: `direct_no_visible_gain`

```
