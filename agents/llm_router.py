"""Provider-agnostic LLM routing for agent runtime calls."""
from __future__ import annotations

import json
import os
from typing import Any

import httpx

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - optional dependency path
    genai = None

DEFAULT_MODEL_BY_TARGET = {
    "gemini": "gemini-1.5-flash",
    "claude": "claude-sonnet-4-20250514",
    "openai": "gpt-4o-mini",
    "ollama": "mistral",
}


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _strip_fence(text: str) -> str:
    clean = text.strip()
    if clean.startswith("```") and clean.endswith("```"):
        lines = clean.splitlines()
        if len(lines) >= 2:
            clean = "\n".join(lines[1:-1]).strip()
    if clean.startswith("json\n"):
        clean = clean[5:].strip()
    return clean


def _call_gemini(*, system_prompt: str, user_message: str, model_id: str) -> str:
    if genai is None:
        raise RuntimeError("google-generativeai is not installed for gemini target.")
    genai.configure(api_key=_require_env("GEMINI_API_KEY"))
    model = genai.GenerativeModel(model_name=model_id, system_instruction=system_prompt)
    response = model.generate_content(user_message)
    return str(getattr(response, "text", "") or "").strip()


def _call_claude(*, system_prompt: str, user_message: str, model_id: str, temperature: float, max_tokens: int) -> str:
    headers = {
        "x-api-key": _require_env("ANTHROPIC_API_KEY"),
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model_id,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
    }
    with httpx.Client(timeout=60) as client:
        response = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    blocks = data.get("content", [])
    text_parts = [block.get("text", "") for block in blocks if isinstance(block, dict) and block.get("type") == "text"]
    return "\n".join(part for part in text_parts if part).strip()


def _call_openai(*, system_prompt: str, user_message: str, model_id: str, temperature: float, max_tokens: int) -> str:
    headers = {
        "Authorization": f"Bearer {_require_env('OPENAI_API_KEY')}",
        "content-type": "application/json",
    }
    payload = {
        "model": model_id,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }
    with httpx.Client(timeout=60) as client:
        response = client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    choices = data.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return str(message.get("content", "")).strip()


def _call_ollama(*, system_prompt: str, user_message: str, model_id: str) -> str:
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    payload = {
        "model": model_id,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }
    with httpx.Client(timeout=60) as client:
        response = client.post(f"{host}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
    return str(data.get("message", {}).get("content", "")).strip()


def resolve_target(target: str | None = None) -> str:
    value = (target or os.getenv("LLM_TARGET", "gemini")).strip().lower()
    if value not in {"claude", "openai", "gemini", "ollama", "any"}:
        raise RuntimeError(f"Unsupported LLM_TARGET: {value}")
    if value == "any":
        for candidate, env_name in (
            ("claude", "ANTHROPIC_API_KEY"),
            ("openai", "OPENAI_API_KEY"),
            ("gemini", "GEMINI_API_KEY"),
            ("ollama", "OLLAMA_HOST"),
        ):
            if os.getenv(env_name):
                return candidate
        return "gemini"
    return value


def default_model_for_target(target: str) -> str:
    return DEFAULT_MODEL_BY_TARGET.get(target, DEFAULT_MODEL_BY_TARGET["gemini"])


def generate_text(
    *,
    system_prompt: str,
    user_message: str,
    llm_target: str | None = None,
    model_id: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> str:
    target = resolve_target(llm_target)
    model = (model_id or os.getenv("MODEL_ID") or default_model_for_target(target)).strip()
    if target == "gemini":
        return _call_gemini(system_prompt=system_prompt, user_message=user_message, model_id=model)
    if target == "claude":
        return _call_claude(
            system_prompt=system_prompt,
            user_message=user_message,
            model_id=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    if target == "openai":
        return _call_openai(
            system_prompt=system_prompt,
            user_message=user_message,
            model_id=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    return _call_ollama(system_prompt=system_prompt, user_message=user_message, model_id=model)


def generate_json(
    *,
    system_prompt: str,
    user_message: str,
    llm_target: str | None = None,
    model_id: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    raw = generate_text(
        system_prompt=system_prompt,
        user_message=user_message,
        llm_target=llm_target,
        model_id=model_id,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    clean = _strip_fence(raw)
    try:
        payload = json.loads(clean)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"LLM response was not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("LLM JSON response must be an object.")
    return payload
