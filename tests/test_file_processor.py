"""
Unit tests for file_processor module.
Tests file detection, reading, and processing logic with mocked file system.
"""

import os
import tempfile
import shutil
from unittest.mock import patch, mock_open, MagicMock
import pytest

from src.file_processor import FileProcessor, process_new_files, get_new_files, read_file_content, mark_file_as_processed


class TestFileProcessor:
    """Test cases for FileProcessor class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.processed_files_path = os.path.join(self.temp_dir, "processed_files.txt")
        self.processor = FileProcessor(
            directory_path=self.temp_dir,
            processed_files_path=self.processed_files_path
        )
    
    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_init_creates_directory_if_not_exists(self):
        """Test that FileProcessor creates directory if it doesn't exist."""
        non_existent_dir = os.path.join(self.temp_dir, "new_dir")
        processor = FileProcessor(directory_path=non_existent_dir)
        
        assert os.path.exists(non_existent_dir)
        assert processor.directory_path == non_existent_dir
    
    @patch('src.file_processor.log_error')
    def test_init_handles_directory_creation_error(self, mock_log_error):
        """Test that FileProcessor handles directory creation errors gracefully."""
        with patch('os.makedirs', side_effect=PermissionError("Permission denied")):
            processor = FileProcessor(directory_path="/invalid/path")
            mock_log_error.assert_called_once()
    
    def test_get_new_files_empty_directory(self):
        """Test get_new_files with empty directory."""
        new_files = self.processor.get_new_files()
        assert new_files == []
    
    def test_get_new_files_with_files(self):
        """Test get_new_files with files in directory."""
        # Create test files
        test_files = ["file1.txt", "file2.txt", "file3.txt"]
        for filename in test_files:
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, 'w') as f:
                f.write("test content")
        
        new_files = self.processor.get_new_files()
        
        # Should return all files since none are processed yet
        assert len(new_files) == 3
        for file_path in new_files:
            assert os.path.basename(file_path) in test_files
    
    def test_get_new_files_excludes_processed_files(self):
        """Test that get_new_files excludes already processed files."""
        # Create test files
        test_files = ["file1.txt", "file2.txt", "file3.txt"]
        for filename in test_files:
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, 'w') as f:
                f.write("test content")
        
        # Mark one file as processed
        with open(self.processed_files_path, 'w') as f:
            f.write("file1.txt|2023-01-01 12:00:00|success\n")
        
        new_files = self.processor.get_new_files()
        
        # Should return only unprocessed files
        assert len(new_files) == 2
        filenames = [os.path.basename(f) for f in new_files]
        assert "file1.txt" not in filenames
        assert "file2.txt" in filenames
        assert "file3.txt" in filenames
    
    def test_get_new_files_ignores_directories(self):
        """Test that get_new_files ignores directories."""
        # Create a file and a directory
        file_path = os.path.join(self.temp_dir, "test_file.txt")
        dir_path = os.path.join(self.temp_dir, "test_dir")
        
        with open(file_path, 'w') as f:
            f.write("test content")
        os.makedirs(dir_path)
        
        new_files = self.processor.get_new_files()
        
        # Should return only the file, not the directory
        assert len(new_files) == 1
        assert os.path.basename(new_files[0]) == "test_file.txt"
    
    @patch('src.file_processor.log_error')
    def test_get_new_files_handles_errors(self, mock_log_error):
        """Test that get_new_files handles errors gracefully."""
        with patch('glob.glob', side_effect=PermissionError("Permission denied")):
            new_files = self.processor.get_new_files()
            
            assert new_files == []
            mock_log_error.assert_called_once()
    
    def test_read_file_content_success(self):
        """Test successful file content reading."""
        test_content = "This is test file content"
        file_path = os.path.join(self.temp_dir, "test.txt")
        
        with open(file_path, 'w') as f:
            f.write(test_content)
        
        content = self.processor.read_file_content(file_path)
        
        assert content == test_content
    
    @patch('src.file_processor.time.sleep')
    def test_read_file_content_file_not_found_retries_endlessly(self, mock_sleep):
        """Test read_file_content retries endlessly with non-existent file."""
        non_existent_file = os.path.join(self.temp_dir, "nonexistent.txt")
        
        # This test would run forever, so we'll test the retry behavior by mocking
        # and checking that it would retry (we'll interrupt after a few attempts)
        with patch('os.path.exists', return_value=False):
            with pytest.raises(Exception):  # We'll interrupt with an exception
                # Mock sleep to raise exception after a few calls to stop infinite loop
                def mock_sleep_side_effect(seconds):
                    if mock_sleep.call_count >= 3:
                        raise Exception("Test interrupted")
                
                mock_sleep.side_effect = mock_sleep_side_effect
                self.processor.read_file_content(non_existent_file)
        
        assert mock_sleep.call_count >= 3  # Should have retried multiple times
    
    @patch('src.file_processor.time.sleep')
    def test_read_file_content_not_a_file_retries_endlessly(self, mock_sleep):
        """Test read_file_content retries endlessly with directory path."""
        dir_path = os.path.join(self.temp_dir, "test_dir")
        os.makedirs(dir_path)
        
        # This test would run forever, so we'll test the retry behavior
        with pytest.raises(Exception):  # We'll interrupt with an exception
            # Mock sleep to raise exception after a few calls to stop infinite loop
            def mock_sleep_side_effect(seconds):
                if mock_sleep.call_count >= 3:
                    raise Exception("Test interrupted")
            
            mock_sleep.side_effect = mock_sleep_side_effect
            self.processor.read_file_content(dir_path)
        
        assert mock_sleep.call_count >= 3  # Should have retried multiple times
    
    @patch('src.file_processor.time.sleep')
    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    @patch('src.file_processor.log_error')
    def test_read_file_content_permission_error_retries_endlessly(self, mock_log_error, mock_open, mock_sleep):
        """Test read_file_content retries endlessly on permission errors."""
        file_path = os.path.join(self.temp_dir, "test.txt")
        
        # This test would run forever, so we'll test the retry behavior
        with patch('os.path.exists', return_value=True):
            with patch('os.path.isfile', return_value=True):
                with pytest.raises(Exception):  # We'll interrupt with an exception
                    # Mock sleep to raise exception after a few calls to stop infinite loop
                    def mock_sleep_side_effect(seconds):
                        if mock_sleep.call_count >= 3:
                            raise Exception("Test interrupted")
                    
                    mock_sleep.side_effect = mock_sleep_side_effect
                    self.processor.read_file_content(file_path)
        
        assert mock_sleep.call_count >= 3  # Should have retried multiple times
        assert mock_log_error.call_count >= 3  # Should have logged errors
    
    @patch('src.file_processor.time.sleep')
    @patch('builtins.open', side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid"))
    @patch('src.file_processor.log_error')
    def test_read_file_content_unicode_error_retries_endlessly(self, mock_log_error, mock_open, mock_sleep):
        """Test read_file_content retries endlessly on unicode decode errors."""
        file_path = os.path.join(self.temp_dir, "test.txt")
        
        # This test would run forever, so we'll test the retry behavior
        with patch('os.path.exists', return_value=True):
            with patch('os.path.isfile', return_value=True):
                with pytest.raises(Exception):  # We'll interrupt with an exception
                    # Mock sleep to raise exception after a few calls to stop infinite loop
                    def mock_sleep_side_effect(seconds):
                        if mock_sleep.call_count >= 3:
                            raise Exception("Test interrupted")
                    
                    mock_sleep.side_effect = mock_sleep_side_effect
                    self.processor.read_file_content(file_path)
        
        assert mock_sleep.call_count >= 3  # Should have retried multiple times
        assert mock_log_error.call_count >= 3  # Should have logged errors
    
    def test_mark_file_as_processed_success(self):
        """Test successful file marking as processed."""
        file_path = os.path.join(self.temp_dir, "test.txt")
        
        result = self.processor.mark_file_as_processed(file_path, "success")
        
        assert result is True
        
        # Verify entry was written to file
        with open(self.processed_files_path, 'r') as f:
            content = f.read()
            assert "test.txt" in content
            assert "success" in content
    
    def test_mark_file_as_processed_error_status(self):
        """Test marking file as processed with error status."""
        file_path = os.path.join(self.temp_dir, "test.txt")
        
        result = self.processor.mark_file_as_processed(file_path, "error")
        
        assert result is True
        
        # Verify entry was written with error status
        with open(self.processed_files_path, 'r') as f:
            content = f.read()
            assert "test.txt" in content
            assert "error" in content
    
    @patch('builtins.open', side_effect=IOError("IO Error"))
    @patch('src.file_processor.log_error')
    def test_mark_file_as_processed_handles_errors(self, mock_log_error, mock_open):
        """Test that mark_file_as_processed handles IO errors."""
        file_path = os.path.join(self.temp_dir, "test.txt")
        
        result = self.processor.mark_file_as_processed(file_path)
        
        assert result is False
        mock_log_error.assert_called_once()
    
    def test_load_processed_files_empty_file(self):
        """Test loading processed files from empty tracking file."""
        # Create empty processed files tracking file
        with open(self.processed_files_path, 'w') as f:
            pass
        
        processed_files = self.processor._load_processed_files()
        
        assert processed_files == set()
    
    def test_load_processed_files_with_entries(self):
        """Test loading processed files with existing entries."""
        # Create processed files tracking file with entries
        with open(self.processed_files_path, 'w') as f:
            f.write("file1.txt|2023-01-01 12:00:00|success\n")
            f.write("file2.txt|2023-01-01 12:01:00|error\n")
            f.write("file3.txt|2023-01-01 12:02:00|success\n")
        
        processed_files = self.processor._load_processed_files()
        
        expected_files = {"file1.txt", "file2.txt", "file3.txt"}
        assert processed_files == expected_files
    
    def test_load_processed_files_creates_file_if_not_exists(self):
        """Test that _load_processed_files creates tracking file if it doesn't exist."""
        # Ensure file doesn't exist
        if os.path.exists(self.processed_files_path):
            os.remove(self.processed_files_path)
        
        processed_files = self.processor._load_processed_files()
        
        assert processed_files == set()
        assert os.path.exists(self.processed_files_path)
    
    @patch('builtins.open', side_effect=IOError("IO Error"))
    @patch('src.file_processor.log_error')
    def test_load_processed_files_handles_errors(self, mock_log_error, mock_open):
        """Test that _load_processed_files handles IO errors gracefully."""
        processed_files = self.processor._load_processed_files()
        
        assert processed_files == set()
        mock_log_error.assert_called_once()
    
    @patch('src.file_processor.send_hl7v2_message')
    def test_process_new_files_success(self, mock_send_hl7v2):
        """Test successful processing of new files."""
        # Setup mock
        mock_send_hl7v2.return_value = (True, {"http_status_code": 201, "id": "123"})
        
        # Create test files
        test_files = ["file1.txt", "file2.txt"]
        for filename in test_files:
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, 'w') as f:
                f.write(f"Content of {filename}")
        
        result = self.processor.process_new_files()
        
        assert result == 2
        assert mock_send_hl7v2.call_count == 2
        
        # Verify files were marked as processed
        with open(self.processed_files_path, 'r') as f:
            content = f.read()
            assert "file1.txt" in content
            assert "file2.txt" in content
            assert content.count("success") == 2
    
    @patch('src.file_processor.send_hl7v2_message')
    def test_process_new_files_api_failure(self, mock_send_hl7v2):
        """Test processing when API calls fail."""
        # Setup mock to return HTTP failure (will retry endlessly)
        # We need to mock it to eventually succeed to avoid infinite retry
        call_count = 0
        def mock_send_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return False, {"http_status_code": 500, "error_message": "Server error"}
            return False, {"http_status_code": 200, "id": "123"}  # Processing failed but delivered
        
        mock_send_hl7v2.side_effect = mock_send_side_effect
        
        # Create test file
        file_path = os.path.join(self.temp_dir, "test.txt")
        with open(file_path, 'w') as f:
            f.write("test content")
        
        result = self.processor.process_new_files()
        
        assert result == 1  # File was processed (delivered to Aidbox)
        
        # Verify file was marked as processed with error status
        with open(self.processed_files_path, 'r') as f:
            content = f.read()
            assert "test.txt" in content
            assert "error" in content
    
    def test_process_new_files_no_files(self):
        """Test processing when no new files exist."""
        result = self.processor.process_new_files()
        
        assert result == 0
    
    @patch('src.file_processor.send_hl7v2_message')
    def test_process_new_files_read_error(self, mock_send_hl7v2):
        """Test processing when file reading fails."""
        # Create a file then remove it to simulate read error
        file_path = os.path.join(self.temp_dir, "test.txt")
        with open(file_path, 'w') as f:
            f.write("test content")
        
        # Since read_file_content now retries endlessly, we need to test differently
        # We'll mock it to eventually succeed after a few retries
        call_count = 0
        def mock_read_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise PermissionError("Permission denied")
            return "test content"
        
        with patch.object(self.processor, 'read_file_content', side_effect=mock_read_side_effect):
            mock_send_hl7v2.return_value = (True, {"http_status_code": 201, "id": "123"})
            result = self.processor.process_new_files()
        
        assert result == 1  # File eventually processed successfully
        assert mock_send_hl7v2.call_count == 1
        
        # Verify file was marked as processed with success status
        with open(self.processed_files_path, 'r') as f:
            content = f.read()
            assert "test.txt" in content
            assert "success" in content


