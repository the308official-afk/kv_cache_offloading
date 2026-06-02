# Comparison Report: smoke_latest3

- Runs: `3`

## Runs

| Run | Profile | Patch | D2H KV MB | H2D KV MB | Avg TTFT ms | Avg Reuse |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| agentbench-nodebb_20260601_200503 | baseline | False | 1151.500 | 0.000 | 3348.569 | 0.6608 |
| agentbench-nodebb_20260601_192108 | baseline | False | 1151.500 | 0.000 | 3403.166 | 0.6608 |
| agentbench-nodebb_20260601_184042 | baseline | False | 1151.500 | 0.000 | 3362.916 | 0.6608 |

## Profile/Phase Averages

| Profile | Phase | Runs | TTFT ms | SGLang TTFT ms | Reuse | Cached Tokens | H2D Seen |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| baseline | execution | 3 | 1601.377 | 1001.193 | 0.7768 | 8512.0 | False |
| baseline | patch_generation | 3 | 993.455 | 670.151 | 0.9332 | 11072.0 | False |
| baseline | planning | 3 | 9295.376 | 4647.190 | 0.0000 | 0.0 | False |
| baseline | review | 3 | 1595.995 | 943.438 | 0.9330 | 11072.0 | False |
