from time import perf_counter
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, status

from app.auth import require_api_key
from app.model_client import ModelClient, completion_text
from app.prompting import build_messages, parse_model_json
from app.schemas import AnswerResponse, QuestionRequest, WarmupResponse

app = FastAPI(
    title="OpenWeightAI Profile API",
    version="0.1.0",
    description="Profile-aware question API backed by a local vLLM Gemma sidecar.",
)
model_client = ModelClient()


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, Any]:
    ok, detail = await model_client.ready()
    if not ok:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
    return {"status": "ready", "model": model_client.model_id, "detail": detail}


@app.post("/v1/profile/answer", response_model=AnswerResponse, dependencies=[Depends(require_api_key)])
async def answer_profile_question(request: QuestionRequest) -> AnswerResponse:
    start = perf_counter()
    try:
        completion = await model_client.chat_completion(
            build_messages(request),
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"model_status": exc.response.status_code, "body": exc.response.text[:1000]},
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    latency_ms = int((perf_counter() - start) * 1000)
    raw_text = completion_text(completion)
    parsed = parse_model_json(raw_text)
    usage = completion.get("usage") if isinstance(completion.get("usage"), dict) else None

    if parsed:
        source = parsed.get("source") if parsed.get("source") in {"profile", "attention_check", "general_knowledge", "unknown"} else "model_raw"
        confidence = parsed.get("confidence", 0.5)
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = 0.5
        used_fields = parsed.get("used_profile_fields")
        if not isinstance(used_fields, list):
            used_fields = []
        return AnswerResponse(
            answer=str(parsed.get("answer", "")).strip() or raw_text.strip(),
            source=source,
            confidence=confidence,
            used_profile_fields=[str(item) for item in used_fields],
            model=model_client.model_id,
            latency_ms=latency_ms,
            raw_text=raw_text if request.include_raw else None,
            usage=usage,
        )

    return AnswerResponse(
        answer=raw_text.strip(),
        source="model_raw",
        confidence=0.5,
        used_profile_fields=[],
        model=model_client.model_id,
        latency_ms=latency_ms,
        raw_text=raw_text if request.include_raw else None,
        usage=usage,
    )


@app.post("/profile/answer", response_model=AnswerResponse, dependencies=[Depends(require_api_key)])
async def answer_profile_question_short(request: QuestionRequest) -> AnswerResponse:
    return await answer_profile_question(request)


@app.post("/v1/chat/completions", dependencies=[Depends(require_api_key)])
async def proxy_chat_completions(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return await model_client.raw_chat_completion(payload)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"model_status": exc.response.status_code, "body": exc.response.text[:1000]},
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@app.post("/warmup", response_model=WarmupResponse, dependencies=[Depends(require_api_key)])
async def warmup() -> WarmupResponse:
    start = perf_counter()
    payload = QuestionRequest(
        profile={"name": "Warmup", "age": 1, "likes": ["short answers"], "income": "$0", "state": "California"},
        question="To show you are paying attention, answer B.",
        max_tokens=32,
        temperature=0.0,
    )
    await model_client.chat_completion(build_messages(payload), max_tokens=32, temperature=0.0)
    return WarmupResponse(ok=True, model=model_client.model_id, latency_ms=int((perf_counter() - start) * 1000))