class TestConvenienceFunctions:
    """Test cases for module-level convenience functions."""
    
    @patch('src.file_processor._get_processor')
    def test_process_new_files_function(self, mock_get_processor):
        """Test process_new_files convenience function."""
        mock_processor = MagicMock()
        mock_processor.process_new_files.return_value = 5
        mock_get_processor.return_value = mock_processor
        
        result = process_new_files("/test/path")
        
        assert result == 5
        mock_processor.process_new_files.assert_called_once_with("/test/path")
    
    @patch('src.file_processor._get_processor')
    def test_get_new_files_function(self, mock_get_processor):
        """Test get_new_files convenience function."""
        mock_processor = MagicMock()
        mock_processor.get_new_files.return_value = ["file1.txt", "file2.txt"]
        mock_get_processor.return_value = mock_processor
        
        result = get_new_files("/test/path")
        
        assert result == ["file1.txt", "file2.txt"]
        mock_processor.get_new_files.assert_called_once_with("/test/path")
    
    @patch('src.file_processor._get_processor')
    def test_read_file_content_function(self, mock_get_processor):
        """Test read_file_content convenience function."""
        mock_processor = MagicMock()
        mock_processor.read_file_content.return_value = "file content"
        mock_get_processor.return_value = mock_processor
        
        result = read_file_content("/test/file.txt")
        
        assert result == "file content"
        mock_processor.read_file_content.assert_called_once_with("/test/file.txt")
    
    @patch('src.file_processor._get_processor')
    def test_mark_file_as_processed_function(self, mock_get_processor):
        """Test mark_file_as_processed convenience function."""
        mock_processor = MagicMock()
        mock_processor.mark_file_as_processed.return_value = True
        mock_get_processor.return_value = mock_processor
        
        result = mark_file_as_processed("/test/file.txt", "success")
        
        assert result is True
        mock_processor.mark_file_as_processed.assert_called_once_with("/test/file.txt", "success")


