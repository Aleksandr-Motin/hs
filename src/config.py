"""
Configuration module for environment variables and settings.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for file processor application."""
    
    def __init__(self):
        """Initialize configuration with environment variables."""
        self.directory_path = os.getenv('DIRECTORY_PATH', './files')
        self.aidbox_base_url = os.getenv('AIDBOX_BASE_URL', 'https://api.aidbox.dev')
        
        self.aidbox_username = os.getenv('AIDBOX_USERNAME', '')
        self.aidbox_password = os.getenv('AIDBOX_PASSWORD', '')
        
        self.log_file_path = os.getenv('LOG_FILE_PATH', 'file_processor.log')
        self.processed_files_path = os.getenv('PROCESSED_FILES_PATH', 'processed_files.txt')
        self.schedule_interval = int(os.getenv('SCHEDULE_INTERVAL', '10'))
        self.retry_delay_seconds = int(os.getenv('RETRY_DELAY_SECONDS', '5'))
    
    def validate(self) -> bool:
        """
        Validate that required configuration values are present.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        # Check base URL is present
        if not self.aidbox_base_url:
            print("Error: Required configuration AIDBOX_BASE_URL is missing")
            return False
        
        # Check that username and password are provided for basic auth
        if not (self.aidbox_username and self.aidbox_password):
            print("Error: Both AIDBOX_USERNAME and AIDBOX_PASSWORD must be provided")
            return False
        
        return True
    
    def get_directory_path(self) -> str:
        """Get the directory path to monitor for files."""
        return self.directory_path
    
    def get_aidbox_config(self) -> tuple[str, str, str]:
        """
        Get Aidbox configuration.
        
        Returns:
            tuple: (base_url, username, password)
        """
        return self.aidbox_base_url, self.aidbox_username, self.aidbox_password
    
    def get_aidbox_auth_type(self) -> str:
        """
        Determine which authentication type to use.
        
        Returns:
            str: Always returns 'basic' since only basic auth is supported
        """
        return 'basic'
    
    def get_log_file_path(self) -> str:
        """Get the log file path."""
        return self.log_file_path
    
    def get_processed_files_path(self) -> str:
        """Get the processed files tracking file path."""
        return self.processed_files_path
    
    def get_schedule_interval(self) -> int:
        """Get the schedule interval in seconds."""
        return self.schedule_interval
    
    def get_retry_delay_seconds(self) -> int:
        """Get the retry delay in seconds."""
        return self.retry_delay_seconds


# Global configuration instance
config = Config()