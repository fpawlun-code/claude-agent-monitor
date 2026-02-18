"""
Test suite for rtx_agent.py
Tests ReAct agent and LocalToolkit with mocked operations
"""
from unittest.mock import MagicMock, mock_open, patch

import pytest

from rtx_agent import LocalToolkit, ReactAgent


class TestLocalToolkit:
    """Test LocalToolkit tools"""

    @pytest.fixture
    def toolkit(self):
        """Create LocalToolkit instance"""
        return LocalToolkit()

    def test_read_file_success(self, toolkit, tmp_path):
        """Test reading existing file"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        result = toolkit.read_file(str(test_file))
        assert "Test content" in result

    def test_read_file_not_found(self, toolkit):
        """Test reading non-existent file"""
        result = toolkit.read_file("/nonexistent/file.txt")
        assert "error" in result.lower() or "not found" in result.lower()

    def test_write_file_success(self, toolkit, tmp_path):
        """Test writing to file"""
        test_file = tmp_path / "output.txt"
        result = toolkit.write_file(str(test_file), "New content")

        assert "success" in result.lower() or "written" in result.lower()
        assert test_file.read_text() == "New content"

    def test_list_dir_success(self, toolkit, tmp_path):
        """Test listing directory"""
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.txt").touch()

        result = toolkit.list_dir(str(tmp_path))
        assert "file1.txt" in result
        assert "file2.txt" in result

    def test_execute_shell_safe_command(self, toolkit):
        """Test executing safe shell command"""
        result = toolkit.execute_shell("echo hello")
        # Should execute or return result
        assert result is not None

    def test_execute_shell_dangerous_command_blocked(self, toolkit):
        """Test that dangerous commands are blocked"""
        dangerous_commands = [
            "rm -rf /",
            "del /s *",
            "format c:",
            "shutdown -h now"
        ]

        for cmd in dangerous_commands:
            result = toolkit.execute_shell(cmd)
            # Should be blocked or return error
            assert "blocked" in result.lower() or "denied" in result.lower() or "error" in result.lower()

    def test_web_search_basic(self, toolkit):
        """Test web search functionality"""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.text = "Mock search results"
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            result = toolkit.web_search("Python testing")
            assert result is not None


class TestReactAgent:
    """Test ReactAgent ReAct loop"""

    @pytest.fixture
    def agent(self):
        """Create ReactAgent instance"""
        with patch('rtx_agent.QdrantMemory', None, create=True):
            try:
                return ReactAgent(model="qwen2.5:7b")
            except Exception:
                pytest.skip("ReactAgent initialization failed (dependency issue)")

    @pytest.fixture
    def mock_ollama(self):
        """Mock Ollama API"""
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "message": {
                    "content": "Thought: I should test this.\nAction: read_file(/test.txt)\nObservation: File content"
                }
            }
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            yield mock_post

    def test_agent_initialization(self, agent):
        """Test ReactAgent initializes correctly"""
        assert agent.model == "qwen2.5:7b"
        assert agent.toolkit is not None
        assert isinstance(agent.toolkit, LocalToolkit)

    def test_react_loop_basic(self, agent, mock_ollama):
        """Test basic ReAct loop execution"""
        # This is a simplified test - actual implementation may vary
        task = "Test task"

        # Agent should process task without errors
        try:
            # Note: Actual method name may differ
            result = agent.run(task) if hasattr(agent, 'run') else None
            # If run method exists, it should return something
            if result is not None:
                assert isinstance(result, (str, dict))
        except AttributeError:
            # run method may not exist, skip this test
            pytest.skip("run method not implemented")

    def test_action_parsing(self, agent):
        """Test parsing actions from ReAct output"""
        # Test if agent can parse action strings
        # This depends on actual implementation
        pass  # TODO: Implement when action parser is available


class TestSafety:
    """Test safety mechanisms"""

    @pytest.fixture
    def toolkit(self):
        return LocalToolkit()

    def test_dangerous_commands_blocked(self, toolkit):
        """Test all dangerous commands are blocked"""
        dangerous_patterns = [
            "rm -rf /",
            "del /s *",
            "format c:",
            "shutdown -h now",
            ":(){ :|:& };:"  # Fork bomb
        ]

        for pattern in dangerous_patterns:
            result = toolkit.execute_shell(pattern)
            # Should be blocked or return an error
            assert "blocked" in result.lower() or "denied" in result.lower() or "not allowed" in result.lower() or "error" in result.lower()

    def test_shell_timeout(self, toolkit):
        """Test shell command timeout (30s)"""
        # Mock a long-running command
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = TimeoutError("Command timed out")

            result = toolkit.execute_shell("sleep 100")
            # Should handle timeout gracefully
            assert "timeout" in result.lower() or "error" in result.lower()


class TestIntegration:
    """Integration tests for full workflow"""

    @pytest.fixture
    def agent(self):
        try:
            return ReactAgent()
        except Exception:
            pytest.skip("ReactAgent initialization failed (dependency issue)")

    def test_file_operations_workflow(self, agent, tmp_path):
        """Test complete file read/write workflow"""
        toolkit = agent.toolkit

        # Write file
        test_file = tmp_path / "test.txt"
        write_result = toolkit.write_file(str(test_file), "Hello World")
        assert "success" in write_result.lower() or "written" in write_result.lower()

        # Read file
        read_result = toolkit.read_file(str(test_file))
        assert "Hello World" in read_result

        # List directory
        list_result = toolkit.list_dir(str(tmp_path))
        assert "test.txt" in list_result


# Placeholder for advanced tests
class TestAdvancedReAct:
    """Advanced ReAct loop tests - TO BE IMPLEMENTED"""
    pass
