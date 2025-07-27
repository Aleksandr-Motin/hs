"""
Simple main launcher with infinite loop.
Runs file processing every 10 seconds.
"""

import time
import signal
import sys

from src.config import config
from src.logger import log_info, log_error, setup_logger
from src.file_processor import process_new_files


def process_files_job():
    """Wrapper function for calling file processor."""
    try:
        processed_count = process_new_files()
        if processed_count > 0:
            log_info(f"Processed files: {processed_count}")
        return processed_count
    except Exception as e:
        log_error("Error processing files", e)
        return 0


def run_scheduler():
    """Infinite loop with 10-second intervals."""
    interval = config.get_schedule_interval()
    log_info(f"Starting scheduler with {interval} second intervals")
    
    cycle = 0
    
    try:
        while True:
            cycle += 1
            log_info(f"Cycle #{cycle}")
            
            try:
                process_files_job()
            except Exception as e:
                log_error(f"Error in cycle #{cycle}", e)
            
            log_info(f"Waiting {interval} seconds...")
            time.sleep(interval)
            
    except KeyboardInterrupt:
        log_info("Received stop signal")
    except Exception as e:
        log_error("Critical error in scheduler", e)
        raise
    finally:
        log_info(f"Scheduler stopped after {cycle} cycles")


def main():
    """Main function."""
    try:
        setup_logger()
        log_info("Starting file processor application...")
        
        if not config.validate():
            log_error("Configuration validation failed")
            return
        
        log_info("Configuration is valid")
        run_scheduler()
        
    except KeyboardInterrupt:
        log_info("Application stopped by user")
    except Exception as e:
        log_error("Critical error", e)
        sys.exit(1)


if __name__ == "__main__":
    main()