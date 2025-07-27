"""
Unit tests for HL7v2 message handler.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import time

from src.hl7v2_handler import send_hl7v2_message, get_client


class TestHL7v2Handler(unittest.TestCase):
    """Test cases for HL7v2 message handler."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_message = """MSH|^~\\&|TEST|SYSTEM|AIDBOX|TARGET|20250125||ADT^A01|123|P|2.5
EVN||20250125
PID|1||123456789^^^MRN||DOE^JOHN^MIDDLE||19800101|M|||123 MAIN ST^^CITY^ST^12345||555-1234|||S||123456789|123-45-6789"""
        
        self.malformed_message = "MSH|^~\\&|...|PID|1||123||DOE^JOHN|||||"
    
    @patch('src.hl7v2_handler.get_client')
    @patch('src.hl7v2_handler.log_info')
    def test_send_hl7v2_message_success(self, mock_log_info, mock_get_client):
        """Test successful HL7v2 message sending."""
        # Setup mocks
        mock_client = Mock()
        mock_client.post.return_value = (
            True, 
            {
                "id": "test-message-id-123",
                "status": "processed",
                "resourceType": "Hl7v2Message"
            },
            201
        )
        mock_get_client.return_value = mock_client
        
        # Execute
        success, response = send_hl7v2_message(self.test_message, "test-file.txt")
        
        # Verify
        self.assertTrue(success)
        self.assertIsNotNone(response)
        self.assertEqual(response["id"], "test-message-id-123")
        self.assertEqual(response["status"], "processed")
        self.assertEqual(response["http_status_code"], 201)
        
        # Verify logging
        mock_log_info.assert_called_with("[test-file.txt] Sending HL7v2 message to Aidbox")
        
        # Verify client call
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        self.assertEqual(call_args[0][0], "Hl7v2Message")  # endpoint
        payload = call_args[0][1]  # payload
        self.assertEqual(payload["resourceType"], "Hl7v2Message")
        self.assertEqual(payload["status"], "received")
        self.assertIn("MSH|", payload["src"])
    
    @patch('src.hl7v2_handler.get_client')
    @patch('src.hl7v2_handler.log_info')
    def test_send_hl7v2_message_processing_error(self, mock_log_info, mock_get_client):
        """Test HL7v2 message with processing error."""
        # Setup mocks
        mock_client = Mock()
        mock_client.post.return_value = (
            True, 
            {
                "id": "test-error-id-456",
                "status": "error",
                "resourceType": "Hl7v2Message",
                "outcome": ["error", "Exception", "msg", "Parsing failed"]
            },
            201
        )
        mock_get_client.return_value = mock_client
        
        # Execute
        success, response = send_hl7v2_message(self.malformed_message, "error-file.txt")
        
        # Verify
        self.assertFalse(success)
        self.assertIsNotNone(response)
        self.assertEqual(response["id"], "test-error-id-456")
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["http_status_code"], 201)
        
        # Verify logging
        mock_log_info.assert_called_with("[error-file.txt] Sending HL7v2 message to Aidbox")
    
    @patch('src.hl7v2_handler.get_client')
    @patch('src.hl7v2_handler.log_info')
    def test_send_hl7v2_message_without_filename(self, mock_log_info, mock_get_client):
        """Test HL7v2 message sending without filename prefix."""
        # Setup mocks
        mock_client = Mock()
        mock_client.post.return_value = (
            True, 
            {
                "id": "test-no-filename-789",
                "status": "processed",
                "resourceType": "Hl7v2Message"
            },
            201
        )
        mock_get_client.return_value = mock_client
        
        # Execute
        success, response = send_hl7v2_message(self.test_message)
        
        # Verify
        self.assertTrue(success)
        
        # Verify logging without filename prefix
        mock_log_info.assert_called_with("Sending HL7v2 message to Aidbox")
    
    @patch('src.hl7v2_handler.get_client')
    @patch('src.hl7v2_handler.log_info')
    @patch('src.hl7v2_handler.log_error')
    @patch('time.sleep')
    def test_send_hl7v2_message_retry_logic(self, mock_sleep, mock_log_error, mock_log_info, mock_get_client):
        """Test retry logic for failed HTTP requests."""
        # Setup mocks
        mock_client = Mock()
        # First two attempts fail, third succeeds
        mock_client.post.side_effect = [
            (False, None, 404),  # First attempt fails
            (False, None, 404),  # Second attempt fails
            (True, {"id": "retry-success-123", "status": "processed"}, 201)  # Third succeeds
        ]
        mock_get_client.return_value = mock_client
        
        # Execute
        success, response = send_hl7v2_message(self.test_message, "retry-test.txt", max_retries=2)
        
        # Verify
        self.assertTrue(success)
        self.assertEqual(response["id"], "retry-success-123")
        
        # Verify retry attempts were logged
        expected_retry_calls = [
            "[retry-test.txt] HL7v2 message send failed (attempt 1/3), retrying in 1 seconds...",
            "[retry-test.txt] HL7v2 message send failed (attempt 2/3), retrying in 2 seconds..."
        ]
        
        # Check that retry logs were called
        retry_calls = [call for call in mock_log_info.call_args_list if "retrying in" in str(call)]
        self.assertEqual(len(retry_calls), 2)
        
        # Verify sleep was called with exponential backoff
        mock_sleep.assert_any_call(1)  # First retry: 1 second
        mock_sleep.assert_any_call(2)  # Second retry: 2 seconds
        
        # Verify client was called 3 times
        self.assertEqual(mock_client.post.call_count, 3)
    
    @patch('src.hl7v2_handler.get_client')
    @patch('src.hl7v2_handler.log_info')
    @patch('src.hl7v2_handler.log_error')
    @patch('time.sleep')
    def test_send_hl7v2_message_all_retries_fail(self, mock_sleep, mock_log_error, mock_log_info, mock_get_client):
        """Test when all retry attempts fail."""
        # Setup mocks
        mock_client = Mock()
        mock_client.post.return_value = (False, None, 500)  # All attempts fail
        mock_get_client.return_value = mock_client
        
        # Execute
        success, response = send_hl7v2_message(self.test_message, "fail-test.txt", max_retries=2)
        
        # Verify
        self.assertFalse(success)
        self.assertIsNotNone(response)
        self.assertEqual(response["http_status_code"], 500)
        self.assertEqual(response["error_message"], "Failed to send HL7v2 message after 3 attempts")
        self.assertTrue(response["final_attempt"])
        
        # Verify final error was logged
        mock_log_error.assert_called_with("[fail-test.txt] HL7v2 message send failed after 3 attempts")
        
        # Verify all retry attempts were made
        self.assertEqual(mock_client.post.call_count, 3)
        
        # Verify sleep was called for retries
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)
    
    @patch('src.hl7v2_handler.get_client')
    @patch('src.hl7v2_handler.log_info')
    def test_send_hl7v2_message_unknown_status(self, mock_log_info, mock_get_client):
        """Test HL7v2 message with unknown processing status."""
        # Setup mocks
        mock_client = Mock()
        mock_client.post.return_value = (
            True, 
            {
                "id": "unknown-status-999",
                "status": "pending",  # Unknown status
                "resourceType": "Hl7v2Message"
            },
            201
        )
        mock_get_client.return_value = mock_client
        
        # Execute
        success, response = send_hl7v2_message(self.test_message, "unknown-status.txt")
        
        # Verify
        self.assertFalse(success)  # Unknown status should be treated as failure
        self.assertIsNotNone(response)
        self.assertEqual(response["status"], "pending")
        self.assertEqual(response["http_status_code"], 201)


class TestGetClient(unittest.TestCase):
    """Test cases for get_client function."""
    
    @patch('src.hl7v2_handler.AidboxClient')
    @patch('src.hl7v2_handler.config')
    def test_get_client_creates_singleton(self, mock_config, mock_aidbox_client_class):
        """Test that get_client creates a singleton instance."""
        # Setup mocks
        mock_client_instance = Mock()
        mock_aidbox_client_class.return_value = mock_client_instance
        
        # Execute multiple calls
        client1 = get_client()
        client2 = get_client()
        
        # Verify
        self.assertIs(client1, client2)  # Same instance
        mock_aidbox_client_class.assert_called_once_with(mock_config)  # Only created once
    
    def tearDown(self):
        """Clean up after each test."""
        # Reset the global client instance
        import src.hl7v2_handler
        src.hl7v2_handler._aidbox_client = None


class TestIntegrationScenarios(unittest.TestCase):
    """Integration test scenarios for common use cases."""
    
    @patch('src.hl7v2_handler.get_client')
    @patch('src.hl7v2_handler.log_info')
    def test_successful_file_processing_flow(self, mock_log_info, mock_get_client):
        """Test complete successful file processing flow."""
        # Setup mocks
        mock_client = Mock()
        mock_client.post.return_value = (
            True, 
            {
                "id": "integration-test-123",
                "status": "processed",
                "resourceType": "Hl7v2Message",
                "parsed": {"msg": {"MSH": {"id": "123"}}}
            },
            201
        )
        mock_get_client.return_value = mock_client
        
        # Test message
        test_message = """MSH|^~\\&|EMR|HOSPITAL|AIDBOX|SYSTEM|20250126||ADT^A01|MSG123|P|2.5
