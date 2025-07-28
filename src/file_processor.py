"""
File processor module for detecting and processing new files.
Core business logic for file detection, reading, and processing workflow.
"""

import os
import glob
from typing import List, Optional, Set
from datetime import datetime

from .config import config
from .logger import log_info, log_error, log_warning, log_success
from .hl7v2_handler import send_hl7v2_message


class FileProcessor:
    """Core file processing logic for detecting and processing new files."""
    
    def __init__(self, directory_path: str = None, processed_files_path: str = None):
        """
        Initialize file processor.
        
        Args:
            directory_path: Directory to monitor for files
            processed_files_path: Path to file tracking processed files
        """
        self.directory_path = directory_path or config.get_directory_path()
        self.processed_files_path = processed_files_path or config.get_processed_files_path()
        
        # Ensure directory exists
        if not os.path.exists(self.directory_path):
            try:
                os.makedirs(self.directory_path)
                log_info(f"Created directory: {self.directory_path}")
            except Exception as e:
                log_error(f"Failed to create directory {self.directory_path}", e)
    
    def get_new_files(self, directory_path: str = None) -> List[str]:
        """
        Identify unprocessed files in the directory.
        
        Args:
            directory_path: Optional override for directory path
            
        Returns:
            List[str]: List of file paths that haven't been processed
        """
        target_directory = directory_path or self.directory_path
        
        try:
            # Get all files in directory
            pattern = os.path.join(target_directory, "*")
            all_files = glob.glob(pattern)
            
            # Filter to only include files (not directories) and exclude processed files tracking file
            processed_files_filename = os.path.basename(self.processed_files_path)
            all_files = [f for f in all_files if os.path.isfile(f) and os.path.basename(f) != processed_files_filename]
            
            if not all_files:
                log_info(f"No new files found in directory: {target_directory}")
                return []
            
            # Get set of processed files
            processed_files = self._load_processed_files()
            
            # Find new files by comparing with processed files
            new_files = []
            for file_path in all_files:
                filename = os.path.basename(file_path)
                if filename not in processed_files:
                    new_files.append(file_path)
            
            # Sort files alphabetically by filename to ensure consistent processing order
            new_files.sort(key=lambda x: os.path.basename(x))
            
            if new_files:
                log_info(f"Found {len(new_files)} new files to process")
            else:
                log_info("No new files found for processing")
            
            return new_files
            
        except Exception as e:
            log_error(f"Error detecting new files in {target_directory}", e)
            return []
    
    def read_file_content(self, file_path: str) -> Optional[str]:
        """
        Safely read file contents with error handling.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            Optional[str]: File content as string, or None if error occurred
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                log_error(f"File not found: {file_path}")
                return None
            
            # Check if it's actually a file
            if not os.path.isfile(file_path):
                log_error(f"Path is not a file: {file_path}")
                return None
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                log_info(f"[{os.path.basename(file_path)}] Successfully read file ({len(content)} characters)")
                return content
                
        except PermissionError as e:
            log_error(f"Permission denied reading file {file_path}", e)
            return None
            
        except UnicodeDecodeError as e:
            log_error(f"Unicode decode error reading file {file_path}", e)
            return None
            
        except IOError as e:
            log_error(f"IO error reading file {file_path}", e)
            return None
            
        except Exception as e:
            log_error(f"Unexpected error reading file {file_path}", e)
            return None
    
    def mark_file_as_processed(self, file_path: str, status: str = "success") -> bool:
        """
        Mark a file as processed by adding it to the tracking file.
        
        Args:
            file_path: Path to the file that was processed
            status: Processing status ("success" or "error")
            
        Returns:
            bool: True if successfully marked, False otherwise
        """
        try:
            filename = os.path.basename(file_path)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Create entry for processed file
            entry = f"{filename}|{timestamp}|{status}\n"
            
            # Append to processed files tracking file
            with open(self.processed_files_path, 'a', encoding='utf-8') as file:
                file.write(entry)
            
            log_info(f"[{filename}] Marked file as processed (status: {status})")
            return True
            
        except Exception as e:
            log_error(f"Failed to mark file as processed: {file_path}", e)
            return False
    
    def _load_processed_files(self) -> Set[str]:
        """
        Load the set of processed files from tracking file.
        
        Returns:
            Set[str]: Set of filenames that have been processed
        """
        processed_files = set()
        
        try:
            if not os.path.exists(self.processed_files_path):
                # Create empty file if it doesn't exist
                with open(self.processed_files_path, 'w', encoding='utf-8') as file:
                    pass
                log_info(f"Created processed files tracking file: {self.processed_files_path}")
                return processed_files
            
            with open(self.processed_files_path, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if line:
                        # Parse entry format: filename|timestamp|status
                        parts = line.split('|')
                        if len(parts) >= 1:
                            filename = parts[0]
                            processed_files.add(filename)
            
            log_info(f"Loaded {len(processed_files)} processed files from tracking file")
            return processed_files
            
        except Exception as e:
            log_error(f"Error loading processed files from {self.processed_files_path}", e)
            return processed_files
    
    def process_new_files(self, directory_path: str = None) -> int:
        """
        Main processing function that orchestrates the complete workflow.
        
        Args:
            directory_path: Optional override for directory path
            
        Returns:
            int: Number of files successfully processed
        """
        target_directory = directory_path or self.directory_path
        processed_count = 0
        
        try:
            log_info(f"Starting file processing for directory: {target_directory}")
            
            # Step 1: Get new files
            new_files = self.get_new_files(target_directory)
            
            if not new_files:
                log_info("No new files to process")
                return 0
            
            # Step 2: Process each file
            for file_path in new_files:
                filename = os.path.basename(file_path)
                
                try:
                    log_info(f"[{filename}] Processing file")
                    
                    # Step 3: Read file content
                    content = self.read_file_content(file_path)
                    if content is None:
                        log_error(f"[{filename}] Failed to read file content")
                        self.mark_file_as_processed(file_path, "error")
                        continue
                    
                    # Level 1: File was successfully read
                    log_info(f"[{filename}] File was successfully read")
                    
                    # Step 4: Send to Aidbox API
                    success, response_data = send_hl7v2_message(content, filename)
                    
                    if success:
                        # Step 5: Mark as processed successfully
                        self.mark_file_as_processed(file_path, "success")
                        processed_count += 1
                        
                        # Get message ID and status from response
                        message_id = response_data.get("id", "unknown") if response_data else "unknown"
                        http_status = response_data.get("http_status_code", "unknown") if response_data else "unknown"
                        
                        # Top level: Consolidated success log
                        log_info(f"[{filename}] HL7v2 sending message - SUCCESS {{status: {http_status}, id: {message_id}}} | Processing - SUCCESS")
                    else:
                        # Mark as processed with error status
                        self.mark_file_as_processed(file_path, "error")
                        
                        # Get status and message info from response
                        if response_data:
                            message_id = response_data.get("id", "unknown")
                            http_status = response_data.get("http_status_code", "unknown")
                            error_message = response_data.get("error_message", "")
                            
                            if message_id != "unknown":
                                # HTTP success but processing failed
                                log_warning(f"[{filename}] HL7v2 sending message - SUCCESS {{status: {http_status}, id: {message_id}}} | Processing - ERROR")
                            else:
                                # HTTP request failed
                                log_error(f"[{filename}] HL7v2 sending message - FAILED {{status: {http_status}, message: {error_message}}}")
                        else:
                            log_error(f"[{filename}] HL7v2 sending message - FAILED {{status: unknown, message: No response data}}")
                
                except Exception as e:
                    log_error(f"Error processing file {filename}", e)
                    self.mark_file_as_processed(file_path, "error")
            
            log_info(f"File processing completed. Successfully processed: {processed_count}/{len(new_files)} files")
            return processed_count
            
        except Exception as e:
            log_error(f"Error in main file processing workflow", e)
            return processed_count


# Global file processor instance
_file_processor: Optional[FileProcessor] = None


def _get_processor() -> FileProcessor:
    """Get or create the global file processor instance."""
    global _file_processor
    if _file_processor is None:
        _file_processor = FileProcessor()
    return _file_processor


# Convenience functions for backward compatibility
def process_new_files(directory_path: str = None) -> int:
    """
    Process new files using the global processor instance.
    
    Args:
        directory_path: Optional override for directory path
        
    Returns:
        int: Number of files successfully processed
    """
    return _get_processor().process_new_files(directory_path)


def get_new_files(directory_path: str = None) -> List[str]:
    """
    Get new files using the global processor instance.
    
    Args:
        directory_path: Optional override for directory path
        
    Returns:
        List[str]: List of file paths that haven't been processed
    """
    return _get_processor().get_new_files(directory_path)


def read_file_content(file_path: str) -> Optional[str]:
    """
    Read file content using the global processor instance.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        Optional[str]: File content as string, or None if error occurred
    """
    return _get_processor().read_file_content(file_path)


def mark_file_as_processed(file_path: str, status: str = "success") -> bool:
    """
    Mark file as processed using the global processor instance.
    
    Args:
        file_path: Path to the file that was processed
        status: Processing status ("success" or "error")
        
    Returns:
        bool: True if successfully marked, False otherwise
    """
    return _get_processor().mark_file_as_processed(file_path, status)