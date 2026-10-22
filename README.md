# YIFI — Local Personal AI Assistant

**YIFI** is a self-hosted personal AI assistant project built around a single local language model. The goal is to combine private, local inference with web research, a structured personal knowledge base, and controlled integrations with homelab services.

> **Status: Work in progress.** The local chat/API path is working. End-to-end autonomous web searches, personal memory, and homelab actions are planned, not yet implemented in the YIFI router.

## Project goals

- Run a practical French-speaking assistant locally on modest hardware.
- Search the web and provide traceable sources when up-to-date information is needed.
- Retrieve relevant information from personal documents and project notes using RAG.
- Maintain an editable, source-aware memory of preferences, decisions, and project progress.
- Integrate selected self-hosted services through permission-controlled APIs.
- Keep **one conversational LLM**; auxiliary embedding/OCR components may be added for specialized processing.

## Current architecture

```text
LibreChat (UI)
    |
    v
YIFI Router (FastAPI, OpenAI-compatible endpoint)
    |
    v
Ollama on the Windows host -> yifi:4b (Qwen3 4B, Q4_0)

Existing adjacent services (integration to be verified / developed):
- SearXNG: reachable JSON search endpoint
- LibreChat RAG API + PostgreSQL/pgvector: running infrastructure
- MongoDB + Meilisearch: LibreChat services
```

The router currently exposes `yifi-auto` to LibreChat and forwards chat completions to Ollama. **The current router still contains older 4B/8B routing rules**; migration to `yifi:4b` only is the next planned change. It does not yet implement its own web-search tool loop.

## Verified functionality

- Local inference with `yifi:4b` through Ollama.
- LibreChat reaches the router's `/v1/models` endpoint.
- Router `/v1/chat/completions` successfully returns a `yifi:4b` response.
- The router can reach the Windows Ollama endpoint.
- SearXNG returns real JSON search results to the router container.
- Comparative local benchmarks performed against `qwen3.5:4b` to choose a model suitable for the current hardware.

## Roadmap

- [ ] Remove legacy multi-model routing and pin all chat requests to `yifi:4b`.
- [ ] Add secure `web_search` tool execution through SearXNG.
- [ ] Add URL reading, source verification, and citations.
- [ ] Design a personal-data schema in PostgreSQL and semantic retrieval using pgvector.
- [ ] Add controlled document ingestion (text/PDF; OCR in a later phase).
- [ ] Add project memory with provenance, updates, and deletion support.
- [ ] Integrate homelab applications using limited-permission APIs.
- [ ] Add automated tests, monitoring, backup/restore checks, and security safeguards.

## Technologies

Python · FastAPI · Ollama · Qwen3 · LibreChat · Docker Compose · SearXNG · PostgreSQL · pgvector · REST APIs

## Project layout

For a **standalone router repository**, the initial contents should be limited to the router source and documentation:

```text
yifi-assistant/
├── app/
│   └── main.py
├── Dockerfile
├── requirements.txt  # only if present in the existing router
├── .gitignore
└── README.md
```

Do not publish the entire LibreChat installation or its runtime volumes. The upstream LibreChat application is a separate project.

## Development status and limitations

This repository documents the YIFI-specific work. Existing `main.py` contains a legacy model-selection mechanism; live tool orchestration and personal memory are **not** available yet. Benchmark scripts and configurations will be added separately after review, without private data or API keys.

## Security

Never commit `.env` files, API keys, tokens, personal documents, local databases, embeddings of private content, logs, model weights, or Docker volumes. Review the Git staging area before every push. Network and file-system actions introduced later will require explicit permissions and validation.
