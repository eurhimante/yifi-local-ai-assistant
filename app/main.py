"""YIFI v0.3: one LLM, bounded web-search tool loop, OpenAI-compatible API."""
import json
import time
import uuid
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from .orchestrator import complete, YIFI_MODEL

app = FastAPI(title='Yifi Router')
VIRTUAL_MODEL = 'yifi-auto'


@app.get('/health')
async def health():
    return {'status': 'ok', 'model': YIFI_MODEL}


@app.get('/v1/models')
async def models():
    return {'object': 'list', 'data': [{'id': VIRTUAL_MODEL, 'object': 'model', 'owned_by': 'yifi-router'}]}


def as_sse(result):
    """Emit valid SSE after orchestration completes (buffered, not token-live)."""
    message = (result.get('choices') or [{}])[0].get('message') or {}
    content = message.get('content') or ''
    chunk = {
        'id': result.get('id', f'chatcmpl-{uuid.uuid4().hex}'),
        'object': 'chat.completion.chunk',
        'created': result.get('created', int(time.time())),
        'model': VIRTUAL_MODEL,
        'choices': [{'index': 0, 'delta': {'role': 'assistant', 'content': content}, 'finish_reason': None}],
    }
    yield f'data: {json.dumps(chunk, ensure_ascii=False)}\n\n'
    chunk['choices'] = [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]
    yield f'data: {json.dumps(chunk, ensure_ascii=False)}\n\n'
    yield 'data: [DONE]\n\n'


@app.post('/v1/chat/completions')
async def chat_completions(request: Request):
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            return JSONResponse(status_code=400, content={'error': 'Expected JSON object'})
        streamed = payload.get('stream', False)
        result = await complete(payload)
        print('ROUTED -> yifi:4b | web tools enabled', flush=True)
        if streamed:
            return StreamingResponse(as_sse(result), media_type='text/event-stream')
        return JSONResponse(content=result)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={'error': str(exc)})
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        return JSONResponse(status_code=502, content={'error': f'Upstream request failed: {type(exc).__name__}'})
