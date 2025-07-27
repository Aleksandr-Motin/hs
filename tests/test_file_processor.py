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
    
    def test_read_file_content_file_not_found(self):
        """Test read_file_content with non-existent file."""
        non_existent_file = os.path.join(self.temp_dir, "nonexistent.txt")
        
        content = self.processor.read_file_content(non_existent_file)
        
        assert content is None
    
    def test_read_file_content_not_a_file(self):
        """Test read_file_content with directory path."""
        dir_path = os.path.join(self.temp_dir, "test_dir")
        os.makedirs(dir_path)
        
        content = self.processor.read_file_content(dir_path)
        
        assert content is None
    
    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    @patch('src.file_processor.log_error')
    def test_read_file_content_permission_error(self, mock_log_error, mock_open):
        """Test read_file_content handles permission errors."""
        file_path = os.path.join(self.temp_dir, "test.txt")
        
        content = self.processor.read_file_content(file_path)
        
        assert content is None
        mock_log_error.assert_called_once()
    
    @patch('builtins.open', side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid"))
    @patch('src.file_processor.log_error')
    def test_read_file_content_unicode_error(self, mock_log_error, mock_open):
        """Test read_file_content handles unicode decode errors."""
        file_path = os.path.join(self.temp_dir, "test.txt")
        
        content = self.processor.read_file_content(file_path)
        
        assert content is None
        mock_log_error.assert_called_once()
    
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
    
    @patch('src.file_processor.send_to_aidbox')
    def test_process_new_files_success(self, mock_send_to_aidbox):
        """Test successful processing of new files."""
        # Setup mock
        mock_send_to_aidbox.return_value = (True, {"status": "success"})
        
        # Create test files
        test_files = ["file1.txt", "file2.txt"]
        for filename in test_files:
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, 'w') as f:
                f.write(f"Content of {filename}")
        
        result = self.processor.process_new_files()
        
        assert result == 2
        assert mock_send_to_aidbox.call_count == 2
        
        # Verify files were marked as processed
        with open(self.processed_files_path, 'r') as f:
            content = f.read()
            assert "file1.txt" in content
            assert "file2.txt" in content
            assert content.count("success") == 2
    
    @patch('src.file_processor.send_to_aidbox')
    def test_process_new_files_api_failure(self, mock_send_to_aidbox):
        """Test processing when API calls fail."""
        # Setup mock to return failure
        mock_send_to_aidbox.return_value = (False, None)
        
        # Create test file
        file_path = os.path.join(self.temp_dir, "test.txt")
        with open(file_path, 'w') as f:
            f.write("test content")
        
        result = self.processor.process_new_files()
        
        assert result == 0  # No files successfully processed
        
        # Verify file was marked as processed with error status
        with open(self.processed_files_path, 'r') as f:
            content = f.read()
            assert "test.txt" in content
            assert "error" in content
    
    def test_process_new_files_no_files(self):
        """Test processing when no new files exist."""
        result = self.processor.process_new_files()
        
        assert result == 0
    
    @patch('src.file_processor.send_to_aidbox')
    def test_process_new_files_read_error(self, mock_send_to_aidbox):
        """Test processing when file reading fails."""
        # Create a file then remove it to simulate read error
        file_path = os.path.join(self.temp_dir, "test.txt")
        with open(file_path, 'w') as f:
            f.write("test content")
        
        # Mock read_file_content to return None (simulating read error)
        with patch.object(self.processor, 'read_file_content', return_value=None):
            result = self.processor.process_new_files()
        
        assert result == 0
        assert mock_send_to_aidbox.call_count == 0
        
        # Verify file was marked as processed with error status
        with open(self.processed_files_path, 'r') as f:
            content = f.read()
            assert "test.txt" in content
            assert "error" in content


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
    
    @patch('src.file_processor.send_to_aidbox')
    def test_complete_workflow_success(self, mock_send_to_aidbox):
        """Test complete end-to-end processing workflow with successful API calls."""
        # Setup mock API response
        mock_send_to_aidbox.return_value = (True, {"status": "success", "id": "123"})
        
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
        assert mock_send_to_aidbox.call_count == 3
        
        # Verify API was called with correct parameters for each file
        calls = mock_send_to_aidbox.call_args_list
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
    
    @patch('src.file_processor.send_to_aidbox')
    def test_complete_workflow_mixed_results(self, mock_send_to_aidbox):
        """Test complete workflow with mixed success and failure results."""
        # Create test files with predictable names
        test_files = ["file_a.txt", "file_b.txt", "file_c.txt"]
        for filename in test_files:
            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, 'w') as f:
                f.write(f"Content of {filename}")
        
        # Setup mock to return success, failure, success in order of processing
        # Since file order is not deterministic, we'll track which files succeed/fail
        call_count = 0
        def mock_api_call(content, filename):
            nonlocal call_count
            call_count += 1
            # Make second call fail, others succeed
            if call_count == 2:
                return (False, None)
            return (True, {"status": "success"})
        
        mock_send_to_aidbox.side_effect = mock_api_call
        
        # Execute workflow
        result = self.processor.process_new_files()
        
        # Verify results
        assert result == 2  # Only 2 files processed successfully
        assert mock_send_to_aidbox.call_count == 3
        
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
    
    @patch('src.file_processor.send_to_aidbox')
    def test_workflow_with_file_read_errors(self, mock_send_to_aidbox):
        """Test workflow when some files cannot be read."""
        # Create one readable file and one that will cause read error
        readable_file = os.path.join(self.temp_dir, "readable.txt")
        with open(readable_file, 'w') as f:
            f.write("This file can be read")
        
        # Create a file that will be deleted to simulate read error
        unreadable_file = os.path.join(self.temp_dir, "unreadable.txt")
        with open(unreadable_file, 'w') as f:
            f.write("This file will cause error")
        
        # Mock read_file_content to return None for error file
        original_read = self.processor.read_file_content
        def mock_read(file_path):
            if "unreadable.txt" in file_path:
                return None
            return original_read(file_path)
        
        with patch.object(self.processor, 'read_file_content', side_effect=mock_read):
            mock_send_to_aidbox.return_value = (True, {"status": "success"})
            
            result = self.processor.process_new_files()
        
        # Verify results
        assert result == 1  # Only readable file processed successfully
        assert mock_send_to_aidbox.call_count == 1  # Only called for readable file
        
        # Verify both files are marked as processed (one success, one error)
        with open(self.processed_files_path, 'r') as f:
            processed_content = f.read()
            assert "readable.txt" in processed_content
            assert "unreadable.txt" in processed_content
            # Count success and error status entries
            success_count = len([line for line in processed_content.split('\n') if line.strip() and '|success' in line])
            error_count = len([line for line in processed_content.split('\n') if line.strip() and '|error' in line])
            assert success_count == 1
            assert error_count == 1
    
    def test_workflow_with_no_new_files(self):
        """Test workflow when no new files are present."""
        result = self.processor.process_new_files()
        
        assert result == 0
        
        # Verify no processed files tracking file is created (or empty if created)
        if os.path.exists(self.processed_files_path):
            with open(self.processed_files_path, 'r') as f:
                content = f.read().strip()
                assert content == ""
    
    @patch('src.file_processor.send_to_aidbox')
    def test_workflow_skips_already_processed_files(self, mock_send_to_aidbox):
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
        
        mock_send_to_aidbox.return_value = (True, {"status": "success"})
        
        # Execute workflow
        result = self.processor.process_new_files()
        
        # Verify results
        assert result == 2  # Only new files processed
        assert mock_send_to_aidbox.call_count == 2
        
        # Verify API was called only for new files
        calls = mock_send_to_aidbox.call_args_list
        called_files = [args[1] for args, kwargs in calls]  # filename is second argument
        assert "new1.txt" in called_files
        assert "new2.txt" in called_files
        assert "old.txt" not in called_files
    
    @patch('src.file_processor.send_to_aidbox')
    @patch('src.file_processor.log_error')
    def test_workflow_handles_unexpected_errors(self, mock_log_error, mock_send_to_aidbox):
        """Test workflow handles unexpected errors gracefully."""
        # Create test file
        file_path = os.path.join(self.temp_dir, "test.txt")
        with open(file_path, 'w') as f:
            f.write("test content")
        
        # Mock send_to_aidbox to raise unexpected exception
        mock_send_to_aidbox.side_effect = Exception("Unexpected error")
        
        # Execute workflow - should not crash
        result = self.processor.process_new_files()
        
        # Verify error handling
        assert result == 0  # No files processed successfully
        mock_log_error.assert_called()
        
        # Verify file is marked as processed with error status
        with open(self.processed_files_path, 'r') as f:
            content = f.read()
            assert "test.txt" in content
            assert "error" in content
    
    @patch('src.file_processor.send_to_aidbox')
    def test_workflow_with_large_files(self, mock_send_to_aidbox):
        """Test workflow with larger file content."""
        mock_send_to_aidbox.return_value = (True, {"status": "success"})
        
        # Create a larger test file
        large_content = "This is a line of content.\n" * 1000  # ~26KB file
        file_path = os.path.join(self.temp_dir, "large_file.txt")
        with open(file_path, 'w') as f:
            f.write(large_content)
        
        # Execute workflow
        result = self.processor.process_new_files()
        
        # Verify results
        assert result == 1
        assert mock_send_to_aidbox.call_count == 1
        
        # Verify the large content was passed correctly
        args, kwargs = mock_send_to_aidbox.call_args
        assert args[0] == large_content
        assert args[1] == "large_file.txt"
    
    @patch('src.file_processor.send_to_aidbox')
    def test_workflow_with_different_file_types(self, mock_send_to_aidbox):
        """Test workflow processes different file types correctly."""
        mock_send_to_aidbox.return_value = (True, {"status": "success"})
        
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
        assert mock_send_to_aidbox.call_count == len(test_files)
        
        # Verify each file was sent with correct content
        calls = mock_send_to_aidbox.call_args_list
        sent_files = {}
        for args, kwargs in calls:
            content, filename = args[0], args[1]
            sent_files[filename] = content
        
        for filename, expected_content in test_files.items():
            assert filename in sent_files
            assert sent_files[filename] == expected_content


if __name__ == "__main__":
    pytest.main([__file__])