
```bash
ojaiyeob@gracehopper:~/kv_cache_offloading$ cd ~/kv_cache_offloading

./agentbench/debug_prompt_evolution_tool_calls.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8

========================================
PROMPT EVOLUTION TOOL-CALL DEBUG
========================================
Model: Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
Frontend URL: http://127.0.0.1:8000/v1/chat/completions
Python: python3.11
Deep Agents source: upstream
Output dir: experiments/reports/tool_call_debug/tool_call_debug_20260714_194439

This script does not start Dynamo.
Run it while the same Dynamo runtime from Experiment 6 is still up.

========================================
STEP -1: ENSURE DEEP AGENTS IS READY
========================================
Checking Deep Agents dependency...
Deep Agents dir: upstream/deepagents
Deep Agents ref: 2cf7e25dbb40e783d9d4d545c29e595800bf314f
Auto install: 1
Deep Agents git checkout exists; refreshing refs...
remote: Enumerating objects: 8, done.
remote: Counting objects: 100% (8/8), done.
remote: Compressing objects: 100% (8/8), done.
remote: Total 8 (delta 0), reused 0 (delta 0), pack-reused 0 (from 0)
Unpacking objects: 100% (8/8), 199.04 KiB | 4.06 MiB/s, done.
From https://github.com/langchain-ai/deepagents
   1aa4d465..5668bd5f  mdrxy/code/inline-ctrl-d -> origin/mdrxy/code/inline-ctrl-d
HEAD is now at 2cf7e25d fix(evals,ci): cap dependency versions and reorder Fireworks models (#3202)
Installing Deep Agents package...
Defaulting to user installation because normal site-packages is not writeable
Processing ./upstream/deepagents/libs/deepagents
  Installing build dependencies ... done
  Getting requirements to build wheel ... done
  Preparing metadata (pyproject.toml) ... done
Requirement already satisfied: langchain-core<2.0.0,>=1.3.2 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from deepagents==0.5.7) (1.4.0)
Requirement already satisfied: langsmith>=0.8.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from deepagents==0.5.7) (0.8.5)
Requirement already satisfied: langchain<2.0.0,>=1.2.17 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from deepagents==0.5.7) (1.3.1)
Requirement already satisfied: langchain-anthropic<2.0.0,>=1.4.3 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from deepagents==0.5.7) (1.4.3)
Requirement already satisfied: langchain-google-genai<5.0.0,>=4.2.2 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from deepagents==0.5.7) (4.2.2)
Requirement already satisfied: wcmatch in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from deepagents==0.5.7) (10.1)
Requirement already satisfied: langgraph<1.3.0,>=1.2.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain<2.0.0,>=1.2.17->deepagents==0.5.7) (1.2.0)
Requirement already satisfied: pydantic<3.0.0,>=2.7.4 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain<2.0.0,>=1.2.17->deepagents==0.5.7) (2.13.4)
Requirement already satisfied: anthropic<1.0.0,>=0.96.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7) (0.103.1)
Requirement already satisfied: anyio<5,>=3.5.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from anthropic<1.0.0,>=0.96.0->langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7) (4.13.0)
Requirement already satisfied: distro<2,>=1.7.0 in /usr/lib/python3/dist-packages (from anthropic<1.0.0,>=0.96.0->langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7) (1.7.0)
Requirement already satisfied: docstring-parser<1,>=0.15 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from anthropic<1.0.0,>=0.96.0->langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7) (0.18.0)
Requirement already satisfied: httpx<1,>=0.25.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from anthropic<1.0.0,>=0.96.0->langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7) (0.28.1)
Requirement already satisfied: jiter<1,>=0.4.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from anthropic<1.0.0,>=0.96.0->langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7) (0.15.0)
Requirement already satisfied: sniffio in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from anthropic<1.0.0,>=0.96.0->langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7) (1.3.1)
Requirement already satisfied: typing-extensions<5,>=4.14 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from anthropic<1.0.0,>=0.96.0->langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7) (4.15.0)
Requirement already satisfied: idna>=2.8 in /usr/lib/python3/dist-packages (from anyio<5,>=3.5.0->anthropic<1.0.0,>=0.96.0->langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7) (3.3)
Requirement already satisfied: certifi in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from httpx<1,>=0.25.0->anthropic<1.0.0,>=0.96.0->langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7) (2026.5.20)
Requirement already satisfied: httpcore==1.* in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from httpx<1,>=0.25.0->anthropic<1.0.0,>=0.96.0->langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7) (1.0.9)
Requirement already satisfied: h11>=0.16 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from httpcore==1.*->httpx<1,>=0.25.0->anthropic<1.0.0,>=0.96.0->langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7) (0.16.0)
Requirement already satisfied: jsonpatch<2.0.0,>=1.33.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain-core<2.0.0,>=1.3.2->deepagents==0.5.7) (1.33)
Requirement already satisfied: langchain-protocol>=0.0.14 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain-core<2.0.0,>=1.3.2->deepagents==0.5.7) (0.0.15)
Requirement already satisfied: packaging>=23.2.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain-core<2.0.0,>=1.3.2->deepagents==0.5.7) (26.2)
Requirement already satisfied: pyyaml<7.0.0,>=5.3.0 in /usr/lib/python3/dist-packages (from langchain-core<2.0.0,>=1.3.2->deepagents==0.5.7) (5.4.1)
Requirement already satisfied: tenacity!=8.4.0,<10.0.0,>=8.1.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain-core<2.0.0,>=1.3.2->deepagents==0.5.7) (9.1.4)
Requirement already satisfied: uuid-utils<1.0,>=0.12.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain-core<2.0.0,>=1.3.2->deepagents==0.5.7) (0.16.0)
Requirement already satisfied: jsonpointer>=1.9 in /usr/lib/python3/dist-packages (from jsonpatch<2.0.0,>=1.33.0->langchain-core<2.0.0,>=1.3.2->deepagents==0.5.7) (2.0)
Requirement already satisfied: filetype<2.0.0,>=1.2.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7) (1.2.0)
Requirement already satisfied: google-genai<2.0.0,>=1.65.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7) (1.75.0)
Requirement already satisfied: google-auth<3.0.0,>=2.48.1 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from google-auth[requests]<3.0.0,>=2.48.1->google-genai<2.0.0,>=1.65.0->langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7) (2.53.0)
Requirement already satisfied: requests<3.0.0,>=2.28.1 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from google-genai<2.0.0,>=1.65.0->langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7) (2.34.2)
Requirement already satisfied: websockets<17.0,>=13.0.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from google-genai<2.0.0,>=1.65.0->langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7) (16.0)
Requirement already satisfied: pyasn1-modules>=0.2.1 in /usr/lib/python3/dist-packages (from google-auth<3.0.0,>=2.48.1->google-auth[requests]<3.0.0,>=2.48.1->google-genai<2.0.0,>=1.65.0->langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7) (0.2.1)
Requirement already satisfied: cryptography>=38.0.3 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from google-auth<3.0.0,>=2.48.1->google-auth[requests]<3.0.0,>=2.48.1->google-genai<2.0.0,>=1.65.0->langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7) (48.0.0)
Requirement already satisfied: langgraph-checkpoint<5.0.0,>=4.1.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langgraph<1.3.0,>=1.2.0->langchain<2.0.0,>=1.2.17->deepagents==0.5.7) (4.1.0)
Requirement already satisfied: langgraph-prebuilt<1.2.0,>=1.1.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langgraph<1.3.0,>=1.2.0->langchain<2.0.0,>=1.2.17->deepagents==0.5.7) (1.1.0)
Requirement already satisfied: langgraph-sdk<0.4.0,>=0.3.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langgraph<1.3.0,>=1.2.0->langchain<2.0.0,>=1.2.17->deepagents==0.5.7) (0.3.14)
Requirement already satisfied: xxhash>=3.5.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langgraph<1.3.0,>=1.2.0->langchain<2.0.0,>=1.2.17->deepagents==0.5.7) (3.7.0)
Requirement already satisfied: ormsgpack>=1.12.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langgraph-checkpoint<5.0.0,>=4.1.0->langgraph<1.3.0,>=1.2.0->langchain<2.0.0,>=1.2.17->deepagents==0.5.7) (1.12.2)
Requirement already satisfied: orjson>=3.11.5 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langgraph-sdk<0.4.0,>=0.3.0->langgraph<1.3.0,>=1.2.0->langchain<2.0.0,>=1.2.17->deepagents==0.5.7) (3.11.9)
Requirement already satisfied: requests-toolbelt>=1.0.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langsmith>=0.8.0->deepagents==0.5.7) (1.0.0)
Requirement already satisfied: zstandard>=0.23.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langsmith>=0.8.0->deepagents==0.5.7) (0.25.0)
Requirement already satisfied: annotated-types>=0.6.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from pydantic<3.0.0,>=2.7.4->langchain<2.0.0,>=1.2.17->deepagents==0.5.7) (0.7.0)
Requirement already satisfied: pydantic-core==2.46.4 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from pydantic<3.0.0,>=2.7.4->langchain<2.0.0,>=1.2.17->deepagents==0.5.7) (2.46.4)
Requirement already satisfied: typing-inspection>=0.4.2 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from pydantic<3.0.0,>=2.7.4->langchain<2.0.0,>=1.2.17->deepagents==0.5.7) (0.4.2)
Requirement already satisfied: charset_normalizer<4,>=2 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from requests<3.0.0,>=2.28.1->google-genai<2.0.0,>=1.65.0->langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7) (3.4.7)
Requirement already satisfied: urllib3<3,>=1.26 in /usr/lib/python3/dist-packages (from requests<3.0.0,>=2.28.1->google-genai<2.0.0,>=1.65.0->langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7) (1.26.5)
Requirement already satisfied: cffi>=2.0.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from cryptography>=38.0.3->google-auth<3.0.0,>=2.48.1->google-auth[requests]<3.0.0,>=2.48.1->google-genai<2.0.0,>=1.65.0->langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7) (2.0.0)
Requirement already satisfied: pycparser in /usr/lib/python3/dist-packages (from cffi>=2.0.0->cryptography>=38.0.3->google-auth<3.0.0,>=2.48.1->google-auth[requests]<3.0.0,>=2.48.1->google-genai<2.0.0,>=1.65.0->langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7) (2.21)
Requirement already satisfied: bracex>=2.1.1 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from wcmatch->deepagents==0.5.7) (2.6)
Building wheels for collected packages: deepagents
  Building wheel for deepagents (pyproject.toml) ... done
  Created wheel for deepagents: filename=deepagents-0.5.7-py3-none-any.whl size=187644 sha256=bfa52a5e66915369002aace0b79d3e55d42ac20201827420055f1b5efa6ea71b
  Stored in directory: /tmp/pip-ephem-wheel-cache-ql1xnaix/wheels/67/d1/66/6c1b78f1a5c339c94a4a36f1d66cce2b6276edc45e6382ef80
Successfully built deepagents
Installing collected packages: deepagents
  Attempting uninstall: deepagents
    Found existing installation: deepagents 0.5.7
    Uninstalling deepagents-0.5.7:
      Successfully uninstalled deepagents-0.5.7
Successfully installed deepagents-0.5.7
Installing AgentBench Python requirements...
Defaulting to user installation because normal site-packages is not writeable
Processing ./upstream/deepagents/libs/deepagents
  Installing build dependencies ... done
  Getting requirements to build wheel ... done
  Preparing metadata (pyproject.toml) ... done
Requirement already satisfied: langchain-openai in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from -r agentbench/requirements.txt (line 2)) (1.2.1)
Requirement already satisfied: langchain-core in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from -r agentbench/requirements.txt (line 3)) (1.4.0)
Requirement already satisfied: datasets in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from -r agentbench/requirements.txt (line 4)) (4.8.5)
Requirement already satisfied: pandas in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from -r agentbench/requirements.txt (line 5)) (3.0.3)
Requirement already satisfied: openpyxl in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from -r agentbench/requirements.txt (line 6)) (3.1.5)
Requirement already satisfied: langsmith>=0.8.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (0.8.5)
Requirement already satisfied: langchain<2.0.0,>=1.2.17 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (1.3.1)
Requirement already satisfied: langchain-anthropic<2.0.0,>=1.4.3 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (1.4.3)
Requirement already satisfied: langchain-google-genai<5.0.0,>=4.2.2 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (4.2.2)
Requirement already satisfied: wcmatch in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (10.1)
Requirement already satisfied: jsonpatch<2.0.0,>=1.33.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain-core->-r agentbench/requirements.txt (line 3)) (1.33)
Requirement already satisfied: langchain-protocol>=0.0.14 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain-core->-r agentbench/requirements.txt (line 3)) (0.0.15)
Requirement already satisfied: packaging>=23.2.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain-core->-r agentbench/requirements.txt (line 3)) (26.2)
Requirement already satisfied: pydantic<3.0.0,>=2.7.4 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain-core->-r agentbench/requirements.txt (line 3)) (2.13.4)
Requirement already satisfied: pyyaml<7.0.0,>=5.3.0 in /usr/lib/python3/dist-packages (from langchain-core->-r agentbench/requirements.txt (line 3)) (5.4.1)
Requirement already satisfied: tenacity!=8.4.0,<10.0.0,>=8.1.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain-core->-r agentbench/requirements.txt (line 3)) (9.1.4)
Requirement already satisfied: typing-extensions<5.0.0,>=4.7.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain-core->-r agentbench/requirements.txt (line 3)) (4.15.0)
Requirement already satisfied: uuid-utils<1.0,>=0.12.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain-core->-r agentbench/requirements.txt (line 3)) (0.16.0)
Requirement already satisfied: jsonpointer>=1.9 in /usr/lib/python3/dist-packages (from jsonpatch<2.0.0,>=1.33.0->langchain-core->-r agentbench/requirements.txt (line 3)) (2.0)
Requirement already satisfied: langgraph<1.3.0,>=1.2.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain<2.0.0,>=1.2.17->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (1.2.0)
Requirement already satisfied: anthropic<1.0.0,>=0.96.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (0.103.1)
Requirement already satisfied: anyio<5,>=3.5.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from anthropic<1.0.0,>=0.96.0->langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (4.13.0)
Requirement already satisfied: distro<2,>=1.7.0 in /usr/lib/python3/dist-packages (from anthropic<1.0.0,>=0.96.0->langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (1.7.0)
Requirement already satisfied: docstring-parser<1,>=0.15 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from anthropic<1.0.0,>=0.96.0->langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (0.18.0)
Requirement already satisfied: httpx<1,>=0.25.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from anthropic<1.0.0,>=0.96.0->langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (0.28.1)
Requirement already satisfied: jiter<1,>=0.4.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from anthropic<1.0.0,>=0.96.0->langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (0.15.0)
Requirement already satisfied: sniffio in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from anthropic<1.0.0,>=0.96.0->langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (1.3.1)
Requirement already satisfied: idna>=2.8 in /usr/lib/python3/dist-packages (from anyio<5,>=3.5.0->anthropic<1.0.0,>=0.96.0->langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (3.3)
Requirement already satisfied: certifi in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from httpx<1,>=0.25.0->anthropic<1.0.0,>=0.96.0->langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (2026.5.20)
Requirement already satisfied: httpcore==1.* in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from httpx<1,>=0.25.0->anthropic<1.0.0,>=0.96.0->langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (1.0.9)
Requirement already satisfied: h11>=0.16 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from httpcore==1.*->httpx<1,>=0.25.0->anthropic<1.0.0,>=0.96.0->langchain-anthropic<2.0.0,>=1.4.3->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (0.16.0)
Requirement already satisfied: filetype<2.0.0,>=1.2.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (1.2.0)
Requirement already satisfied: google-genai<2.0.0,>=1.65.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (1.75.0)
Requirement already satisfied: google-auth<3.0.0,>=2.48.1 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from google-auth[requests]<3.0.0,>=2.48.1->google-genai<2.0.0,>=1.65.0->langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (2.53.0)
Requirement already satisfied: requests<3.0.0,>=2.28.1 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from google-genai<2.0.0,>=1.65.0->langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (2.34.2)
Requirement already satisfied: websockets<17.0,>=13.0.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from google-genai<2.0.0,>=1.65.0->langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (16.0)
Requirement already satisfied: pyasn1-modules>=0.2.1 in /usr/lib/python3/dist-packages (from google-auth<3.0.0,>=2.48.1->google-auth[requests]<3.0.0,>=2.48.1->google-genai<2.0.0,>=1.65.0->langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (0.2.1)
Requirement already satisfied: cryptography>=38.0.3 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from google-auth<3.0.0,>=2.48.1->google-auth[requests]<3.0.0,>=2.48.1->google-genai<2.0.0,>=1.65.0->langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (48.0.0)
Requirement already satisfied: langgraph-checkpoint<5.0.0,>=4.1.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langgraph<1.3.0,>=1.2.0->langchain<2.0.0,>=1.2.17->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (4.1.0)
Requirement already satisfied: langgraph-prebuilt<1.2.0,>=1.1.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langgraph<1.3.0,>=1.2.0->langchain<2.0.0,>=1.2.17->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (1.1.0)
Requirement already satisfied: langgraph-sdk<0.4.0,>=0.3.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langgraph<1.3.0,>=1.2.0->langchain<2.0.0,>=1.2.17->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (0.3.14)
Requirement already satisfied: xxhash>=3.5.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langgraph<1.3.0,>=1.2.0->langchain<2.0.0,>=1.2.17->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (3.7.0)
Requirement already satisfied: ormsgpack>=1.12.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langgraph-checkpoint<5.0.0,>=4.1.0->langgraph<1.3.0,>=1.2.0->langchain<2.0.0,>=1.2.17->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (1.12.2)
Requirement already satisfied: orjson>=3.11.5 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langgraph-sdk<0.4.0,>=0.3.0->langgraph<1.3.0,>=1.2.0->langchain<2.0.0,>=1.2.17->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (3.11.9)
Requirement already satisfied: requests-toolbelt>=1.0.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langsmith>=0.8.0->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (1.0.0)
Requirement already satisfied: zstandard>=0.23.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langsmith>=0.8.0->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (0.25.0)
Requirement already satisfied: annotated-types>=0.6.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from pydantic<3.0.0,>=2.7.4->langchain-core->-r agentbench/requirements.txt (line 3)) (0.7.0)
Requirement already satisfied: pydantic-core==2.46.4 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from pydantic<3.0.0,>=2.7.4->langchain-core->-r agentbench/requirements.txt (line 3)) (2.46.4)
Requirement already satisfied: typing-inspection>=0.4.2 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from pydantic<3.0.0,>=2.7.4->langchain-core->-r agentbench/requirements.txt (line 3)) (0.4.2)
Requirement already satisfied: charset_normalizer<4,>=2 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from requests<3.0.0,>=2.28.1->google-genai<2.0.0,>=1.65.0->langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (3.4.7)
Requirement already satisfied: urllib3<3,>=1.26 in /usr/lib/python3/dist-packages (from requests<3.0.0,>=2.28.1->google-genai<2.0.0,>=1.65.0->langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (1.26.5)
Requirement already satisfied: openai<3.0.0,>=2.26.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain-openai->-r agentbench/requirements.txt (line 2)) (2.37.0)
Requirement already satisfied: tiktoken<1.0.0,>=0.7.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from langchain-openai->-r agentbench/requirements.txt (line 2)) (0.13.0)
Requirement already satisfied: tqdm>4 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from openai<3.0.0,>=2.26.0->langchain-openai->-r agentbench/requirements.txt (line 2)) (4.67.3)
Requirement already satisfied: regex in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from tiktoken<1.0.0,>=0.7.0->langchain-openai->-r agentbench/requirements.txt (line 2)) (2026.5.9)
Requirement already satisfied: filelock in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from datasets->-r agentbench/requirements.txt (line 4)) (3.29.0)
Requirement already satisfied: numpy>=1.17 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from datasets->-r agentbench/requirements.txt (line 4)) (2.4.6)
Requirement already satisfied: pyarrow>=21.0.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from datasets->-r agentbench/requirements.txt (line 4)) (24.0.0)
Requirement already satisfied: dill<0.4.2,>=0.3.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from datasets->-r agentbench/requirements.txt (line 4)) (0.4.1)
Requirement already satisfied: multiprocess<0.70.20 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from datasets->-r agentbench/requirements.txt (line 4)) (0.70.19)
Requirement already satisfied: fsspec<=2026.2.0,>=2023.1.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from fsspec[http]<=2026.2.0,>=2023.1.0->datasets->-r agentbench/requirements.txt (line 4)) (2026.2.0)
Requirement already satisfied: huggingface-hub<2.0,>=0.25.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from datasets->-r agentbench/requirements.txt (line 4)) (1.16.0)
Requirement already satisfied: aiohttp!=4.0.0a0,!=4.0.0a1 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from fsspec[http]<=2026.2.0,>=2023.1.0->datasets->-r agentbench/requirements.txt (line 4)) (3.13.5)
Requirement already satisfied: hf-xet<2.0.0,>=1.4.3 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from huggingface-hub<2.0,>=0.25.0->datasets->-r agentbench/requirements.txt (line 4)) (1.5.0)
Requirement already satisfied: typer>=0.20.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from huggingface-hub<2.0,>=0.25.0->datasets->-r agentbench/requirements.txt (line 4)) (0.25.1)
Requirement already satisfied: python-dateutil>=2.8.2 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from pandas->-r agentbench/requirements.txt (line 5)) (2.9.0.post0)
Requirement already satisfied: et-xmlfile in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from openpyxl->-r agentbench/requirements.txt (line 6)) (2.0.0)
Requirement already satisfied: aiohappyeyeballs>=2.5.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from aiohttp!=4.0.0a0,!=4.0.0a1->fsspec[http]<=2026.2.0,>=2023.1.0->datasets->-r agentbench/requirements.txt (line 4)) (2.6.2)
Requirement already satisfied: aiosignal>=1.4.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from aiohttp!=4.0.0a0,!=4.0.0a1->fsspec[http]<=2026.2.0,>=2023.1.0->datasets->-r agentbench/requirements.txt (line 4)) (1.4.0)
Requirement already satisfied: attrs>=17.3.0 in /usr/lib/python3/dist-packages (from aiohttp!=4.0.0a0,!=4.0.0a1->fsspec[http]<=2026.2.0,>=2023.1.0->datasets->-r agentbench/requirements.txt (line 4)) (21.2.0)
Requirement already satisfied: frozenlist>=1.1.1 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from aiohttp!=4.0.0a0,!=4.0.0a1->fsspec[http]<=2026.2.0,>=2023.1.0->datasets->-r agentbench/requirements.txt (line 4)) (1.8.0)
Requirement already satisfied: multidict<7.0,>=4.5 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from aiohttp!=4.0.0a0,!=4.0.0a1->fsspec[http]<=2026.2.0,>=2023.1.0->datasets->-r agentbench/requirements.txt (line 4)) (6.7.1)
Requirement already satisfied: propcache>=0.2.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from aiohttp!=4.0.0a0,!=4.0.0a1->fsspec[http]<=2026.2.0,>=2023.1.0->datasets->-r agentbench/requirements.txt (line 4)) (0.5.2)
Requirement already satisfied: yarl<2.0,>=1.17.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from aiohttp!=4.0.0a0,!=4.0.0a1->fsspec[http]<=2026.2.0,>=2023.1.0->datasets->-r agentbench/requirements.txt (line 4)) (1.24.2)
Requirement already satisfied: cffi>=2.0.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from cryptography>=38.0.3->google-auth<3.0.0,>=2.48.1->google-auth[requests]<3.0.0,>=2.48.1->google-genai<2.0.0,>=1.65.0->langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (2.0.0)
Requirement already satisfied: pycparser in /usr/lib/python3/dist-packages (from cffi>=2.0.0->cryptography>=38.0.3->google-auth<3.0.0,>=2.48.1->google-auth[requests]<3.0.0,>=2.48.1->google-genai<2.0.0,>=1.65.0->langchain-google-genai<5.0.0,>=4.2.2->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (2.21)
Requirement already satisfied: six>=1.5 in /usr/lib/python3/dist-packages (from python-dateutil>=2.8.2->pandas->-r agentbench/requirements.txt (line 5)) (1.16.0)
Requirement already satisfied: click>=8.2.1 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from typer>=0.20.0->huggingface-hub<2.0,>=0.25.0->datasets->-r agentbench/requirements.txt (line 4)) (8.4.0)
Requirement already satisfied: shellingham>=1.3.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from typer>=0.20.0->huggingface-hub<2.0,>=0.25.0->datasets->-r agentbench/requirements.txt (line 4)) (1.5.4)
Requirement already satisfied: rich>=13.8.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from typer>=0.20.0->huggingface-hub<2.0,>=0.25.0->datasets->-r agentbench/requirements.txt (line 4)) (15.0.0)
Requirement already satisfied: annotated-doc>=0.0.2 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from typer>=0.20.0->huggingface-hub<2.0,>=0.25.0->datasets->-r agentbench/requirements.txt (line 4)) (0.0.4)
Requirement already satisfied: markdown-it-py>=2.2.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from rich>=13.8.0->typer>=0.20.0->huggingface-hub<2.0,>=0.25.0->datasets->-r agentbench/requirements.txt (line 4)) (4.2.0)
Requirement already satisfied: pygments<3.0.0,>=2.13.0 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from rich>=13.8.0->typer>=0.20.0->huggingface-hub<2.0,>=0.25.0->datasets->-r agentbench/requirements.txt (line 4)) (2.20.0)
Requirement already satisfied: mdurl~=0.1 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from markdown-it-py>=2.2.0->rich>=13.8.0->typer>=0.20.0->huggingface-hub<2.0,>=0.25.0->datasets->-r agentbench/requirements.txt (line 4)) (0.1.2)
Requirement already satisfied: bracex>=2.1.1 in /home/central/ojaiyeob/.local/lib/python3.11/site-packages (from wcmatch->deepagents==0.5.7->-r agentbench/requirements.txt (line 1)) (2.6)
Building wheels for collected packages: deepagents
  Building wheel for deepagents (pyproject.toml) ... done
  Created wheel for deepagents: filename=deepagents-0.5.7-py3-none-any.whl size=187644 sha256=297603f36843479ae94aa5c8f98d9ae4c3f66dbbb35a2b6487b483b43a51dee2
  Stored in directory: /tmp/pip-ephem-wheel-cache-l76a1hkf/wheels/67/d1/66/6c1b78f1a5c339c94a4a36f1d66cce2b6276edc45e6382ef80
Successfully built deepagents
Installing collected packages: deepagents
  Attempting uninstall: deepagents
    Found existing installation: deepagents 0.5.7
    Uninstalling deepagents-0.5.7:
      Successfully uninstalled deepagents-0.5.7
Successfully installed deepagents-0.5.7
Verifying Deep Agents import...
deepagents: /home/central/ojaiyeob/.local/lib/python3.11/site-packages/deepagents/__init__.py
Deep Agents ready.

========================================
STEP 0: LOCAL FILE CHECK
========================================
ok: agentbench/diagnose_dynamo_tool_calls.py
ok: agentbench/diagnose_deepagents_tool_loop.py
ok: upstream/deepagents/libs/deepagents/pyproject.toml

========================================
STEP 1: CHECK WHETHER EXPERIMENT 6 STARTED DYNAMO WITH TOOL PARSER
========================================
Latest batch dir: experiments/reports/batches/prompt_evolution_batch_20260714_184144
6:Tool-call parser: hermes

========================================
STEP 2: CHECK RECENT PROMPT-EVOLUTION TOOL COUNTS
========================================
execution_prompts_csv: experiments/reports/all_runs_execution_prompts.csv
overview_csv: experiments/reports/all_runs_overview.csv
recent_execution_rows: 20
recent_execution_tool_calls: 0
recent_overview_rows: 20
recent_overview_tool_calls: 0
saved_recent_rows: experiments/reports/tool_call_debug/tool_call_debug_20260714_194439/recent_prompt_evolution_rows.tsv

Latest execution rows:
run_id  phase   tool_call_count tools_called    patch_bytes
agentbench-20260714_135511      execution       0       none    0
agentbench-20260714_135511      execution       0       none    0
agentbench-20260714_135511      execution       0       none    0
agentbench-20260714_135511      execution       0       none    0
agentbench-20260714_135523      execution       0       none    0
agentbench-20260714_135523      execution       0       none    0
agentbench-20260714_135523      execution       0       none    0
agentbench-20260714_135523      execution       0       none    0
agentbench-20260714_135523      execution       0       none    0
agentbench-20260714_135523      execution       0       none    0

========================================
STEP 3: DIRECT DYNAMO TOOL-CALL TEST
========================================
Goal: any case should show tool_calls=1.
[auto] finish_reason='stop' tool_calls=0 content_preview='<tool_call>\n<function=echo_status>\n<parameter=status>\nready\n</parameter>\n</function>\n</tool_call>'
[required] finish_reason='tool_calls' tool_calls=1 content_preview=''
[named] finish_reason='tool_calls' tool_calls=1 content_preview=''
Diagnostic output: experiments/reports/tool_call_debug/tool_call_debug_20260714_194439/dynamo_tool_calls
Direct Dynamo diagnostic exit status: 0
Direct Dynamo tool-call counts: [0, 1, 1]

========================================
STEP 4: DEEP AGENTS TOOL LOOP TEST
========================================
Goal: tool_calls > 0, multi_tool_loop_observed=True, case_success=True.
Diagnostic output: experiments/reports/tool_call_debug/tool_call_debug_20260714_194439/deepagents_tool_loop
tool_calls=0
tool_messages=0
invalid_tool_calls=0
unique_tools=(none)
required_tools_observed=False
missing_required_tools=execute,ls,read_file
multi_tool_loop_observed=False
result_file_exists=False
edit_validation_observed=True
case_success=False
Deep Agents diagnostic exit status: 0
Deep Agents tool calls: 0
Deep Agents tool messages: 0
Deep Agents multi-tool loop observed: False
Deep Agents case success: False
CRITICAL FAIL: Deep Agents did not complete the required multi-tool loop.
ojaiyeob@gracehopper:~/kv_cache_offloading$


```




