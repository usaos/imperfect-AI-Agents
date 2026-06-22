# imperfect · Agent Imperfection Protocol

> The immune system for AI Agents. Share failures, avoid pitfalls, generate DPO vaccines.

<div align="center">

![version](https://img.shields.io/badge/version-3.1-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![MCP](https://img.shields.io/badge/MCP-compatible-purple)

**Scar Tissue Project ·imperfect**

</div>

## 🧠 What is imperfect?

imperfect is a distributed failure memory network for AI Agents. Instead of every Agent reinventing the wheel and stepping in the same pit, imperfect collects "failure → reflection → correction" triplets across all Agent ecosystems, forming a collective immune system.

- 🛡️ **Immune System**: Agents query historical failures before execution, avoiding known dead ends
- 💉 **Vaccine Factory**: Export high-quality DPO contrast datasets directly for model alignment
- 🌐 **Ecosystem Native**: Works out of the box with Claude MCP, Hermes, OpenClaw and more
- 🪶 **Zero Cost**: Local deployment with SQLite + Faiss, no paid APIs required

## ✨ Core Features

### 🔍 Search before you act
Query 10000+ historical failure cases with vector similarity search. Know where the pits are before you step in.

### 📝 Reflect after you fail
Structured reflection logging turns every mistake into collective wisdom for the whole ecosystem.

### 🧪 DPO Dataset Export
One-click export of standard `prompt/chosen/rejected` triplets, directly feed into DPO training pipelines.

### 🧩 Multi-ecosystem Compatible
- **Claude MCP**: Native MCP Server, one-line config for Claude Desktop
- **Hermes**: Standard OpenAPI tool, Function Calling ready
- **OpenClaw**: Async hook SDK, auto-capture exceptions with background reflection

## 🚀 One-Click Deploy

### Local Docker (Recommended)

```bash
git clone https://github.com/yourname/imperfect-mvp.git
cd imperfect-mvp
mkdir -p data
docker compose up --build -d
```

- **API Docs**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8080

### Local Development

```bash
cd backend
pip install -r requirements.txt
python main.py
```

## 📦 Installation & Usage

### Claude Desktop MCP Setup

1. Install dependencies:
   ```bash
   pip install mcp requests python-dotenv
   ```

2. Add to your `claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "imperfect": {
         "command": "python",
         "args": ["/path/to/backend/mcp_server.py"],
         "env": {
           "IMPERFECT_API_BASE": "http://localhost:8000"
         }
       }
     }
   }
   ```

3. Restart Claude. You can now ask: *"Search past failures in web scraping before writing the crawler"*

### Python SDK Hook

```python
import sys
sys.path.insert(0, '/path/to/sdk')

from imperfect_sdk import ImperfectHook

# 初始化（支持本地Ollama反思）
hook = ImperfectHook(
    api_base="http://localhost:8000",
    ollama_base="http://localhost:11434",
    reflection_model="qwen2:1.8b"
)

def risky_api_call():
    try:
        # 你的业务代码
        raise TimeoutError("API request timed out after 10s")
    except Exception as e:
        hook.catch_exception("Fetch user data from external API", e, tags="api,timeout")
        print("Error caught, auto-reflecting in background")

risky_api_call()
import time
time.sleep(5)  # 等待后台异步上报
```

### Seed Data Generation

Generate initial failure data using local Ollama:

```bash
# 1. Install Ollama and pull model
ollama pull qwen2:7b

# 2. Run seed script
cd scripts
pip install requests
python seed_data.py
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│  Claude MCP  ·  Hermes Tool  ·  OpenClaw Hook  │
├─────────────────────────────────────────┤
│  FastAPI REST API  /  MCP Server             │
├─────────────────────────────────────────┤
│  SQLite / PostgreSQL + Faiss / pgvector       │
└─────────────────────────────────────────┘
```

## 📁 Project Structure

```
imperfect-mvp/
├── backend/                 # Core backend + MCP Server
│   ├── config.py            # Unified configuration
│   ├── database.py          # SQLite + Faiss vector DB
│   ├── main.py              # FastAPI REST API
│   ├── mcp_server.py        # MCP Server
│   └── requirements.txt     # Python dependencies
├── sdk/                     # Agent/OpenClaw SDK
│   └── imperfect_sdk/
│       ├── __init__.py
│       └── hook.py          # Async reflection hook
├── scripts/
│   └── seed_data.py         # Zero-cost seed data generator
├── web/
│   └── index.html           # Minimal Web Dashboard
├── data/                    # Data persistence directory
├── Dockerfile               # Backend image build
├── docker-compose.yml       # One-click deploy
└── README.md
```

## 🎯 Why imperfect?

In 2026, everyone is making Agents smarter. No one is making them *less wrong*.

Perfect models produce mediocre outputs. Real errors breed evolving intelligence. imperfect is not a patch. It is the immune system of the Agent ecosystem.

## 🤝 Contributing

- Submit new platform adapters
- Deploy public nodes
- Report bugs and suggest improvements

