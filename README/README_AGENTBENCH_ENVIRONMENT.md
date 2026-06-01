# AgentBench Environment Setup

Use this runbook to prepare a fresh machine before running the NodeBB
SWE-bench task through AgentBench.

Goal: make the NodeBB workspace pass the selected local tests before asking the
agent to fix the task.

## 1. Harness Check

From the repo root:

```bash
cd ~/kv_cache_offloading

grep -n "collect_workspace_artifacts(run_dir, workspace_dir, auxiliary_dir=others_dir)" \
  agentbench/deepagents_swebench_single_host.py

grep -n "patch_path = report_dir / \"workspace.patch\"" \
  agentbench/deepagents_swebench_single_host.py
```

Both commands should print a line. New runs should write:

```text
experiments/raw/agentbench/results/<run_id>/workspace.patch
```

## 2. Node Shell

Run AgentBench from the same shell where Node is available:

```bash
cd ~/kv_cache_offloading

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm install 22
nvm use 22
export PATH="$(dirname "$(command -v node)"):$PATH"

node -v
npm -v
```

If a run shows `/bin/sh: line 1: node: command not found`, repeat this step and
rerun AgentBench from that same shell.

## 3. NodeBB Dependencies

The harness materializes the task checkout here:

```text
agentbench/repos/NodeBB__NodeBB
```

For this NodeBB checkout, the real app manifest is `install/package.json`; root
`package.json` only carries a few benchmark-specific ranges. Install both, with
root ranges applied last:

```bash
cd ~/kv_cache_offloading/agentbench/repos/NodeBB__NodeBB

unset NODE_ENV

NODEBB_INSTALL_DEPS="$(
node <<'NODE'
const fs = require('fs');
const install = JSON.parse(fs.readFileSync('install/package.json', 'utf8'));
const root = JSON.parse(fs.readFileSync('package.json', 'utf8'));
const deps = {
  ...(install.dependencies || {}),
  ...(install.devDependencies || {}),
  ...(root.dependencies || {}),
  ...(root.devDependencies || {}),
};
console.log(Object.entries(deps).map(([name, version]) => `${name}@${version}`).join(' '));
NODE
)"

npm install --no-save $NODEBB_INSTALL_DEPS
```

Verify the important packages:

```bash
node -e "console.log(require('chalk').yellow('chalk ok'))"
node -e "new (require('@isaacs/ttlcache'))({ ttl: 1000 }); console.log('ttlcache ok')"
node -e "if (typeof require('connect-redis').default !== 'function') throw new Error('connect-redis mismatch'); console.log('connect-redis ok')"
npm ls nconf winston
test -d node_modules/timeago/locales && echo "timeago locales ok"
test -f node_modules/nodebb-theme-persona/theme.json && echo "persona theme ok"
```

`npm audit` warnings are expected for this historical benchmark dependency set.
Do not run `npm audit fix`; it can change versions away from the task snapshot.

## 4. Redis And Config

Redis is the local test database for NodeBB.

```bash
cd ~/kv_cache_offloading/agentbench/repos/NodeBB__NodeBB

docker rm -f nodebb-test-redis >/dev/null 2>&1 || true
docker run -d \
  --name nodebb-test-redis \
  --network host \
  redis:7-alpine

docker ps --filter name=nodebb-test-redis
```

Create `config.json`:

```bash
cat > config.json <<'JSON'
{
  "url": "http://127.0.0.1:4567",
  "secret": "agentbench-test-secret",
  "database": "redis",
  "redis": {
    "host": "127.0.0.1",
    "port": "6379",
    "password": "",
    "database": "0"
  },
  "test_database": {
    "host": "127.0.0.1",
    "port": "6379",
    "password": "",
    "database": "1"
  }
}
JSON

test -f config.json && echo "config.json exists"
```

## 5. Local Preflight

Build the templates used by the email tests:

```bash
cd ~/kv_cache_offloading/agentbench/repos/NodeBB__NodeBB

./nodebb build tpl --series
test -f build/public/templates/emails/verify-email.js && echo "email template ok"
```

For this preflight, webpack errors about missing `build/public/src/client.js` or
`build/public/src/admin/admin.js` are not blocking as long as
`email template ok` prints. These tests only need compiled templates.

Run the selected tests:

```bash
npx mocha --timeout 30000 test/database.js test/database/keys.js test/user/emails.js
```

Expected success signal:

```text
298 passing
```

Do not rerun AgentBench until this preflight passes. The `sendmail-not-found`
log can appear during the test run and still pass.

## 6. Rerun AgentBench

Return to the repo root and rerun baseline from the same Node-enabled shell:

```bash
cd ~/kv_cache_offloading

AGENTBENCH_WORKFLOW_MODE=baseline \
python3.11 agentbench/deepagents_swebench_single_host.py \
  --app-variant upstream_deploy_coding_agent \
  --frontend-url http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions \
  --model "$MODEL_NAME" \
  --dataset ScaleAI/SWE-bench_Pro \
  --split test \
  --index 0 \
  --prompt-evolution-value-char-limit 1000
```

Check the latest result:

```bash
LATEST_RESULT="$(ls -td experiments/raw/agentbench/results/* | head -1)"
echo "$LATEST_RESULT"

wc -c "$LATEST_RESULT/workspace.patch"
cat "$LATEST_RESULT/others/git_status.txt"
cat "$LATEST_RESULT/others/git_diff_stat.txt"
```

Useful signal:

```text
workspace.patch size > 0
git_status.txt or git_diff_stat.txt is non-empty
```
