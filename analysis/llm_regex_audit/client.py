"""
analysis/llm_regex_audit/client.py

Minimal local Ollama client for structured regular expression discovery.
Strictly local inference with zero external network transmission.
Enforces schema validation and isolated candidate parsing.
"""

from __future__ import annotations

import copy
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

from .models import CandidateProposal
from .schema import CANDIDATE_OUTPUT_JSON_SCHEMA, validate_candidate_dict


DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3:4b"


@dataclass
class OllamaClientResult:
    """Structured result returned by local model client."""
    success: bool
    proposals: List[CandidateProposal] = field(default_factory=list)
    raw_response: Optional[str] = None
    parsed_json: Optional[Any] = None
    validation_errors: List[str] = field(default_factory=list)
    error: Optional[str] = None
    model_name: str = ""
    inference_duration_sec: float = 0.0
    prompt_tokens: Optional[int] = None
    response_tokens: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "proposals_count": len(self.proposals),
            "proposals": [p.to_dict() for p in self.proposals],
            "validation_errors": self.validation_errors,
            "error": self.error,
            "model_name": self.model_name,
            "inference_duration_sec": round(self.inference_duration_sec, 3),
            "prompt_tokens": self.prompt_tokens,
            "response_tokens": self.response_tokens,
        }


def is_ollama_running(host: str = DEFAULT_OLLAMA_HOST) -> bool:
    """Checks whether the local Ollama HTTP service is accessible."""
    try:
        resp = requests.get(f"{host.rstrip('/')}/api/tags", timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False


def get_local_models(host: str = DEFAULT_OLLAMA_HOST) -> List[Dict[str, Any]]:
    """Retrieves list of installed local models from Ollama."""
    try:
        resp = requests.get(f"{host.rstrip('/')}/api/tags", timeout=3.0)
        if resp.status_code == 200:
            return resp.json().get("models", [])
        return []
    except Exception:
        return []


def get_model_details(model_name: str, host: str = DEFAULT_OLLAMA_HOST) -> Dict[str, Any]:
    """Retrieves technical details (quantization, context size, architecture) for a model."""
    try:
        resp = requests.post(
            f"{host.rstrip('/')}/api/show",
            json={"name": model_name},
            timeout=5.0,
        )
        if resp.status_code == 200:
            return resp.json()
        return {}
    except Exception:
        return {}


def request_candidate_proposals(
    prompt_package: Dict[str, Any],
    *,
    model_name: str = DEFAULT_MODEL,
    host: str = DEFAULT_OLLAMA_HOST,
    timeout: float = 180.0,
    temperature: float = 0.0,
    seed: int = 42,
    session: Optional[requests.Session] = None,
) -> OllamaClientResult:
    """
    Submits a structured discovery prompt to the local Ollama instance and
    validates candidate output against CANDIDATE_OUTPUT_JSON_SCHEMA.

    Handles:
    - Ollama service unavailable
    - Model not installed / loaded
    - Request timeout
    - Malformed JSON responses
    - Partial candidate invalidity (independent candidate validation)
    """
    start_time = time.perf_counter()
    http = session or requests.Session()

    system_instruction = prompt_package.get("system_instruction", "")
    user_prompt = prompt_package.get("user_prompt", "")
    target_skill = prompt_package.get("target_skill")

    schema_payload = copy.deepcopy(CANDIDATE_OUTPUT_JSON_SCHEMA)
    if target_skill:
        schema_payload["properties"]["canonical_skill"]["enum"] = [target_skill]

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt},
        ],
        "format": schema_payload,
        "stream": False,
        "think": False,
        "options": {
            "temperature": temperature,
            "seed": seed,
            "num_ctx": 8192,
        },
    }

    try:
        endpoint = f"{host.rstrip('/')}/api/chat"
        response = http.post(endpoint, json=payload, timeout=timeout)
    except requests.exceptions.ConnectionError:
        return OllamaClientResult(
            success=False,
            error=f"Local Ollama service is not reachable at {host}. Ensure 'ollama serve' is running.",
            model_name=model_name,
            inference_duration_sec=time.perf_counter() - start_time,
        )
    except requests.exceptions.Timeout:
        return OllamaClientResult(
            success=False,
            error=f"Local Ollama request timed out after {timeout:.1f}s while processing model {model_name}.",
            model_name=model_name,
            inference_duration_sec=time.perf_counter() - start_time,
        )
    except Exception as exc:
        return OllamaClientResult(
            success=False,
            error=f"Unexpected error communicating with local Ollama: {exc}",
            model_name=model_name,
            inference_duration_sec=time.perf_counter() - start_time,
        )

    duration = time.perf_counter() - start_time

    if response.status_code == 404:
        return OllamaClientResult(
            success=False,
            error=f"Model {model_name!r} not found in local Ollama. Install it via 'ollama pull {model_name}'.",
            model_name=model_name,
            inference_duration_sec=duration,
        )
    elif response.status_code != 200:
        return OllamaClientResult(
            success=False,
            error=f"Local Ollama API returned HTTP status {response.status_code}: {response.text[:300]}",
            model_name=model_name,
            inference_duration_sec=duration,
        )

    # Parse response JSON
    try:
        resp_data = response.json()
    except Exception as exc:
        return OllamaClientResult(
            success=False,
            error=f"Failed to parse Ollama HTTP response as JSON: {exc}",
            raw_response=response.text,
            model_name=model_name,
            inference_duration_sec=duration,
        )

    # Extract message content
    message = resp_data.get("message", {})
    raw_content = message.get("content", "").strip()
    if raw_content.startswith("```"):
        lines = raw_content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw_content = "\n".join(lines).strip()

    if not raw_content:
        return OllamaClientResult(
            success=False,
            error="Local model returned an empty response string.",
            model_name=model_name,
            inference_duration_sec=duration,
            prompt_tokens=resp_data.get("prompt_eval_count"),
            response_tokens=resp_data.get("eval_count"),
        )

    # Parse model content as JSON
    try:
        parsed_obj = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        return OllamaClientResult(
            success=False,
            error=f"Model output could not be parsed as valid JSON: {exc}",
            raw_response=raw_content,
            model_name=model_name,
            inference_duration_sec=duration,
            prompt_tokens=resp_data.get("prompt_eval_count"),
            response_tokens=resp_data.get("eval_count"),
        )

    # Extract candidate candidates: handle single dict, list of dicts, or wrapped dict
    candidate_items: List[Dict[str, Any]] = []
    if isinstance(parsed_obj, dict):
        if "candidates" in parsed_obj and isinstance(parsed_obj["candidates"], list):
            candidate_items = [c for c in parsed_obj["candidates"] if isinstance(c, dict)]
        elif "proposed_regex" in parsed_obj:
            candidate_items = [parsed_obj]
        else:
            return OllamaClientResult(
                success=False,
                error="Model output JSON is an object without 'proposed_regex' or 'candidates' array.",
                raw_response=raw_content,
                parsed_json=parsed_obj,
                model_name=model_name,
                inference_duration_sec=duration,
            )
    elif isinstance(parsed_obj, list):
        candidate_items = [c for c in parsed_obj if isinstance(c, dict)]
    else:
        return OllamaClientResult(
            success=False,
            error=f"Model output root must be a JSON object or array, got {type(parsed_obj).__name__}.",
            raw_response=raw_content,
            parsed_json=parsed_obj,
            model_name=model_name,
            inference_duration_sec=duration,
        )

    if not candidate_items:
        return OllamaClientResult(
            success=False,
            error="No candidate proposals identified in model output.",
            raw_response=raw_content,
            parsed_json=parsed_obj,
            model_name=model_name,
            inference_duration_sec=duration,
        )

    # Independent candidate validation
    valid_proposals: List[CandidateProposal] = []
    validation_errors: List[str] = []

    for idx, cand_dict in enumerate(candidate_items):
        is_valid, errors, proposal = validate_candidate_dict(cand_dict)
        if is_valid and proposal:
            valid_proposals.append(proposal)
        else:
            validation_errors.append(f"Candidate #{idx + 1} validation failed: {'; '.join(errors)}")

    success = len(valid_proposals) > 0
    err_msg = None if success else f"All {len(candidate_items)} candidates failed validation: {'; '.join(validation_errors)}"

    return OllamaClientResult(
        success=success,
        proposals=valid_proposals,
        raw_response=raw_content,
        parsed_json=parsed_obj,
        validation_errors=validation_errors,
        error=err_msg,
        model_name=model_name,
        inference_duration_sec=duration,
        prompt_tokens=resp_data.get("prompt_eval_count"),
        response_tokens=resp_data.get("eval_count"),
    )

