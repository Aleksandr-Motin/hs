"""
Unit tests for Aidbox API client.
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from requests.exceptions import Timeout, ConnectionError, RequestException

from src.aidbox_client import AidboxClient, send_to_aidbox, configure_client


class TestAidboxClient:
    """Test cases for AidboxClient class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.base_url = "https://test.aidbox.dev"
        self.auth_token = "test-token-123"
        self.username = "test-user"
        self.password = "test-pass"
    
    def test_init_with_token_parameters(self):
        """Test client initialization with token parameters."""
        client = AidboxClient(self.base_url, auth_token=self.auth_token)
        assert client.base_url == self.base_url
        assert client.auth_token == self.auth_token
        assert client.auth_type == 'token'
        assert client.session is not None
    
    def test_init_with_basic_auth_parameters(self):
        """Test client initialization with basic auth parameters."""
        client = AidboxClient(self.base_url, username=self.username, password=self.password)
        assert client.base_url == self.base_url
        assert client.username == self.username
        assert client.password == self.password
        assert client.auth_type == 'basic'
        assert client.session is not None
    
    def test_init_without_parameters_uses_config_token(self):
        """Test client initialization uses config token when no parameters provided."""
        with patch('src.aidbox_client.config') as mock_config:
            mock_config.aidbox_base_url = "https://config.aidbox.dev"
            mock_config.aidbox_auth_token = "config-token"
            mock_config.aidbox_username = ""
            mock_config.aidbox_password = ""
            
            client = AidboxClient()
            assert client.base_url == "https://config.aidbox.dev"
            assert client.auth_token == "config-token"
            assert client.auth_type == 'token'
    
    def test_init_without_parameters_uses_config_basic(self):
        """Test client initialization uses config basic auth when no parameters provided."""
        with patch('src.aidbox_client.config') as mock_config:
            mock_config.aidbox_base_url = "https://config.aidbox.dev"
            mock_config.aidbox_auth_token = ""
            mock_config.aidbox_username = "config-user"
            mock_config.aidbox_password = "config-pass"
            
            client = AidboxClient()
            assert client.base_url == "https://config.aidbox.dev"
            assert client.username == "config-user"
            assert client.password == "config-pass"
            assert client.auth_type == 'basic'
    
    def test_init_raises_error_for_missing_base_url(self):
        """Test client initialization raises error when base URL is missing."""
        with pytest.raises(ValueError, match="Aidbox base URL is required"):
            AidboxClient("", auth_token=self.auth_token)
    
    def test_init_raises_error_for_missing_auth(self):
        """Test client initialization raises error when no auth is provided."""
        with pytest.raises(ValueError, match="Either auth token or username/password are required"):
            AidboxClient(self.base_url)
    
    def test_create_session_sets_bearer_headers(self):
        """Test session creation sets correct Bearer headers."""
        client = AidboxClient(self.base_url, auth_token=self.auth_token)
        session = client.session
        assert session.headers['Content-Type'] == 'application/json'
        assert session.headers['Authorization'] == f'Bearer {self.auth_token}'
    
    def test_create_session_sets_basic_headers(self):
        """Test session creation sets correct Basic auth headers."""
        import base64
        client = AidboxClient(self.base_url, username=self.username, password=self.password)
        session = client.session
        
        expected_credentials = base64.b64encode(f"{self.username}:{self.password}".encode('utf-8')).decode('utf-8')
        assert session.headers['Content-Type'] == 'application/json'
        assert session.headers['Authorization'] == f'Basic {expected_credentials}'
    
    @patch('src.aidbox_client.log_info')
    @patch('src.aidbox_client.log_success')
    def test_send_to_aidbox_success_200(self, mock_log_success, mock_log_info):
        """Test successful API call with 200 response."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "123", "status": "processed"}
        mock_response.content = b'{"id": "123", "status": "processed"}'
        
        with patch.object(self.client.session, 'post', return_value=mock_response) as mock_post:
            success, response_data = self.client.send_to_aidbox("test content", "test.txt")
            
            assert success is True
            assert response_data == {"id": "123", "status": "processed"}
            
            # Verify API call
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == f"{self.base_url}/file-processor"
            assert call_args[1]['timeout'] == 30
            
            # Verify payload structure
            payload = call_args[1]['json']
            assert payload['filename'] == "test.txt"
            assert payload['content'] == "test content"
            assert payload['source'] == "file-processor"
            assert 'timestamp' in payload
            
            # Verify logging
            mock_log_info.assert_called_with("Sending file test.txt to Aidbox API")
            mock_log_success.assert_called_with("Successfully sent file test.txt to Aidbox. Status: 200")
    
    @patch('src.aidbox_client.log_info')
    @patch('src.aidbox_client.log_success')
    def test_send_to_aidbox_success_201(self, mock_log_success, mock_log_info):
        """Test successful API call with 201 response."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"created": True}
        mock_response.content = b'{"created": True}'
        
        with patch.object(self.client.session, 'post', return_value=mock_response):
            success, response_data = self.client.send_to_aidbox("test content", "test.txt")
            
            assert success is True
            assert response_data == {"created": True}
            mock_log_success.assert_called_with("Successfully sent file test.txt to Aidbox. Status: 201")
    
    @patch('src.aidbox_client.log_info')
    @patch('src.aidbox_client.log_success')
    def test_send_to_aidbox_success_empty_response(self, mock_log_success, mock_log_info):
        """Test successful API call with empty response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b''
        
        with patch.object(self.client.session, 'post', return_value=mock_response):
            success, response_data = self.client.send_to_aidbox("test content", "test.txt")
            
            assert success is True
            assert response_data == {}
    
    @patch('src.aidbox_client.log_info')
    @patch('src.aidbox_client.log_error')
    def test_send_to_aidbox_client_error_400(self, mock_log_error, mock_log_info):
        """Test API call with 400 client error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        
        with patch.object(self.client.session, 'post', return_value=mock_response):
            success, response_data = self.client.send_to_aidbox("test content", "test.txt")
            
            assert success is False
            assert response_data is None
            mock_log_error.assert_called_with(
                "Client error sending file test.txt to Aidbox. Status: 400, Response: Bad Request"
            )
    
    @patch('src.aidbox_client.log_info')
    @patch('src.aidbox_client.log_error')
    def test_send_to_aidbox_client_error_401(self, mock_log_error, mock_log_info):
        """Test API call with 401 authentication error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        with patch.object(self.client.session, 'post', return_value=mock_response):
            success, response_data = self.client.send_to_aidbox("test content", "test.txt")
            
            assert success is False
            assert response_data is None
            mock_log_error.assert_called_with(
                "Client error sending file test.txt to Aidbox. Status: 401, Response: Unauthorized"
            )
    
    @patch('src.aidbox_client.log_info')
    @patch('src.aidbox_client.log_error')
    def test_send_to_aidbox_server_error_500(self, mock_log_error, mock_log_info):
        """Test API call with 500 server error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        with patch.object(self.client.session, 'post', return_value=mock_response):
            success, response_data = self.client.send_to_aidbox("test content", "test.txt")
            
            assert success is False
            assert response_data is None
            mock_log_error.assert_called_with(
                "Server error sending file test.txt to Aidbox. Status: 500, Response: Internal Server Error"
            )
    
    @patch('src.aidbox_client.log_info')
    @patch('src.aidbox_client.log_error')
    def test_send_to_aidbox_timeout_error(self, mock_log_error, mock_log_info):
        """Test API call with timeout error."""
        with patch.object(self.client.session, 'post', side_effect=Timeout("Request timeout")):
            success, response_data = self.client.send_to_aidbox("test content", "test.txt")
            
            assert success is False
            assert response_data is None
            mock_log_error.assert_called_with("Timeout error sending file test.txt to Aidbox")
    
    @patch('src.aidbox_client.log_info')
    @patch('src.aidbox_client.log_error')
    def test_send_to_aidbox_connection_error(self, mock_log_error, mock_log_info):
        """Test API call with connection error."""
        with patch.object(self.client.session, 'post', side_effect=ConnectionError("Connection failed")):
            success, response_data = self.client.send_to_aidbox("test content", "test.txt")
            
            assert success is False
            assert response_data is None
            mock_log_error.assert_called_with(
                "Connection error sending file test.txt to Aidbox: Connection failed"
            )
    
    @patch('src.aidbox_client.log_info')
    @patch('src.aidbox_client.log_error')
    def test_send_to_aidbox_request_exception(self, mock_log_error, mock_log_info):
        """Test API call with general request exception."""
        with patch.object(self.client.session, 'post', side_effect=RequestException("Request failed")):
            success, response_data = self.client.send_to_aidbox("test content", "test.txt")
            
            assert success is False
            assert response_data is None
            mock_log_error.assert_called_with(
                "Request error sending file test.txt to Aidbox: Request failed"
            )
    
    @patch('src.aidbox_client.log_info')
    @patch('src.aidbox_client.log_error')
    def test_send_to_aidbox_json_decode_error(self, mock_log_error, mock_log_info):
        """Test API call with JSON decode error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'invalid json'
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)
        
        with patch.object(self.client.session, 'post', return_value=mock_response):
            success, response_data = self.client.send_to_aidbox("test content", "test.txt")
            
            assert success is False
            assert response_data is None
            mock_log_error.assert_called()
            error_call = mock_log_error.call_args[0][0]
            assert "JSON decode error processing response for file test.txt" in error_call
    
    @patch('src.aidbox_client.log_info')
    @patch('src.aidbox_client.log_error')
    def test_send_to_aidbox_unexpected_error(self, mock_log_error, mock_log_info):
        """Test API call with unexpected error."""
        with patch.object(self.client.session, 'post', side_effect=Exception("Unexpected error")):
            success, response_data = self.client.send_to_aidbox("test content", "test.txt")
            
            assert success is False
            assert response_data is None
            mock_log_error.assert_called_with(
                "Unexpected error sending file test.txt to Aidbox: Unexpected error"
            )
    
    @patch('src.aidbox_client.log_info')
    def test_configure_client(self, mock_log_info):
        """Test client configuration update."""
        new_url = "https://new.aidbox.dev"
        new_token = "new-token-456"
        
        self.client.configure_client(new_url, new_token)
        
        assert self.client.base_url == new_url
        assert self.client.auth_token == new_token
        assert self.client.session.headers['Authorization'] == f'Bearer {new_token}'
        mock_log_info.assert_called_with(f"Aidbox client configured with base URL: {new_url}")
    
    @patch('src.aidbox_client.log_info')
    def test_health_check_success(self, mock_log_info):
        """Test successful health check."""
        mock_response = Mock()
        mock_response.status_code = 200
        
        with patch.object(self.client.session, 'get', return_value=mock_response) as mock_get:
            result = self.client.health_check()
            
            assert result is True
            mock_get.assert_called_once_with(f"{self.base_url}/health", timeout=10)
            mock_log_info.assert_called_with("Aidbox API health check passed")
    
    @patch('src.aidbox_client.log_error')
    def test_health_check_failure(self, mock_log_error):
        """Test failed health check."""
        mock_response = Mock()
        mock_response.status_code = 500
        
        with patch.object(self.client.session, 'get', return_value=mock_response):
            result = self.client.health_check()
            
            assert result is False
            mock_log_error.assert_called_with("Aidbox API health check failed. Status: 500")
    
    @patch('src.aidbox_client.log_error')
    def test_health_check_exception(self, mock_log_error):
        """Test health check with exception."""
        with patch.object(self.client.session, 'get', side_effect=Exception("Network error")):
            result = self.client.health_check()
            
            assert result is False
            mock_log_error.assert_called_with("Aidbox API health check error: Network error")


class TestConvenienceFunctions:
    """Test cases for convenience functions."""
    
    @patch('src.aidbox_client._get_client')
    def test_send_to_aidbox_function(self, mock_get_client):
        """Test send_to_aidbox convenience function."""
        mock_client = Mock()
        mock_client.send_to_aidbox.return_value = (True, {"id": "123"})
        mock_get_client.return_value = mock_client
        
        result = send_to_aidbox("test content", "test.txt")
        
        assert result == (True, {"id": "123"})
        mock_client.send_to_aidbox.assert_called_once_with("test content", "test.txt")
    
    @patch('src.aidbox_client._get_client')
    def test_configure_client_function(self, mock_get_client):
        """Test configure_client convenience function."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        configure_client("https://test.aidbox.dev", "test-token")
        
        mock_client.configure_client.assert_called_once_with("https://test.aidbox.dev", "test-token")


class TestRetryLogic:
    """Test cases for retry logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = AidboxClient("https://test.aidbox.dev", "test-token")
    
    def test_session_has_retry_adapter(self):
        """Test that session has retry adapter configured."""
        # Check that adapters are mounted
        assert 'http://' in self.client.session.adapters
        assert 'https://' in self.client.session.adapters
        
        # Check that adapter has retry configuration
        adapter = self.client.session.adapters['https://']
        assert hasattr(adapter, 'max_retries')