```bash
cd ~/kv_cache_offloading

AGENTBENCH_DEEPAGENTS_SOURCE=upstream \
./agentbench/debug_prompt_evolution_tool_calls.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

```bash
cd ~/kv_cache_offloading

python3.11 -m pip install ./upstream/deepagents/libs/deepagents
python3.11 -m pip install -r agentbench/requirements.txt
```


```bash
ojaiyeob@gracehopper:~/kv_cache_offloading$ cd ~/kv_cache_offloading

./agentbench/debug_prompt_evolution_tool_calls.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8

========================================
PROMPT EVOLUTION TOOL-CALL DEBUG
========================================
Model: Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
Frontend URL: http://127.0.0.1:8000/v1/chat/completions
Python: python3
Output dir: experiments/reports/tool_call_debug/tool_call_debug_20260714_192116

This script does not start Dynamo.
Run it while the same Dynamo runtime from Experiment 6 is still up.

========================================
STEP 0: LOCAL FILE CHECK
========================================
ok: agentbench/diagnose_dynamo_tool_calls.py
ok: agentbench/diagnose_deepagents_tool_loop.py

========================================
STEP 1: CHECK WHETHER EXPERIMENT 6 STARTED DYNAMO WITH TOOL PARSER
========================================
Latest batch dir: experiments/reports/batches/prompt_evolution_batch_20260714_184144
6:Tool-call parser: hermes

