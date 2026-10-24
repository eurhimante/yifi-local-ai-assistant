# YIFI — Local Personal AI Assistant

**A self-hosted, French-speaking AI assistant powered by a single lightweight local LLM.**

YIFI is a personal engineering project combining a Python/FastAPI orchestration layer, Ollama, LibreChat, and controlled read-only web tools. The project focuses on practical inference on consumer hardware, traceable tool execution, and incremental, test-driven development.

> **Current milestone: v0.3.1 (working prototype).** Local chat, SearXNG search, and an official GitHub releases API tool have been exercised successfully. This is not yet a general-purpose web browsing agent or a persistent-memory assistant.

## What works today

| Capability | Status | Notes |
|---|---|---|
| Local conversational model | Implemented | `yifi:4b` (quantized Qwen3 4B) through Ollama; no automatic 8B routing |
| LibreChat integration | Implemented | OpenAI-compatible FastAPI endpoints |
| Web search | Implemented | `web_search` uses SearXNG results and **snippets**, not full article text |
| Verified GitHub releases | Implemented | `github_latest_release` uses GitHub REST API `releases/latest` |
| Tool execution provenance | Implemented, limited | Server appends records of executed tools; heuristics also mitigate some unverified model claims |
| Tool-call limits | Implemented | Bounded tool execution, argument validation, read-only endpoints |
| Streaming response format | Tested | SSE-compatible response; generation is largely buffered rather than token-by-token |
| Full webpage reading | Planned | Secure `web_fetch` with private-network/SSRF protections |
| Personal memory and document RAG | Planned | PostgreSQL/pgvector infrastructure exists separately; YIFI memory is not implemented |
| Homelab service control | Planned | Restricted APIs and explicit confirmations for write actions |

## Architecture

```text
LibreChat (UI)
      |
      | OpenAI-compatible API (model ID: yifi-auto)
      v
YIFI Router — FastAPI
      |
      +--> Orchestrator: bounded tool-calling loop
      |       |
      |       +--> web_search ----------> SearXNG (search snippets)
      |       |
      |       +--> github_latest_release -> GitHub REST API
      |
      +--> Ollama (Windows host) ------> yifi:4b

Separate infrastructure, not yet wired to YIFI personal memory:
PostgreSQL + pgvector, existing homelab applications
```

**Data boundary:** model inference runs locally through Ollama. Search queries and GitHub API requests necessarily reach external services when those tools are invoked. The router does not currently open arbitrary webpages.

## Engineering highlights

- Built a Python **FastAPI** router exposing `/health`, `/v1/models`, and `/v1/chat/completions`.
- Reduced the inference path to **one conversational LLM** to keep response times reasonable on a laptop with a 4 GB VRAM GPU.
- Implemented **bounded function/tool calling** with validated inputs and read-only web operations.
- Integrated **SearXNG** for online searches and **GitHub's REST API** for structured release metadata.
- Implemented a server-side tool execution record so the provenance of GitHub release information is distinguishable from model-generated claims.
- Added **unit tests** and validated integration against a **separate development Docker container** before deploying the tested version to the live router.

### Validation of v0.3.1

- **5 unit tests passed**, including tests for unsupported provenance claims.
- **3 live integration scenarios passed** against the isolated development router: simple chat, Ollama's latest release, and a nonexistent GitHub repository.
- **1 SSE format check passed**: HTTP 200, `text/event-stream`, `data:` events, and `[DONE]`.
- Post-deployment `/health` check and LibreChat GitHub release query succeeded; the response contained a server-generated record confirming an actual GitHub API call.

These tests cover specific scenarios. They do **not** establish perfect factual accuracy, universal tool-selection reliability, or full streaming latency characteristics.

## Repository layout

```text
yifi-local-ai-assistant/
├── app/
│   ├── main.py              # FastAPI/OpenAI-compatible endpoints
│   ├── orchestrator.py      # LLM and tool execution loop
│   └── tools/
│       ├── web_search.py    # SearXNG snippets
│       └── github_releases.py # Structured GitHub release lookup
├── tests/
│   └── test_orchestrator.py
├── docs/
│   └── releases/
│       └── v0.3.1.md
├── Dockerfile
├── requirements.txt
├── CHANGELOG.md
└── README.md
```

This repository contains the **YIFI-specific router**, not the full LibreChat deployment or its data volumes. A sanitized, reproducible standalone deployment guide is still planned.

## Running the tests

Create a local Python virtual environment, install dependencies, and run the unit tests:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

Unit tests use simulated service responses. Live web tools additionally require reachable SearXNG/GitHub services. The DNS name `searxng` is normally available on the Docker network, not directly in Windows Python.

## Development roadmap

- [x] **v0.2** — Single local conversational model (`yifi:4b`).
- [x] **v0.3.1** — Read-only search and GitHub release tools, tool provenance safeguards, isolated integration tests.
- [ ] **v0.3.2** — Secure webpage retrieval, improved source attribution, and stronger structured-answer validation.
- [ ] **v0.4** — Editable, provenance-aware personal memory with PostgreSQL.
- [ ] **v0.5** — Document ingestion and semantic RAG with pgvector.
- [ ] **v0.6** — Permission-limited homelab integrations.

## Known limitations

- `web_search` returns **search snippets**; it does not verify full webpage content.
- Tool use is partly decided by the 4B model and **may be skipped**, even when useful.
- Provenance safeguards detect certain unsupported claims, but generated explanations can still be misleading. In one live test, the model incorrectly described an API-provided date as simulated.
- GitHub `releases/latest` reports GitHub's latest non-draft/non-prerelease release for that repository; this does not prove anything about other distribution channels.
- The SSE interface is compatible with LibreChat, but output is substantially buffered.
- No persistent YIFI memory or homelab write access has been implemented.

## Security and privacy

Tool outputs are **untrusted external data**, never instructions to execute. Only explicitly registered tools are available, with bounded calls and validated parameters. This milestone does **not** provide arbitrary URL fetching, private-network access, shell execution, or write operations against homelab services.

Keep `.env` files, access tokens, personal documents, databases, model weights, and runtime volumes out of version control. Review staged changes before pushing.

## Release documentation

- [v0.3.1 release notes](docs/releases/v0.3.1.md)
- [Changelog](CHANGELOG.md)

YIFI is an ongoing personal project demonstrating Python backend development, LLM integration, API orchestration, Docker-based testing, and engineering tradeoffs for local AI.
