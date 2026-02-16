"""Тесты middleware, включая маскировку чувствительных заголовков."""
import pytest

from lynx_logger.middleware import (
    _sanitize_headers,
    _sanitize_dict,
    _scope_headers_to_dict,
    DEFAULT_SENSITIVE_HEADERS,
    DEFAULT_SENSITIVE_KEYS,
)


class TestSanitizeHeaders:
    """Тесты для _sanitize_headers."""

    def test_masks_authorization(self):
        headers = {"Authorization": "Bearer secret-token-123", "Host": "example.com"}
        result = _sanitize_headers(headers, DEFAULT_SENSITIVE_HEADERS)
        assert result["Authorization"] == "***"
        assert result["Host"] == "example.com"

    def test_masks_cookie(self):
        headers = {"Cookie": "session=abc123", "Accept": "application/json"}
        result = _sanitize_headers(headers, DEFAULT_SENSITIVE_HEADERS)
        assert result["Cookie"] == "***"
        assert result["Accept"] == "application/json"

    def test_masks_case_insensitive(self):
        headers = {"AUTHORIZATION": "Bearer x", "authorization": "Bearer y"}
        result = _sanitize_headers(headers, DEFAULT_SENSITIVE_HEADERS)
        assert result["AUTHORIZATION"] == "***"
        assert result["authorization"] == "***"

    def test_custom_sensitive_headers(self):
        headers = {"X-Custom-Secret": "value123", "Host": "example.com"}
        result = _sanitize_headers(headers, {"x-custom-secret"})
        assert result["X-Custom-Secret"] == "***"
        assert result["Host"] == "example.com"


class TestSanitizeDict:
    """Тесты для _sanitize_dict (form, query, POST)."""

    def test_masks_password(self):
        data = {"username": "admin", "password": "secret123"}
        result = _sanitize_dict(data, DEFAULT_SENSITIVE_KEYS)
        assert result["username"] == "admin"
        assert result["password"] == "***"

    def test_masks_token(self):
        data = {"action": "login", "token": "abc123"}
        result = _sanitize_dict(data, DEFAULT_SENSITIVE_KEYS)
        assert result["action"] == "login"
        assert result["token"] == "***"

    def test_empty_dict(self):
        assert _sanitize_dict({}, DEFAULT_SENSITIVE_KEYS) == {}


class TestScopeHeadersToDict:
    """Тесты для _scope_headers_to_dict (ASGI)."""

    def test_converts_scope_headers(self):
        scope = {
            "headers": [
                (b"host", b"example.com"),
                (b"authorization", b"Bearer xyz"),
            ]
        }
        result = _scope_headers_to_dict(scope)
        assert result["host"] == "example.com"
        assert result["authorization"] == "Bearer xyz"