========================================
STEP 2: CHECK RECENT PROMPT-EVOLUTION TOOL COUNTS
========================================
execution_prompts_csv: experiments/reports/all_runs_execution_prompts.csv
overview_csv: experiments/reports/all_runs_overview.csv
recent_execution_rows: 20
recent_execution_tool_calls: 0
recent_overview_rows: 20
recent_overview_tool_calls: 0
saved_recent_rows: experiments/reports/tool_call_debug/tool_call_debug_20260714_192116/recent_prompt_evolution_rows.tsv

Latest execution rows:
run_id  phase   tool_call_count tools_called    patch_bytes
agentbench-20260714_135511      execution       0       none    0
agentbench-20260714_135511      execution       0       none    0
agentbench-20260714_135511      execution       0       none    0
agentbench-20260714_135511      execution       0       none    0
agentbench-20260714_135523      execution       0       none    0
agentbench-20260714_135523      execution       0       none    0
agentbench-20260714_135523      execution       0       none    0
agentbench-20260714_135523      execution       0       none    0
agentbench-20260714_135523      execution       0       none    0
agentbench-20260714_135523      execution       0       none    0

========================================
STEP 3: DIRECT DYNAMO TOOL-CALL TEST
========================================
Goal: any case should show tool_calls=1.
[auto] finish_reason='stop' tool_calls=0 content_preview='<tool_call>\n<function=echo_status>\n<parameter=status>\nready\n</parameter>\n</function>\n</tool_call>'
[required] finish_reason='tool_calls' tool_calls=1 content_preview=''
[named] finish_reason='tool_calls' tool_calls=1 content_preview=''
Diagnostic output: experiments/reports/tool_call_debug/tool_call_debug_20260714_192116/dynamo_tool_calls
Direct Dynamo diagnostic exit status: 0

