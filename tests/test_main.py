"""
Unit tests for main launcher and scheduling logic.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import time

from main import (
    main, 
    run_scheduler, 
    process_files_job
)


class TestProcessFilesJob(unittest.TestCase):
    """Test cases for process_files_job function."""
    
    @patch('main.process_new_files')
    @patch('main.log_info')
    def test_process_files_job_success(self, mock_log_info, mock_process_files):
        """Test successful file processing job."""
        # Setup mocks
        mock_process_files.return_value = 3
        
        # Execute
        result = process_files_job()
        
        # Verify
        self.assertEqual(result, 3)
        mock_process_files.assert_called_once()
        mock_log_info.assert_called_once_with("Processed files: 3")
    
    @patch('main.process_new_files')
    def test_process_files_job_no_files(self, mock_process_files):
        """Test file processing job when no files are processed."""
        # Setup mocks
        mock_process_files.return_value = 0
        
        # Execute
        result = process_files_job()
        
        # Verify
        self.assertEqual(result, 0)
        mock_process_files.assert_called_once()
    
    @patch('main.process_new_files')
    @patch('main.log_error')
    def test_process_files_job_exception(self, mock_log_error, mock_process_files):
        """Test file processing job handles exceptions."""
        # Setup mocks
        mock_process_files.side_effect = Exception("Test error")
        
        # Execute
        result = process_files_job()
        
        # Verify
        self.assertEqual(result, 0)
        mock_log_error.assert_called_once_with("Error processing files", mock_process_files.side_effect)


class TestRunScheduler(unittest.TestCase):
    """Test cases for run_scheduler function."""
    
    @patch('main.config')
    @patch('main.process_files_job')
    @patch('main.time.sleep')
    @patch('main.log_info')
    def test_run_scheduler_single_cycle(self, mock_log_info, mock_sleep, mock_process_job, mock_config):
        """Test scheduler runs single cycle before KeyboardInterrupt."""
        # Setup mocks
        mock_config.get_schedule_interval.return_value = 10
        mock_process_job.return_value = 2
        mock_sleep.side_effect = KeyboardInterrupt()  # Stop after first cycle
        
        # Execute
        run_scheduler()
        
        # Verify
        mock_process_job.assert_called_once()
        mock_sleep.assert_called_once_with(10)
        mock_log_info.assert_any_call("Starting scheduler with 10 second intervals")
        mock_log_info.assert_any_call("Cycle #1")
        mock_log_info.assert_any_call("Received stop signal")
    
    @patch('main.config')
    @patch('main.process_files_job')
    @patch('main.time.sleep')
    @patch('main.log_info')
    def test_run_scheduler_multiple_cycles(self, mock_log_info, mock_sleep, mock_process_job, mock_config):
        """Test scheduler runs multiple cycles."""
        # Setup mocks
        mock_config.get_schedule_interval.return_value = 5
        mock_process_job.return_value = 1
        
        # Stop after 3 cycles
        call_count = [0]
        def sleep_side_effect(interval):
            call_count[0] += 1
            if call_count[0] >= 3:
                raise KeyboardInterrupt()
        
        mock_sleep.side_effect = sleep_side_effect
        
        # Execute
        run_scheduler()
        
        # Verify
        self.assertEqual(mock_process_job.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 3)
    
    @patch('main.config')
    @patch('main.process_files_job')
    @patch('main.time.sleep')
    @patch('main.log_error')
    def test_run_scheduler_job_exception(self, mock_log_error, mock_sleep, mock_process_job, mock_config):
        """Test scheduler handles job exceptions."""
        # Setup mocks
        mock_config.get_schedule_interval.return_value = 5
        mock_process_job.side_effect = Exception("Test error")
        mock_sleep.side_effect = KeyboardInterrupt()  # Stop after first cycle
        
        # Execute
        run_scheduler()
        
        # Verify
        mock_log_error.assert_any_call("Error in cycle #1", mock_process_job.side_effect)
    
    @patch('main.config')
    @patch('main.process_files_job')
    @patch('main.time.sleep')
    @patch('main.log_error')
    def test_run_scheduler_critical_error(self, mock_log_error, mock_sleep, mock_process_job, mock_config):
        """Test scheduler handles critical errors."""
        # Setup mocks - error occurs during processing
        mock_config.get_schedule_interval.return_value = 5
        test_error = Exception("Critical error")
        mock_process_job.side_effect = test_error
        mock_sleep.side_effect = KeyboardInterrupt()  # Stop after first cycle
        
        # Execute
        run_scheduler()
        
        # Verify error was logged
        mock_log_error.assert_any_call("Error in cycle #1", test_error)


class TestMain(unittest.TestCase):
    """Test cases for main function."""
    
    @patch('main.setup_logger')
    @patch('main.config')
    @patch('main.run_scheduler')
    @patch('main.log_info')
    def test_main_success(self, mock_log_info, mock_run_scheduler, mock_config, mock_setup_logger):
        """Test main function successful execution."""
        # Setup mocks
        mock_config.validate.return_value = True
        
        # Execute
        main()
        
        # Verify
        mock_setup_logger.assert_called_once()
        mock_config.validate.assert_called_once()
        mock_run_scheduler.assert_called_once()
        mock_log_info.assert_any_call("Starting file processor application...")
        mock_log_info.assert_any_call("Configuration is valid")
    
    @patch('main.setup_logger')
    @patch('main.config')
    @patch('main.log_error')
    def test_main_config_validation_failure(self, mock_log_error, mock_config, mock_setup_logger):
        """Test main function when configuration validation fails."""
        # Setup mocks
        mock_config.validate.return_value = False
        
        # Execute
        main()
        
        # Verify
        mock_setup_logger.assert_called_once()
        mock_config.validate.assert_called_once()
        mock_log_error.assert_called_once_with("Configuration validation failed")
    
    @patch('main.setup_logger')
    @patch('main.config')
    @patch('main.run_scheduler')
    @patch('main.log_info')
    def test_main_keyboard_interrupt(self, mock_log_info, mock_run_scheduler, mock_config, mock_setup_logger):
        """Test main function handles keyboard interrupt."""
        # Setup mocks
        mock_config.validate.return_value = True
        mock_run_scheduler.side_effect = KeyboardInterrupt()
        
        # Execute
        main()
        
        # Verify
        mock_log_info.assert_any_call("Application stopped by user")
    
    @patch('main.setup_logger')
    @patch('main.config')
    @patch('main.log_error')
    @patch('main.sys.exit')
    def test_main_critical_error(self, mock_exit, mock_log_error, mock_config, mock_setup_logger):
        """Test main function handles critical errors."""
        # Setup mocks
        mock_config.validate.side_effect = Exception("Critical error")
        
        # Execute
        main()
        
        # Verify
        mock_log_error.assert_called_once_with("Critical error", mock_config.validate.side_effect)
        mock_exit.assert_called_once_with(1)


if __name__ == '__main__':
    unittest.main()