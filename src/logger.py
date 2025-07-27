"""
Logger module for file processor application.
Provides file-based logging with rotation and timestamp formatting.
"""

import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional


class FileProcessorLogger:
    """Centralized logger for the file processor application."""
    
    def __init__(self, log_file_path: str = "file_processor.log", max_bytes: int = 10485760, backup_count: int = 5):
        """
        Initialize the logger with file-based logging and rotation.
        
        Args:
            log_file_path: Path to the log file
            max_bytes: Maximum size of log file before rotation (default: 10MB)
            backup_count: Number of backup files to keep (default: 5)
        """
        self.log_file_path = log_file_path
        self.logger = logging.getLogger('file_processor')
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_file_path) if os.path.dirname(log_file_path) else '.'
        if log_dir != '.' and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Set up rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        
        # Create formatter with timestamp
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(file_handler)
    
    def log_info(self, message: str) -> None:
        """
        Log an informational message.
        
        Args:
            message: The message to log
        """
        try:
            self.logger.info(message)
        except Exception as e:
            # Fallback to console if logging fails
            print(f"[INFO] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")
            print(f"[ERROR] Logging failed: {e}")
    
    def log_error(self, message: str, exception: Optional[Exception] = None) -> None:
        """
        Log an error message with optional exception details.
        
        Args:
            message: The error message to log
            exception: Optional exception object for additional context
        """
        try:
            if exception:
                exception_type = type(exception).__name__
                error_msg = f"{message} - {exception_type}: {str(exception)}"
                self.logger.error(error_msg)
            else:
                self.logger.error(message)
        except Exception as e:
            # Fallback to console if logging fails
            print(f"[ERROR] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")
            if exception:
                print(f"[ERROR] Exception: {exception}")
            print(f"[ERROR] Logging failed: {e}")
    
    def log_warning(self, message: str) -> None:
        """
        Log a warning message.
        
        Args:
            message: The warning message to log
        """
        try:
            self.logger.warning(message)
        except Exception as e:
            # Fallback to console if logging fails
            print(f"[WARNING] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")
            print(f"[ERROR] Logging failed: {e}")
    
    def log_success(self, message: str) -> None:
        """
        Log a success message (using INFO level with SUCCESS prefix).
        
        Args:
            message: The success message to log
        """
        try:
            success_msg = f"SUCCESS: {message}"
            self.logger.info(success_msg)
        except Exception as e:
            # Fallback to console if logging fails
            print(f"[SUCCESS] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")
            print(f"[ERROR] Logging failed: {e}")


# Global logger instance
_logger_instance: Optional[FileProcessorLogger] = None


def setup_logger(log_file_path: str = "file_processor.log", max_bytes: int = 10485760, backup_count: int = 5) -> FileProcessorLogger:
    """
    Set up and return the global logger instance.
    
    Args:
        log_file_path: Path to the log file
        max_bytes: Maximum size of log file before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
    
    Returns:
        FileProcessorLogger instance
    """
    global _logger_instance
    _logger_instance = FileProcessorLogger(log_file_path, max_bytes, backup_count)
    return _logger_instance


def get_logger() -> FileProcessorLogger:
    """
    Get the global logger instance. Creates one if it doesn't exist.
    
    Returns:
        FileProcessorLogger instance
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = FileProcessorLogger()
    return _logger_instance


# Convenience functions for direct logging
def log_info(message: str) -> None:
    """Log an informational message using the global logger."""
    get_logger().log_info(message)


def log_error(message: str, exception: Optional[Exception] = None) -> None:
    """Log an error message using the global logger."""
    get_logger().log_error(message, exception)


def log_warning(message: str) -> None:
    """Log a warning message using the global logger."""
    get_logger().log_warning(message)


def log_success(message: str) -> None:
    """Log a success message using the global logger."""
    get_logger().log_success(message)