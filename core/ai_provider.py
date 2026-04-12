"""Shared AI provider wrapper with fallback support."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


def _load_env_value(*keys: str) -> Optional[str]:
    for key in keys:
        value = os.environ.get(key)
        if value:
            return value
    env_path = os.path.expanduser('~/.hermes/grant-system/.env')
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    k, v = line.split('=', 1)
                    if k.strip() in keys and v.strip():
                        return v.strip().strip('"').strip("'")
        except Exception:
            pass
    return None


@dataclass
class AIResult:
    text: str
    provider: str
    model: str


class AIProviderError(RuntimeError):
    pass


def _gemini_generate(prompt: str, model: str) -> AIResult:
    api_key = _load_env_value('GP_GOOGLE_API_KEY', 'GOOGLE_API_KEY')
    if not api_key:
        raise AIProviderError('Gemini API key is not configured')
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model, contents=prompt)
        return AIResult(text=(response.text or '').strip(), provider='gemini', model=model)
    except Exception as e:
        raise AIProviderError(f'Gemini request failed: {e}') from e


def _minimax_generate(prompt: str, model: str) -> AIResult:
    api_key = _load_env_value('GP_MINIMAX_API_KEY', 'MINIMAX_API_KEY')
    if not api_key:
        raise AIProviderError('Fallback MiniMax API key is not configured')
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': 'Return only the requested content. No markdown fences unless explicitly requested.'},
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.2,
    }
    r = requests.post(
        'https://api.minimax.io/v1/text/chatcompletion_v2',
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        json=payload,
        timeout=90,
    )
    if not r.ok:
        raise AIProviderError(f'Fallback provider HTTP {r.status_code}')
    data = r.json()
    try:
        choices = data.get('choices') or data.get('result', {}).get('choices') or []
        text = choices[0]['message']['content'] if choices else data.get('reply', '')
    except Exception as e:
        raise AIProviderError(f'Fallback provider response parse failed: {e}') from e
    return AIResult(text=(text or '').strip(), provider='minimax', model=model)


def generate_text(prompt: str, model: str = 'gemini-2.5-flash', fallback_model: Optional[str] = None) -> AIResult:
    fallback_model = fallback_model or _load_env_value('GP_FALLBACK_MODEL') or 'MiniMax-2.7-Highspeed'
    try:
        return _gemini_generate(prompt, model)
    except Exception as primary_err:
        logger.warning('Primary AI provider failed, falling back: %s', primary_err)
        try:
            return _minimax_generate(prompt, fallback_model)
        except Exception as fallback_err:
            logger.error('Both AI providers failed: primary=%s fallback=%s', primary_err, fallback_err)
            raise AIProviderError(f'All AI providers failed: {fallback_err}') from fallback_err


def safe_json_loads(raw: str) -> Any:
    raw = (raw or '').strip()
    if raw.startswith('```'):
        raw = raw.replace('```json', '').replace('```', '').strip()
    return json.loads(raw)