EVN||20250126
PID|1||PATIENT123^^^MRN||INTEGRATION^TEST^PATIENT||19900101|M|||123 TEST ST^^TESTCITY^TS^12345||555-1234|||S||PATIENT123|123-45-6789"""
        
        # Execute
        success, response = send_hl7v2_message(test_message, "integration-test.hl7")
        
        # Verify
        self.assertTrue(success)
        self.assertEqual(response["id"], "integration-test-123")
        self.assertEqual(response["status"], "processed")
        self.assertEqual(response["http_status_code"], 201)
        
        # Verify the message was properly formatted
        call_args = mock_client.post.call_args
        payload = call_args[0][1]
        self.assertEqual(payload["resourceType"], "Hl7v2Message")
        self.assertEqual(payload["status"], "received")
        self.assertIn("MSH|", payload["src"])
        self.assertIn("INTEGRATION^TEST^PATIENT", payload["src"])
    
    @patch('src.hl7v2_handler.get_client')
    @patch('src.hl7v2_handler.log_info')
    @patch('src.hl7v2_handler.log_error')
    @patch('time.sleep')
    def test_network_failure_recovery_flow(self, mock_sleep, mock_log_error, mock_log_info, mock_get_client):
        """Test network failure and recovery flow."""
        # Setup mocks - network fails twice, then succeeds
        mock_client = Mock()
        mock_client.post.side_effect = [
            (False, None, None),  # Network error (no status code)
            (False, None, 503),   # Server error
            (True, {"id": "recovery-123", "status": "processed"}, 201)  # Success
        ]
        mock_get_client.return_value = mock_client
        
        # Execute
        success, response = send_hl7v2_message(
            "MSH|^~\\&|TEST|SYS|AIDBOX|TGT|20250126||ADT^A01|REC123|P|2.5",
            "network-recovery.hl7",
            max_retries=2
        )
        
        # Verify
        self.assertTrue(success)
        self.assertEqual(response["id"], "recovery-123")
        
        # Verify retry behavior
        self.assertEqual(mock_client.post.call_count, 3)
        mock_sleep.assert_any_call(1)  # First retry delay
        mock_sleep.assert_any_call(2)  # Second retry delay


if __name__ == '__main__':
    unittest.main()