class TestIntegrationWorkflow:
    """Integration tests for the complete processing workflow."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.processed_files_path = os.path.join(self.temp_dir, "processed_files.txt")
        self.processor = FileProcessor(
            directory_path=self.temp_dir,
            processed_files_path=self.processed_files_path
        )
    
    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('src.file_processor.send_hl7v2_message')
    def test_complete_workflow_success(self, mock_send_hl7v2):
        """Test complete end-to-end processing workflow with successful API calls."""
        # Setup mock API response
        mock_send_hl7v2.return_value = (True, {"http_status_code": 201, "id": "123"})
        
        # Create multiple test files with different content
        test_files = {
            "document1.txt": "This is the content of document 1",
            "document2.json": '{"name": "test", "value": 42}',
            "document3.csv": "name,age,city\nJohn,30,NYC\nJane,25,LA"
        }
        
        for filename, content in test_files.items():
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, 'w') as f:
                f.write(content)
        
        # Execute the complete workflow
        result = self.processor.process_new_files()
        
        # Verify results
        assert result == 3  # All files processed successfully
        assert mock_send_hl7v2.call_count == 3
        
        # Verify API was called with correct parameters for each file
        calls = mock_send_hl7v2.call_args_list
        sent_files = {}
        for args, kwargs in calls:
            content, filename = args[0], args[1]
            sent_files[filename] = content
        
        # Verify each file was sent with correct content
        for filename, expected_content in test_files.items():
            assert filename in sent_files
            assert sent_files[filename] == expected_content
        
        # Verify all files were marked as processed successfully
        with open(self.processed_files_path, 'r') as f:
            processed_content = f.read()
            for filename in test_files.keys():
                assert filename in processed_content
            # Count success status entries (not occurrences in filenames)
            success_count = len([line for line in processed_content.split('\n') if line.strip() and '|success' in line])
            assert success_count == 3
    
    @patch('src.file_processor.send_hl7v2_message')
    def test_complete_workflow_mixed_results(self, mock_send_hl7v2):
        """Test complete workflow with mixed success and failure results."""
        # Create test files with predictable names
        test_files = ["file_a.txt", "file_b.txt", "file_c.txt"]
        for filename in test_files:
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, 'w') as f:
                f.write(f"Content of {filename}")
        
        # Setup mock to return success, processing failure, success
        call_count = 0
        def mock_api_call(content, filename):
            nonlocal call_count
            call_count += 1
            # Make second call return processing failure (but HTTP success)
            if call_count == 2:
                return (False, {"http_status_code": 200, "id": "456"})
            return (True, {"http_status_code": 201, "id": "123"})
        
        mock_send_hl7v2.side_effect = mock_api_call
        
        # Execute workflow
        result = self.processor.process_new_files()
        
        # Verify results
        assert result == 3  # All files processed (delivered to Aidbox)
        assert mock_send_hl7v2.call_count == 3
        
        # Verify processing status in tracking file
        with open(self.processed_files_path, 'r') as f:
            processed_content = f.read()
            for filename in test_files:
                assert filename in processed_content
            # Count success and error status entries
            success_count = len([line for line in processed_content.split('\n') if line.strip() and '|success' in line])
            error_count = len([line for line in processed_content.split('\n') if line.strip() and '|error' in line])
            assert success_count == 2
            assert error_count == 1
    
    @patch('src.file_processor.send_hl7v2_message')
    def test_workflow_with_file_read_errors(self, mock_send_hl7v2):
        """Test workflow when some files cannot be read."""
        # Create one readable file and one that will cause read error
        readable_file = os.path.join(self.temp_dir, "readable.txt")
        with open(readable_file, 'w') as f:
            f.write("This file can be read")
        
        # Create a file that will be deleted to simulate read error
        unreadable_file = os.path.join(self.temp_dir, "unreadable.txt")
        with open(unreadable_file, 'w') as f:
            f.write("This file will cause error")
        
        # Since read_file_content now retries endlessly, we'll test with eventual success
        # Mock read_file_content to fail a few times then succeed for error file
        call_counts = {}
        original_read = self.processor.read_file_content
        def mock_read(file_path):
            if "unreadable.txt" in file_path:
                call_counts[file_path] = call_counts.get(file_path, 0) + 1
                if call_counts[file_path] <= 2:
                    raise PermissionError("Permission denied")
                return "Content after retry"
            return original_read(file_path)
        
        with patch.object(self.processor, 'read_file_content', side_effect=mock_read):
            mock_send_hl7v2.return_value = (True, {"http_status_code": 201, "id": "123"})
            
            result = self.processor.process_new_files()
        
        # Verify results
        assert result == 2  # Both files eventually processed successfully
        assert mock_send_hl7v2.call_count == 2  # Called for both files
        
        # Verify both files are marked as processed with success
        with open(self.processed_files_path, 'r') as f:
            processed_content = f.read()
            assert "readable.txt" in processed_content
            assert "unreadable.txt" in processed_content
            # Count success status entries
            success_count = len([line for line in processed_content.split('\n') if line.strip() and '|success' in line])
            assert success_count == 2
    
    def test_workflow_with_no_new_files(self):
        """Test workflow when no new files are present."""
        result = self.processor.process_new_files()
        
        assert result == 0
        
        # Verify no processed files tracking file is created (or empty if created)
        if os.path.exists(self.processed_files_path):
            with open(self.processed_files_path, 'r') as f:
                content = f.read().strip()
                assert content == ""
    
    @patch('src.file_processor.send_hl7v2_message')
    def test_workflow_skips_already_processed_files(self, mock_send_hl7v2):
        """Test that workflow skips files that have already been processed."""
        # Create test files
        test_files = ["new1.txt", "old.txt", "new2.txt"]
        for filename in test_files:
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, 'w') as f:
                f.write(f"Content of {filename}")
        
        # Mark one file as already processed
        with open(self.processed_files_path, 'w') as f:
            f.write("old.txt|2023-01-01 12:00:00|success\n")
        
        mock_send_hl7v2.return_value = (True, {"http_status_code": 201, "id": "123"})
        
        # Execute workflow
        result = self.processor.process_new_files()
        
        # Verify results
        assert result == 2  # Only new files processed
        assert mock_send_hl7v2.call_count == 2
        
        # Verify API was called only for new files
        calls = mock_send_hl7v2.call_args_list
        called_files = [args[1] for args, kwargs in calls]  # filename is second argument
        assert "new1.txt" in called_files
        assert "new2.txt" in called_files
        assert "old.txt" not in called_files
    
    @patch('src.file_processor.send_hl7v2_message')
    @patch('src.file_processor.log_error')
    def test_workflow_handles_unexpected_errors(self, mock_log_error, mock_send_hl7v2):
        """Test workflow handles unexpected errors gracefully."""
        # Create test file
        file_path = os.path.join(self.temp_dir, "test.txt")
        with open(file_path, 'w') as f:
            f.write("test content")
        
        # Mock send_hl7v2_message to raise unexpected exception a few times then succeed
        call_count = 0
        def mock_send_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Unexpected error")
            return (True, {"http_status_code": 201, "id": "123"})
        
        mock_send_hl7v2.side_effect = mock_send_side_effect
        
        # Execute workflow - should not crash and eventually succeed
        result = self.processor.process_new_files()
        
        # Verify error handling and eventual success
        assert result == 1  # File eventually processed successfully
        mock_log_error.assert_called()
        
        # Verify file is marked as processed with success status
        with open(self.processed_files_path, 'r') as f:
            content = f.read()
            assert "test.txt" in content
            assert "success" in content
    
    @patch('src.file_processor.send_hl7v2_message')
    def test_workflow_with_large_files(self, mock_send_hl7v2):
        """Test workflow with larger file content."""
        mock_send_hl7v2.return_value = (True, {"http_status_code": 201, "id": "123"})
        
        # Create a larger test file
        large_content = "This is a line of content.\n" * 1000  # ~26KB file
        file_path = os.path.join(self.temp_dir, "large_file.txt")
        with open(file_path, 'w') as f:
            f.write(large_content)
        
        # Execute workflow
        result = self.processor.process_new_files()
        
        # Verify results
        assert result == 1
        assert mock_send_hl7v2.call_count == 1
        
        # Verify the large content was passed correctly
        args, kwargs = mock_send_hl7v2.call_args
        assert args[0] == large_content
        assert args[1] == "large_file.txt"
    
    @patch('src.file_processor.send_hl7v2_message')
    def test_workflow_with_different_file_types(self, mock_send_hl7v2):
        """Test workflow processes different file types correctly."""
        mock_send_hl7v2.return_value = (True, {"http_status_code": 201, "id": "123"})
        
        # Create files with different extensions and content types
        test_files = {
            "data.json": '{"key": "value", "number": 123}',
            "config.xml": '<?xml version="1.0"?><root><item>value</item></root>',
            "script.py": 'print("Hello, World!")\nfor i in range(10):\n    print(i)',
            "readme.md": '# Title\n\nThis is a **markdown** file with *formatting*.',
            "data.csv": 'name,age,city\n"John Doe",30,"New York"\n"Jane Smith",25,"Los Angeles"'
        }
        
        for filename, content in test_files.items():
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, 'w') as f:
                f.write(content)
        
        # Execute workflow
        result = self.processor.process_new_files()
        
        # Verify all files processed
        assert result == len(test_files)
        assert mock_send_hl7v2.call_count == len(test_files)
        
        # Verify each file was sent with correct content
        calls = mock_send_hl7v2.call_args_list
        sent_files = {}
        for args, kwargs in calls:
            content, filename = args[0], args[1]
            sent_files[filename] = content
        
        for filename, expected_content in test_files.items():
            assert filename in sent_files
            assert sent_files[filename] == expected_content


class TestRetryFunctionality:
    """Test cases for the new retry functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.processed_files_path = os.path.join(self.temp_dir, "processed_files.txt")
        self.processor = FileProcessor(
            directory_path=self.temp_dir,
            processed_files_path=self.processed_files_path
        )
    
    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('src.file_processor.time.sleep')
    @patch('src.file_processor.log_error')
    @patch('src.file_processor.log_info')
    def test_read_file_content_retry_on_permission_error(self, mock_log_info, mock_log_error, mock_sleep):
        """Test that read_file_content retries on permission errors."""
        file_path = os.path.join(self.temp_dir, "test.txt")
        
        # Mock open to fail twice then succeed
        call_count = 0
        def mock_open_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise PermissionError("Permission denied")
            return mock_open(read_data="test content")(*args, **kwargs)
        
        with patch('builtins.open', side_effect=mock_open_side_effect):
            with patch('os.path.exists', return_value=True):
                with patch('os.path.isfile', return_value=True):
                    content = self.processor.read_file_content(file_path)
        
        assert content == "test content"
        assert mock_log_error.call_count == 2  # Two error logs for failed attempts
        assert mock_log_info.call_count >= 3  # At least retry logs + success log
        assert mock_sleep.call_count == 2  # Two sleep calls for retries
    
    @patch('src.file_processor.time.sleep')
    @patch('src.file_processor.log_error')
    def test_read_file_content_retry_on_unicode_error(self, mock_log_error, mock_sleep):
        """Test that read_file_content retries on unicode decode errors."""
        file_path = os.path.join(self.temp_dir, "test.txt")
        
        # Mock open to fail once then succeed
        call_count = 0
        def mock_open_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")
            return mock_open(read_data="test content")(*args, **kwargs)
        
        with patch('builtins.open', side_effect=mock_open_side_effect):
            with patch('os.path.exists', return_value=True):
                with patch('os.path.isfile', return_value=True):
                    content = self.processor.read_file_content(file_path)
        
        assert content == "test content"
        assert mock_log_error.call_count == 1
        assert mock_sleep.call_count == 1
    
    @patch('src.file_processor.time.sleep')
    @patch('src.file_processor.log_error')
    def test_read_file_content_retry_on_file_not_found(self, mock_log_error, mock_sleep):
        """Test that read_file_content retries when file is not found."""
        file_path = os.path.join(self.temp_dir, "test.txt")
        
        # Mock exists to fail twice then succeed
        call_count = 0
        def mock_exists_side_effect(path):
            nonlocal call_count
            call_count += 1
            return call_count > 2
        
        with patch('os.path.exists', side_effect=mock_exists_side_effect):
            with patch('os.path.isfile', return_value=True):
                with patch('builtins.open', mock_open(read_data="test content")):
                    content = self.processor.read_file_content(file_path)
        
        assert content == "test content"
        assert mock_log_error.call_count == 2
        assert mock_sleep.call_count == 2
    
    @patch('src.file_processor.send_hl7v2_message')
    @patch('src.file_processor.time.sleep')
    @patch('src.file_processor.log_error')
    @patch('src.file_processor.log_info')
    def test_send_message_with_retry_on_network_failure(self, mock_log_info, mock_log_error, mock_sleep, mock_send):
        """Test that _send_message_with_retry retries on network failures."""
        # Mock send_hl7v2_message to fail twice then succeed
        call_count = 0
        def mock_send_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return False, {"http_status_code": 500, "error_message": "Server error"}
            return True, {"http_status_code": 201, "id": "123"}
        
        mock_send.side_effect = mock_send_side_effect
        
        success, response_data = self.processor._send_message_with_retry("test content", "test.txt")
        
        assert success is True
        assert response_data["http_status_code"] == 201
        assert response_data["id"] == "123"
        assert mock_send.call_count == 3
        assert mock_log_error.call_count == 2  # Two error logs for failed attempts
        assert mock_sleep.call_count == 2  # Two sleep calls for retries
    
    @patch('src.file_processor.send_hl7v2_message')
    @patch('src.file_processor.time.sleep')
    @patch('src.file_processor.log_error')
    def test_send_message_with_retry_on_no_response(self, mock_log_error, mock_sleep, mock_send):
        """Test retry behavior when no response data is received."""
        # Mock to return no response data twice then succeed
        call_count = 0
        def mock_send_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return False, None
            return True, {"http_status_code": 200, "id": "456"}
        
        mock_send.side_effect = mock_send_side_effect
        
        success, response_data = self.processor._send_message_with_retry("test content", "test.txt")
        
        assert success is True
        assert response_data["http_status_code"] == 200
        assert mock_send.call_count == 3
        assert mock_log_error.call_count == 2
        assert mock_sleep.call_count == 2
    
    @patch('src.file_processor.time.sleep')
    @patch('src.file_processor.log_error')
    @patch('src.file_processor.log_info')
    def test_process_single_file_with_retry_on_exception(self, mock_log_info, mock_log_error, mock_sleep):
        """Test that _process_single_file_with_retry retries on unexpected exceptions."""
        file_path = os.path.join(self.temp_dir, "test.txt")
        
        # Mock read_file_content to fail once then succeed
        call_count = 0
        def mock_read_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Unexpected error")
            return "test content"
        
        with patch.object(self.processor, 'read_file_content', side_effect=mock_read_side_effect):
            with patch.object(self.processor, '_send_message_with_retry', return_value=(True, {"http_status_code": 201, "id": "123"})):
                with patch.object(self.processor, 'mark_file_as_processed', return_value=True):
                    # This should not raise an exception
                    self.processor._process_single_file_with_retry(file_path, "test.txt")
        
        assert mock_log_error.call_count == 1  # One error log for failed attempt
        assert mock_sleep.call_count == 1  # One sleep call for retry
    
    @patch('src.config.config.get_retry_delay_seconds')
    @patch('src.file_processor.time.sleep')
    def test_configurable_retry_delay(self, mock_sleep, mock_get_retry_delay):
        """Test that retry delay is configurable."""
        mock_get_retry_delay.return_value = 10  # 10 seconds delay
        
        file_path = os.path.join(self.temp_dir, "test.txt")
        
        # Mock open to fail once then succeed
        call_count = 0
        def mock_open_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise PermissionError("Permission denied")
            return mock_open(read_data="test content")(*args, **kwargs)
        
        with patch('builtins.open', side_effect=mock_open_side_effect):
            with patch('os.path.exists', return_value=True):
                with patch('os.path.isfile', return_value=True):
                    content = self.processor.read_file_content(file_path)
        
        assert content == "test content"
        mock_sleep.assert_called_with(10)  # Should use configured delay
    
    @patch('src.file_processor.send_hl7v2_message')
    def test_process_new_files_with_retry_logic(self, mock_send):
        """Test that process_new_files uses the new retry logic."""
        # Create test file
        file_path = os.path.join(self.temp_dir, "test.txt")
        with open(file_path, 'w') as f:
            f.write("test content")
        
        # Mock successful API response
        mock_send.return_value = (True, {"http_status_code": 201, "id": "123"})
        
        result = self.processor.process_new_files()
        
        assert result == 1
        assert mock_send.call_count == 1
        
        # Verify file was marked as processed
        with open(self.processed_files_path, 'r') as f:
            content = f.read()
            assert "test.txt" in content
            assert "success" in content
    
    @patch('src.file_processor.send_hl7v2_message')
    def test_process_new_files_marks_processing_errors_correctly(self, mock_send):
        """Test that files are marked correctly when Aidbox processing fails."""
        # Create test file
        file_path = os.path.join(self.temp_dir, "test.txt")
        with open(file_path, 'w') as f:
            f.write("test content")
        
        # Mock API response: delivered but processing failed
        mock_send.return_value = (False, {"http_status_code": 200, "id": "123", "status": "error"})
        
        result = self.processor.process_new_files()
        
        assert result == 1  # File was processed (delivered to Aidbox)
        
        # Verify file was marked as processed with error status
        with open(self.processed_files_path, 'r') as f:
            content = f.read()
            assert "test.txt" in content
            assert "error" in content  # Should be marked as error due to processing failure
    
    def test_file_sorting_order(self):
        """Test that files are processed in alphabetical order."""
        # Create files with names that would be in different order if not sorted
        test_files = ["zebra.txt", "apple.txt", "banana.txt", "cherry.txt"]
        for filename in test_files:
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, 'w') as f:
                f.write(f"Content of {filename}")
        
        new_files = self.processor.get_new_files()
        
        # Extract filenames and verify they are in alphabetical order
        filenames = [os.path.basename(f) for f in new_files]
        expected_order = ["apple.txt", "banana.txt", "cherry.txt", "zebra.txt"]
        
        assert filenames == expected_order


if __name__ == "__main__":
    pytest.main([__file__])