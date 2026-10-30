"""
tests/test_llm_regex_audit_client.py

Focused unit tests for the local Ollama client (analysis.llm_regex_audit.client).
Uses mocked HTTP responses to guarantee tests run reliably in offline CI/local environments
without requiring Ollama to be running or models to be installed.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest
import requests

from analysis.llm_regex_audit.client import (
    get_local_models,
    is_ollama_running,
    request_candidate_proposals,
)


@pytest.fixture
def dummy_prompt():
    return {
        "system_instruction": "You are a regex auditor.",
        "user_prompt": json.dumps({"canonical_skill": "R", "samples": []}),
        "target_skill": "R",
        "sample_count": 0,
    }


def test_is_ollama_running_success():
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        assert is_ollama_running() is True


def test_is_ollama_running_failure():
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError):
        assert is_ollama_running() is False


def test_get_local_models():
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "models": [{"name": "qwen3:4b", "size": 2500000000}]
        }
        models = get_local_models()
        assert len(models) == 1
        assert models[0]["name"] == "qwen3:4b"


def test_request_candidate_proposals_success_single(dummy_prompt):
    valid_candidate = {
        "canonical_skill": "R",
        "proposed_regex": r"\b[Rr]\s*programming\b",
        "proposed_aliases": ["r-lang"],
        "explanation": "Matches explicit R programming.",
        "positive_test_cases": ["R programming"],
        "negative_test_cases": ["R&D"],
        "false_positive_risks": [],
        "confidence_score": 0.95,
        "human_review_required": [],
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "message": {"content": json.dumps(valid_candidate)},
        "prompt_eval_count": 120,
        "eval_count": 45,
    }

    with patch("requests.Session.post", return_value=mock_resp):
        res = request_candidate_proposals(dummy_prompt, model_name="qwen3:4b")
        assert res.success is True
        assert len(res.proposals) == 1
        assert res.proposals[0].canonical_skill == "R"
        assert res.proposals[0].proposed_regex == r"\b[Rr]\s*programming\b"
        assert res.prompt_tokens == 120
        assert res.response_tokens == 45


def test_request_candidate_proposals_multiple_partial_validity(dummy_prompt):
    # One valid candidate, one invalid candidate (missing explanation)
    valid_candidate = {
        "canonical_skill": "R",
        "proposed_regex": r"\b[Rr]\s*programming\b",
        "proposed_aliases": [],
        "explanation": "Valid rule",
        "positive_test_cases": ["R programming"],
        "negative_test_cases": ["R&D"],
        "false_positive_risks": [],
        "confidence_score": 0.9,
        "human_review_required": [],
    }
    invalid_candidate = {
        "canonical_skill": "R",
        "proposed_regex": r"\bR\b",
        # Missing explanation and test cases
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "message": {"content": json.dumps({"candidates": [valid_candidate, invalid_candidate]})},
    }

    with patch("requests.Session.post", return_value=mock_resp):
        res = request_candidate_proposals(dummy_prompt, model_name="qwen3:4b")
        # Partial validity: the valid candidate is accepted, invalid is flagged
        assert res.success is True
        assert len(res.proposals) == 1
        assert len(res.validation_errors) == 1
        assert "Candidate #2 validation failed" in res.validation_errors[0]


def test_request_candidate_proposals_connection_error(dummy_prompt):
    with patch("requests.Session.post", side_effect=requests.exceptions.ConnectionError):
        res = request_candidate_proposals(dummy_prompt, host="http://127.0.0.1:9999")
        assert res.success is False
        assert "not reachable" in res.error.lower()


def test_request_candidate_proposals_timeout(dummy_prompt):
    with patch("requests.Session.post", side_effect=requests.exceptions.Timeout):
        res = request_candidate_proposals(dummy_prompt, timeout=5.0)
        assert res.success is False
        assert "timed out" in res.error.lower()


def test_request_candidate_proposals_model_not_found_404(dummy_prompt):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.text = "model 'nonexistent' not found"

    with patch("requests.Session.post", return_value=mock_resp):
        res = request_candidate_proposals(dummy_prompt, model_name="nonexistent")
        assert res.success is False
        assert "not found" in res.error.lower()


def test_request_candidate_proposals_invalid_json(dummy_prompt):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "message": {"content": "This is plain text, not JSON at all."},
    }

    with patch("requests.Session.post", return_value=mock_resp):
        res = request_candidate_proposals(dummy_prompt)
        assert res.success is False
        assert "not be parsed as valid json" in res.error.lower()


def test_request_candidate_proposals_empty_response(dummy_prompt):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "message": {"content": "   \n\t  "},
    }

    with patch("requests.Session.post", return_value=mock_resp):
        res = request_candidate_proposals(dummy_prompt)
        assert res.success is False
        assert "empty response" in res.error.lower()


def test_request_candidate_proposals_schema_validation_failure(dummy_prompt):
    malformed_candidate = {
        "canonical_skill": "R",
        "proposed_regex": r"\bR\b",
        "explanation": "Rule without tests",
        # Missing positive_test_cases, negative_test_cases, confidence_score
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "message": {"content": json.dumps(malformed_candidate)},
    }

    with patch("requests.Session.post", return_value=mock_resp):
        res = request_candidate_proposals(dummy_prompt)
        assert res.success is False
        assert len(res.proposals) == 0
        assert "validation failed" in res.error.lower()