========================================
STEP 4: DEEP AGENTS TOOL LOOP TEST
========================================
Goal: tool_calls > 0, multi_tool_loop_observed=True, case_success=True.
Deep Agents dependencies could not be imported. Install the AgentBench Python environment first, for example: python3.11 -m pip install -r agentbench/requirements.txt. Original import error: No module named 'deepagents'
Deep Agents diagnostic exit status: 1

========================================
STEP 5: SIMPLE INTERPRETATION
========================================
# Prompt Evolution Tool-Call Debug Summary

- direct_dynamo_exit_status: `0`
- direct_dynamo_tool_call_counts: `[0, 1, 1]`
- direct_dynamo_pass: `True`
- deepagents_exit_status: `1`
- deepagents_tool_calls: `0`
- deepagents_tool_messages: `0`
- deepagents_multi_tool_loop_observed: `False`
- deepagents_case_success: `False`

## Meaning
Dynamo can produce tool calls, but Deep Agents did not complete the tool loop.
The likely issue is Deep Agents/LangChain tool binding or tool-result handling.

- verdict: `deepagents_tool_loop_missing`

Summary file: experiments/reports/tool_call_debug/tool_call_debug_20260714_192116/tool_call_debug_summary.md

========================================
DONE
========================================
Full debug output: experiments/reports/tool_call_debug/tool_call_debug_20260714_192116
ojaiyeob@gracehopper:~/kv_cache_offloading$

```

```bash
cd ~/kv_cache_offloading

./agentbench/debug_prompt_evolution_tool_calls.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```

```bash
cd ~/kv_cache_offloading

export DYNAMO_MACHINE_PROFILE=gh200
source runtime_instrumentation/dynamo_machine_profile.sh

export MODEL_NAME='Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8'
export DYN_TOOL_CALL_PARSER=hermes

./run_dynamo_single_host.sh stop || true

FRONTEND_IMAGE="$FRONTEND_IMAGE" \
WORKER_IMAGE="$WORKER_IMAGE" \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="$MODEL_NAME" \
DYNAMO_SERVED_MODEL_NAME="$MODEL_NAME" \
WORKER_BASE_ARGS="--enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru" \
./run_dynamo_single_host.sh start
```

