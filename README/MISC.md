

```bash
cd ~/kv_cache_offloading

ls -lah experiments/charts/exp6_prompt_evolution_run_overview.svg
grep -n "plot_prompt_evolution_overview" agentbench/run_prompt_evolution_batch_single_host.sh
ls -lah experiments/reports/prompt_evolution_run_overview.csv

```


```bash
cd ~/kv_cache_offloading

mkdir -p experiments/charts

python3 experiments/scripts/prompt_evolution/plot_prompt_evolution_overview.py \
  --overview-csv experiments/reports/prompt_evolution_run_overview.csv \
  --out-svg experiments/charts/exp6_prompt_evolution_run_overview.svg

ls -lah experiments/charts/exp6_prompt_evolution_run_overview.svg
```


```bash
ojaiyeob@gracehopper:~/kv_cache_offloading$ cd ~/kv_cache_offloading

ls -lah experiments/charts/exp6_prompt_evolution_run_overview.svg
grep -n "plot_prompt_evolution_overview" agentbench/run_prompt_evolution_batch_single_host.sh
ls -lah experiments/reports/prompt_evolution_run_overview.csv
ls: cannot access 'experiments/charts/exp6_prompt_evolution_run_overview.svg': No such file or directory
-rw-rw-r-- 1 ojaiyeob ojaiyeob 1.5K Jul 14 17:06 experiments/reports/prompt_evolution_run_overview.csv
ojaiyeob@gracehopper:~/kv_cache_offloading$ cat experiments/reports/prompt_evolution_run_overview.csv
Run,Repo,Model,Steps,Planning,Execution,Exec Size Δ,Patch Gen,Review,Other,Total,Patch
113646,NodeBB,Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8,3,0 - none,0 - none,-5905,0 - none,0 - none,0 - none,0,0 B
113723,qutebrowser,Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8,3,0 - none,0 - none,-2164,0 - none,0 - none,0 - none,0,0 B
113736,NodeBB,Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8,3,0 - none,0 - none,-4644,0 - none,0 - none,0 - none,0,0 B
113750,qutebrowser,Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8,3,0 - none,0 - none,-2789,0 - none,0 - none,0 - none,0,0 B
113759,ansible,Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8,3,0 - none,0 - none,-969,0 - none,0 - none,0 - none,0,0 B
113840,ansible,Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8,3,0 - none,0 - none,-2974,0 - none,0 - none,0 - none,0,0 B
120532,NodeBB,Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8,3,0 - none,0 - none,-5905,0 - none,0 - none,0 - none,0,0 B
120546,qutebrowser,Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8,3,0 - none,0 - none,-2164,0 - none,0 - none,0 - none,0,0 B
120555,NodeBB,Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8,3,0 - none,0 - none,-4644,0 - none,0 - none,0 - none,0,0 B
120609,qutebrowser,Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8,3,0 - none,0 - none,-2789,0 - none,0 - none,0 - none,0,0 B
120618,ansible,Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8,3,0 - none,0 - none,-969,0 - none,0 - none,0 - none,0,0 B
120634,ansible,Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8,3,0 - none,0 - none,-2974,0 - none,0 - none,0 - none,0,0 B
ojaiyeob@gracehopper:~/kv_cache_offloading$

```
