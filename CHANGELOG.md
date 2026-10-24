# Changelog

Notable changes to the **YIFI-specific router** are documented here. This is not the LibreChat or Ollama upstream changelog.

## [v0.3.1] — 2026-10-24

### Added
- `web_search` integration with SearXNG, returning limited search snippets and URLs.
- `github_latest_release` integration with the GitHub REST API for structured, official release metadata.
- Bounded function/tool execution through the FastAPI orchestrator.
- Server-generated provenance records for tools actually executed.
- Automated tests for tool availability, ordinary conversation, and several unsupported-verification claims.

### Improved
- Single-model operation with `yifi:4b` retained from v0.2.
- Better handling of cases where the model claims to have verified an API result without a corresponding tool call.
- Development workflow with an isolated Docker container, unit tests, and an explicit backup before production deployment.

### Validated
- Five unit tests passed.
- Three isolated live integration cases passed (plain chat, GitHub release success, GitHub release failure).
- SSE response format validated.
- Production health endpoint and a LibreChat-to-GitHub-release request verified after deployment.

### Known limitations
- Search results are snippets, not full-page reads.
- Model-selected tool calling is not guaranteed; provenance filtering is heuristic, not a proof of factual accuracy.
- Buffered SSE output rather than progressive token streaming.
- No persistent personal memory or document RAG yet.

See [detailed release notes](docs/releases/v0.3.1.md).

## [v0.2] — 2026-10 (before v0.3.1)

- Replaced legacy 4B/8B heuristic routing with a single configured conversational model, `yifi:4b`.
- Kept the OpenAI-compatible router endpoints and LibreChat integration.

## [v0.1] — Initial repository snapshot

- Published the early Python/FastAPI router, Dockerfile, dependency list and initial project documentation.
