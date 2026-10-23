"""YIFI OpenAI-compatible proxy, pinned to a single local Ollama model."""

import os

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI(title="Yifi Router")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434/v1").rstrip("/")
YIFI_MODEL = os.getenv("YIFI_MODEL", "yifi:4b")
VIRTUAL_MODEL = "yifi-auto"  # Preserve the model name configured in LibreChat.


@app.get("/health")
async def health():
    return {"status": "ok", "model": YIFI_MODEL}


@app.get("/v1/models")
async def models():
    return {
        "object": "list",
        "data": [{"id": VIRTUAL_MODEL, "object": "model", "owned_by": "yifi-router"}],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    payload = await request.json()
    if not isinstance(payload, dict):
        return JSONResponse(status_code=400, content={"error": "Expected a JSON object"})

    # Pin all requests to the same model, including complex prompts.
    payload["model"] = YIFI_MODEL
    print(f"ROUTED -> {YIFI_MODEL}", flush=True)

    url = f"{OLLAMA_URL}/chat/completions"
    if payload.get("stream", False):
        client = httpx.AsyncClient(timeout=600.0)

        async def stream_response():
            try:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_raw():
                        yield chunk
            finally:
                await client.aclose()

        return StreamingResponse(stream_response(), media_type="text/event-stream")

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(url, json=payload)
    except httpx.RequestError as exc:
        return JSONResponse(status_code=502, content={"error": f"Ollama unavailable: {type(exc).__name__}"})

    try:
        content = response.json()
    except ValueError:
        return JSONResponse(status_code=502, content={"error": "Ollama returned non-JSON response"})
    return JSONResponse(content=content, status_code=response.status_code)
