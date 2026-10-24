## [0.3.1] — 2026-10-24

### Added
- SearXNG-backed `web_search` for public-web titles, URLs, and snippets.
- `github_latest_release` for structured GitHub release metadata.
- Bounded tool-calling orchestration using the local `yifi:4b` model.
- Server-generated audit text for actual GitHub tool execution and errors.
- Automated tests for tool availability and unsupported verification claims.

### Improved
- Handling of some unsupported model claims about external API verification.
- Independent development-container validation before production deployment.

### Validated
- Five unit tests, three live-model development scenarios, SSE response format, and production health/API smoke tests.

### Known limitations
- Search snippets are not full-page verification.
- Tool invocation remains model-dependent; generated responses can still be misleading.
- Streaming is buffered rather than truly incremental during tool orchestration.
- Memory and document RAG are not implemented.

See [full v0.3.1 release notes](docs/releases/v0.3.1.md).
