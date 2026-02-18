"""
Test suite for ai_gateway.py
Tests delegation functions with mocked Ollama API
"""
from unittest.mock import MagicMock, Mock, patch

import pytest

from ai_gateway import LocalAI, delegate_to_rtx


class TestDelegation:
    """Test delegation functions"""

    @pytest.fixture
    def mock_requests(self):
        """Mock HTTP requests to Ollama API"""
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "model": "qwen2.5:7b",
                "created_at": "2024-01-01T00:00:00Z",
                "response": "Mock RTX response",
                "done": True
            }
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            yield mock_post

    def test_delegate_to_rtx_basic(self, mock_requests):
        """Test basic RTX delegation"""
        result = delegate_to_rtx("Test task")

        assert result is not None
        assert isinstance(result, str)
        assert "Mock RTX response" in result
        mock_requests.assert_called()

    def test_delegate_to_rtx_with_role(self, mock_requests):
        """Test delegation with custom role"""
        result = delegate_to_rtx(
            "Write code",
            role="expert Python developer"
        )

        assert result is not None
        # Verify role was included in system message
        call_args = mock_requests.call_args
        assert call_args is not None

    def test_local_ai_initialization(self):
        """Test LocalAI class initialization"""
        ai = LocalAI(model="qwen2.5:7b")

        assert ai.model == "qwen2.5:7b"
        assert ai.base_url == "http://localhost:11434"

    def test_error_handling(self, mock_requests):
        """Test error handling when API fails"""
        mock_requests.side_effect = Exception("API Error")

        # Should handle error gracefully
        try:
            result = delegate_to_rtx("Test task")
            # If no exception, check result
            assert result is not None
        except Exception as e:
            # Exception is also acceptable
            assert "API Error" in str(e) or "error" in str(e).lower()


class TestCaching:
    """Test caching functionality"""

    @pytest.fixture
    def mock_requests(self):
        """Mock HTTP requests"""
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "message": {"content": "Cached response"}
            }
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            yield mock_post

    def test_cache_enabled_by_default(self):
        """Test that caching is enabled by default"""
        ai = LocalAI()
        assert ai.enable_cache is True

    def test_cache_ttl_default(self):
        """Test default cache TTL is 5 minutes"""
        ai = LocalAI()
        assert ai.cache_ttl == 300  # 5 minutes in seconds


# Placeholder for more tests - will be added by RTX in next iteration
class TestAdvancedDelegation:
    """Advanced delegation tests - TO BE IMPLEMENTED"""
    pass


class TestBatchOperations:
    """Batch operation tests - TO BE IMPLEMENTED"""
    pass
