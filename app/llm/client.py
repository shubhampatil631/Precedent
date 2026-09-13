"""
app/llm/client.py
Multi-provider LLM client with automatic fallback order:
1. Ollama (local) -> 2. Groq (fast cloud API) -> 3. Google Gemini (strong reasoning)
"""

import os
import json
import logging
import time
from typing import Optional, Dict, Any, List
import httpx

from app.config import (
    GEMINI_API_KEY,
    GROQ_API_KEY,
    OLLAMA_HOST,
    OLLAMA_MODEL,
    LLM_PROVIDER_ORDER
)

logger = logging.getLogger("llm_client")

# Fast check to see if Ollama server is alive
_OLLAMA_AVAILABLE = None
_LAST_OLLAMA_CHECK = 0

def is_ollama_alive(host: str) -> bool:
    global _OLLAMA_AVAILABLE, _LAST_OLLAMA_CHECK
    now = time.time()
    if _OLLAMA_AVAILABLE is not None and (now - _LAST_OLLAMA_CHECK < 60):
        return _OLLAMA_AVAILABLE
    try:
        with httpx.Client(timeout=0.4) as client:
            r = client.get(f"{host.rstrip('/')}/api/tags")
            _OLLAMA_AVAILABLE = (r.status_code == 200)
    except Exception:
        _OLLAMA_AVAILABLE = False
    _LAST_OLLAMA_CHECK = now
    return _OLLAMA_AVAILABLE

class LLMClient:
    def __init__(self):
        self.groq_api_key = GROQ_API_KEY
        self.gemini_api_key = GEMINI_API_KEY
        self.ollama_host = OLLAMA_HOST
        self.provider_order = LLM_PROVIDER_ORDER

        self._groq_client = None
        self._gemini_initialized = False

    def _get_groq_client(self):
        if self._groq_client is None and self.groq_api_key:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=self.groq_api_key)
            except ImportError:
                logger.warning("groq library not installed.")
        return self._groq_client

    def _init_gemini(self):
        if not self._gemini_initialized and self.gemini_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_api_key)
                self._gemini_initialized = True
            except ImportError:
                logger.warning("google-generativeai library not installed.")

    def _call_ollama(self, prompt: str, model: Optional[str] = None, temperature: float = 0.2) -> str:
        if not is_ollama_alive(self.ollama_host):
            raise ConnectionError(f"Ollama server not reachable at {self.ollama_host}")
        
        model_name = model if (model and not "/" in model) else OLLAMA_MODEL
        url = f"{self.ollama_host.rstrip('/')}/api/generate"
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature}
        }
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()

    def _call_groq(self, prompt: str, model: Optional[str] = None, temperature: float = 0.2, max_tokens: int = 1500) -> str:
        groq_client = self._get_groq_client()
        if not groq_client:
            raise RuntimeError("Groq API key or client is not available.")
        
        # Select active Groq model
        model_name = "qwen/qwen3.6-27b"
        if model and any(k in model for k in ["gpt-oss", "qwen/qwen", "compound"]):
            model_name = model

        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "user", "content": prompt}
            ],
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )
        content = chat_completion.choices[0].message.content or ""
        # Strip reasoning tags if present (both closed and unclosed)
        import re
        content = re.sub(r"<think>[\s\S]*?(?:</think>|$)", "", content).strip()
        return content

    def _call_gemini(self, prompt: str, model: Optional[str] = None, temperature: float = 0.2) -> str:
        self._init_gemini()
        if not self.gemini_api_key:
            raise RuntimeError("Gemini API key is not configured.")
        
        import google.generativeai as genai
        models_to_try = ["gemini-3.5-flash-lite", "gemini-3.6-flash"]
        if model and "gemini" in model.lower():
            models_to_try.insert(0, model)

        for m_name in models_to_try:
            try:
                gen_model = genai.GenerativeModel(m_name)
                response = gen_model.generate_content(
                    prompt,
                    generation_config={"temperature": temperature}
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                logger.warning(f"Gemini model {m_name} failed: {e}")
                continue

        raise RuntimeError("All configured Gemini models failed.")

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        preferred_provider: Optional[str] = None,
        temperature: float = 0.2
    ) -> str:
        """
        Executes prompt with fallback priority:
        1. Preferred provider (if given) -> 2. Ollama (if running) -> 3. Groq -> 4. Gemini
        """
        providers = list(self.provider_order)
        if preferred_provider and preferred_provider in providers:
            providers.remove(preferred_provider)
            providers.insert(0, preferred_provider)

        errors = []
        for provider in providers:
            try:
                if provider == "ollama":
                    if not is_ollama_alive(self.ollama_host):
                        continue
                    return self._call_ollama(prompt, model=model, temperature=temperature)
                elif provider == "groq":
                    return self._call_groq(prompt, model=model, temperature=temperature)
                elif provider == "gemini":
                    return self._call_gemini(prompt, model=model, temperature=temperature)
            except Exception as exc:
                err_msg = f"Provider '{provider}' failed: {exc}"
                errors.append(err_msg)

        raise RuntimeError(f"All LLM providers failed. Errors: {'; '.join(errors)}")

    def generate_json(
        self,
        prompt: str,
        model: Optional[str] = None,
        preferred_provider: Optional[str] = None,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """
        Executes prompt and guarantees parsed JSON dict output.
        """
        raw_text = self.generate(
            prompt=prompt,
            model=model,
            preferred_provider=preferred_provider,
            temperature=temperature
        )
        
        import re

        # Strategy 1: Look for markdown json fence ```json { ... } ```
        fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", raw_text)
        if fence_match:
            try:
                return json.loads(fence_match.group(1).strip())
            except Exception:
                pass

        # Strategy 2: Strip closed think blocks
        clean_text = re.sub(r"<think>[\s\S]*?</think>", "", raw_text).strip()

        # Strategy 3: Direct JSON load after stripping fences
        stripped = clean_text
        if stripped.startswith("```json"):
            stripped = stripped[7:]
        elif stripped.startswith("```"):
            stripped = stripped[3:]
        if stripped.endswith("```"):
            stripped = stripped[:-3]
        stripped = stripped.strip()

        try:
            return json.loads(stripped)
        except Exception:
            pass

        # Strategy 4: Find outermost JSON object in clean_text or raw_text
        for target in [stripped, clean_text, raw_text]:
            match = re.search(r"(\{[\s\S]*\})", target)
            if match:
                json_str = match.group(1).strip()
                try:
                    return json.loads(json_str)
                except Exception:
                    # Attempt to fix trailing commas or partial closures
                    try:
                        fixed = re.sub(r",\s*([\}\]])", r"\1", json_str)
                        return json.loads(fixed)
                    except Exception:
                        pass

        # Strategy 5: If plain text returned, wrap gracefully
        if stripped:
            return {"draft_reply": stripped, "intent": "other_unclear", "confidence": 0.5}
        elif raw_text:
            cleaned_raw = re.sub(r"<think>[\s\S]*?(?:</think>|$)", "", raw_text).strip()
            if cleaned_raw:
                return {"draft_reply": cleaned_raw, "intent": "other_unclear", "confidence": 0.5}

        raise ValueError(f"Could not parse valid JSON from LLM output: {raw_text[:200]}")

llm_client = LLMClient()
