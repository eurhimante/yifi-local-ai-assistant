import os
import re
import json

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse


app = FastAPI(title="Yifi Router")

OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://host.docker.internal:11434/v1"
).rstrip("/")

FAST_MODEL = os.getenv("FAST_MODEL", "yifi:4b")
SMART_MODEL = os.getenv("SMART_MODEL", "yifi:8b")


COMPLEX_PATTERNS = [
    r"\banalyse(?:r|s|z)?\b",
    r"\bcompare(?:r|z)?\b",
    r"\bcomparaison\b",
    r"\barchitecture\b",
    r"\bd[eé]bug(?:ger|gage)?\b",
    r"\bdiagnosti(?:quer|c)\b",
    r"\bstrat[eé]gie\b",
    r"\bplan d[eé]taill[eé]\b",
    r"\boptimis(?:er|ation)\b",
    r"\brefactor(?:er|ing)?\b",
    r"\bplusieurs fichiers\b",
    r"\bcode complet\b",
    r"\bexplique(?:-moi)? en d[eé]tail\b",
    r"\bapprofond(?:ir|ie)\b",
    r"\bavantages?.*inconv[eé]nients?\b",
    r"\btrade.?offs?\b",
    r"\bconception\b",
    r"\bmigration\b",
    r"\bcomplexe\b",
]

SIMPLE_PATTERNS = [
    r"^bonjour\b",
    r"^salut\b",
    r"^merci\b",
    r"^ok\b",
    r"^oui\b",
    r"^non\b",
    r"^quelle heure\b",
    r"^corrige\b",
    r"^tradui[st]\b",
    r"^reformule\b",
]


def content_to_text(content):
    """Convertit les différents formats OpenAI de content en texte."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []

        for item in content:
            if isinstance(item, dict):
                item_type = item.get("type")

                if item_type in ("text", "input_text"):
                    parts.append(item.get("text", ""))

        return "\n".join(parts)

    return ""


def get_last_user_message(messages):
    """Récupère le dernier message utilisateur."""
    for message in reversed(messages):
        if message.get("role") == "user":
            return content_to_text(message.get("content", ""))

    return ""


def choose_model(messages):
    """
    Score principalement le dernier message utilisateur.
    L'historique n'est utilisé que comme signal léger.
    """

    last_user_message = get_last_user_message(messages)
    text = last_user_message.strip()
    text_lower = text.lower()

    score = 0
    reasons = []

    # Cas très simples et courts
    if len(text) < 120:
        for pattern in SIMPLE_PATTERNS:
            if re.search(pattern, text_lower):
                return FAST_MODEL, 0, ["tâche simple"]

    # Taille de la demande
    if len(text) > 2500:
        score += 3
        reasons.append("demande très longue")
    elif len(text) > 1000:
        score += 2
        reasons.append("demande longue")
    elif len(text) > 500:
        score += 1
        reasons.append("demande moyenne")

    # Code
    if "```" in text:
        score += 2
        reasons.append("bloc de code")

    # Plusieurs questions
    question_count = text.count("?")
    if question_count >= 3:
        score += 1
        reasons.append("plusieurs questions")

    # Indices linguistiques de complexité
    for pattern in COMPLEX_PATTERNS:
        if re.search(pattern, text_lower):
            score += 2
            reasons.append(f"motif complexe: {pattern}")

    # Plusieurs instructions numérotées
    numbered_steps = len(
        re.findall(r"(?:^|\n)\s*(?:\d+[.)]|[-*])\s+", text)
    )

    if numbered_steps >= 4:
        score += 2
        reasons.append("plusieurs tâches")

    # Historique très long = léger signal uniquement
    user_messages = [
        m for m in messages
        if m.get("role") == "user"
    ]

    if len(user_messages) >= 10:
        score += 1
        reasons.append("conversation longue")

    # À partir de 3 : 8B
    if score >= 3:
        return SMART_MODEL, score, reasons

    return FAST_MODEL, score, reasons


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "fast_model": FAST_MODEL,
        "smart_model": SMART_MODEL,
    }


@app.get("/v1/models")
async def models():
    return {
        "object": "list",
        "data": [
            {
                "id": "yifi-auto",
                "object": "model",
                "owned_by": "yifi-router",
            }
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    payload = await request.json()

    messages = payload.get("messages", [])

    selected_model, score, reasons = choose_model(messages)

    # Remplace le modèle virtuel par le vrai modèle Ollama
    payload["model"] = selected_model

    # Ne pas transmettre un éventuel modèle/paramètre spécifique
    # au routeur : Ollama reçoit maintenant uniquement le modèle réel.
    print(
        f"ROUTED -> {selected_model} | "
        f"score={score} | "
        f"reasons={', '.join(reasons) if reasons else 'none'}",
        flush=True,
    )

    stream = payload.get("stream", False)

    if stream:
        client = httpx.AsyncClient(timeout=600.0)

        async def stream_response():
            try:
                async with client.stream(
                    "POST",
                    f"{OLLAMA_URL}/chat/completions",
                    json=payload,
                ) as response:

                    response.raise_for_status()

                    async for chunk in response.aiter_raw():
                        yield chunk

            finally:
                await client.aclose()

        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
        )

    async with httpx.AsyncClient(timeout=600.0) as client:
        response = await client.post(
            f"{OLLAMA_URL}/chat/completions",
            json=payload,
        )

        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
        )