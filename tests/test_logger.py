"""
Unit tests for the logger module.
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import logging
from datetime import datetime

from src.logger import (
    FileProcessorLogger,
    setup_logger,
    get_logger,
    log_info,
    log_error,
    log_warning,
    log_success
)


class TestFileProcessorLogger(unittest.TestCase):
    """Test cases for FileProcessorLogger class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file_path = os.path.join(self.temp_dir, "test.log")
        self.logger = FileProcessorLogger(self.log_file_path, max_bytes=1024, backup_count=2)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up log files and directories
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_logger_initialization(self):
        """Test logger initialization and configuration."""
        self.assertEqual(self.logger.log_file_path, self.log_file_path)
        self.assertEqual(self.logger.logger.name, 'file_processor')
        self.assertEqual(self.logger.logger.level, logging.DEBUG)
        self.assertEqual(len(self.logger.logger.handlers), 1)
        
        # Check handler configuration
        handler = self.logger.logger.handlers[0]
        self.assertIsInstance(handler, logging.handlers.RotatingFileHandler)
        self.assertEqual(handler.maxBytes, 1024)
        self.assertEqual(handler.backupCount, 2)
    
    def test_log_info(self):
        """Test info logging functionality."""
        test_message = "Test info message"
        self.logger.log_info(test_message)
        
        # Check log file was created and contains the message
        self.assertTrue(os.path.exists(self.log_file_path))
        with open(self.log_file_path, 'r') as f:
            log_content = f.read()
            self.assertIn("INFO", log_content)
            self.assertIn(test_message, log_content)
            # Check timestamp format
            self.assertRegex(log_content, r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')
    
    def test_log_error_without_exception(self):
        """Test error logging without exception."""
        test_message = "Test error message"
        self.logger.log_error(test_message)
        
        with open(self.log_file_path, 'r') as f:
            log_content = f.read()
            self.assertIn("ERROR", log_content)
            self.assertIn(test_message, log_content)
    
    def test_log_error_with_exception(self):
        """Test error logging with exception."""
        test_message = "Test error with exception"
        test_exception = ValueError("Test exception")
        
        self.logger.log_error(test_message, test_exception)
        
        with open(self.log_file_path, 'r') as f:
            log_content = f.read()
            self.assertIn("ERROR", log_content)
            self.assertIn(test_message, log_content)
            self.assertIn("ValueError", log_content)
            self.assertIn("Test exception", log_content)
    
    def test_log_warning(self):
        """Test warning logging functionality."""
        test_message = "Test warning message"
        self.logger.log_warning(test_message)
        
        with open(self.log_file_path, 'r') as f:
            log_content = f.read()
            self.assertIn("WARNING", log_content)
            self.assertIn(test_message, log_content)
    
    def test_log_success(self):
        """Test success logging functionality."""
        test_message = "Test success message"
        self.logger.log_success(test_message)
        
        with open(self.log_file_path, 'r') as f:
            log_content = f.read()
            self.assertIn("INFO", log_content)
            self.assertIn("SUCCESS:", log_content)
            self.assertIn(test_message, log_content)
    
    def test_log_rotation(self):
        """Test log rotation functionality."""
        # Write enough data to trigger rotation
        large_message = "x" * 500  # 500 characters
        
        # Write multiple messages to exceed max_bytes (1024)
        for i in range(5):
            self.logger.log_info(f"{large_message} - Message {i}")
        
        # Check that rotation occurred
        log_files = [f for f in os.listdir(self.temp_dir) if f.startswith("test.log")]
        self.assertGreater(len(log_files), 1)  # Should have main log + rotated files
    
    def test_log_directory_creation(self):
        """Test that log directory is created if it doesn't exist."""
        nested_log_path = os.path.join(self.temp_dir, "logs", "nested.log")
        logger = FileProcessorLogger(nested_log_path)
        
        logger.log_info("Test message")
        
        self.assertTrue(os.path.exists(nested_log_path))
        self.assertTrue(os.path.isdir(os.path.dirname(nested_log_path)))
    
    @patch('builtins.print')
    def test_logging_failure_fallback(self, mock_print):
        """Test fallback to console when logging fails."""
        # Create logger with invalid path to trigger failure
        with patch.object(logging.handlers.RotatingFileHandler, 'emit', side_effect=Exception("Logging failed")):
            logger = FileProcessorLogger(self.log_file_path)
            logger.log_info("Test message")
            
            # Check that fallback print was called
            mock_print.assert_called()
            call_args = [str(call) for call in mock_print.call_args_list]
            self.assertTrue(any("[INFO]" in arg and "Test message" in arg for arg in call_args))


class TestGlobalLoggerFunctions(unittest.TestCase):
    """Test cases for global logger functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file_path = os.path.join(self.temp_dir, "global_test.log")
        
        # Reset global logger instance
        import src.logger
        src.logger._logger_instance = None
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up log files and directories
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        
        # Clean up default log file if created
        if os.path.exists("file_processor.log"):
            os.remove("file_processor.log")
        
        # Reset global logger instance
        import src.logger
        src.logger._logger_instance = None
    
    def test_setup_logger(self):
        """Test setup_logger function."""
        logger = setup_logger(self.log_file_path, max_bytes=2048, backup_count=3)
        
        self.assertIsInstance(logger, FileProcessorLogger)
        self.assertEqual(logger.log_file_path, self.log_file_path)
        
        # Test that subsequent calls return the same instance
        logger2 = get_logger()
        self.assertIs(logger, logger2)
    
    def test_get_logger_creates_default(self):
        """Test that get_logger creates default logger if none exists."""
        logger = get_logger()
        
        self.assertIsInstance(logger, FileProcessorLogger)
        self.assertEqual(logger.log_file_path, "file_processor.log")
    
    def test_convenience_functions(self):
        """Test convenience logging functions."""
        setup_logger(self.log_file_path)
        
        # Test all convenience functions
        log_info("Info message")
        log_error("Error message")
        log_warning("Warning message")
        log_success("Success message")
        
        # Check log file contains all messages
        with open(self.log_file_path, 'r') as f:
            log_content = f.read()
            self.assertIn("Info message", log_content)
            self.assertIn("Error message", log_content)
            self.assertIn("Warning message", log_content)
            self.assertIn("Success message", log_content)
            self.assertIn("INFO", log_content)
            self.assertIn("ERROR", log_content)
            self.assertIn("WARNING", log_content)
            self.assertIn("SUCCESS:", log_content)
    
    def test_log_error_convenience_with_exception(self):
        """Test log_error convenience function with exception."""
        setup_logger(self.log_file_path)
        
        test_exception = RuntimeError("Test runtime error")
        log_error("Error with exception", test_exception)
        
        with open(self.log_file_path, 'r') as f:
            log_content = f.read()
            self.assertIn("Error with exception", log_content)
            self.assertIn("RuntimeError", log_content)
            self.assertIn("Test runtime error", log_content)


class TestLoggerIntegration(unittest.TestCase):
    """Integration tests for logger functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file_path = os.path.join(self.temp_dir, "integration_test.log")
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up log files and directories
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_concurrent_logging(self):
        """Test that logger handles multiple log calls correctly."""
        logger = FileProcessorLogger(self.log_file_path)
        
        # Log multiple messages of different types
        messages = [
            ("info", "Processing started"),
            ("error", "File not found"),
            ("warning", "Low disk space"),
            ("success", "File processed successfully"),
            ("info", "Processing completed")
        ]
        
        for log_type, message in messages:
            if log_type == "info":
                logger.log_info(message)
            elif log_type == "error":
                logger.log_error(message)
            elif log_type == "warning":
                logger.log_warning(message)
            elif log_type == "success":
                logger.log_success(message)
        
        # Verify all messages are in the log file
        with open(self.log_file_path, 'r') as f:
            log_content = f.read()
            for _, message in messages:
                self.assertIn(message, log_content)
        
        # Count log entries
        log_lines = log_content.strip().split('\n')
        self.assertEqual(len(log_lines), len(messages))
    
    def test_timestamp_format_consistency(self):
        """Test that all log entries have consistent timestamp format."""
        logger = FileProcessorLogger(self.log_file_path)
        
        logger.log_info("Test message 1")
        logger.log_error("Test message 2")
        logger.log_warning("Test message 3")
        logger.log_success("Test message 4")
        
        with open(self.log_file_path, 'r') as f:
            log_lines = f.read().strip().split('\n')
            
            timestamp_pattern = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
            for line in log_lines:
                self.assertRegex(line, timestamp_pattern)


if __name__ == '__main__':
    unittest.main()