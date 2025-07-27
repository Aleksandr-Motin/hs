# Design Document

## Overview

The file processor application is a simple Python service that monitors a directory for new files and sends them to an Aidbox REST API. The application follows a straightforward architecture with a main launcher that schedules periodic execution of the core file processing logic. The design prioritizes simplicity and cloud function compatibility while providing robust error handling and logging.

## Architecture

The application uses a simple modular architecture with clear separation of concerns:

```
main.py (launcher) → file_processor.py (core logic) → aidbox_client.py (API client) → logger.py (logging)
```

### Key Components:

- **Main Launcher**: Schedules and orchestrates the file processing
- **File Processor**: Core business logic for file detection and processing
- **Aidbox Client**: Handles REST API communication with Aidbox
- **Logger**: Centralized logging functionality

## Components and Interfaces

### 1. Main Launcher (`main.py`)

**Purpose**: Entry point that schedules periodic execution of file processing

**Key Functions**:

- `main()`: Primary entry point compatible with Google Cloud Functions
- `run_scheduler()`: Implements 10-second interval scheduling
- `process_files_job()`: Wrapper that calls the file processor

**Dependencies**:

- `time` (built-in)
- `file_processor` module

### 2. File Processor (`file_processor.py`)

**Purpose**: Core logic for detecting and processing new files

**Key Functions**:

- `process_new_files(directory_path)`: Main processing function
- `get_new_files(directory_path)`: Detects new files in directory
- `read_file_content(file_path)`: Safely reads file contents
- `mark_file_as_processed(file_path)`: Tracks processed files

**State Management**:

- Uses a simple text file (`processed_files.txt`) to track processed files
- Compares current directory contents with processed file list

**Dependencies**:

- `os`, `glob` (built-in)
- `aidbox_client` module
- `logger` module

### 3. Aidbox Client (`aidbox_client.py`)

**Purpose**: Handles REST API communication with Aidbox

**Key Functions**:

- `send_to_aidbox(file_content, filename)`: Sends file data via POST request
- `configure_client(base_url, auth_token)`: Sets up API client configuration

**Configuration**:

- Base URL for Aidbox API
- Authentication token/credentials
- Request timeout settings
- Retry logic for failed requests

**Dependencies**:

- `requests` library
- `json` (built-in)

### 4. Logger (`logger.py`)

**Purpose**: Centralized logging functionality

**Key Functions**:

- `setup_logger()`: Configures file-based logging
- `log_info(message)`: Logs informational messages
- `log_error(message, exception)`: Logs errors with context
- `log_success(message)`: Logs successful operations

**Log Format**:

- Timestamp, log level, message
- File-based output (`file_processor.log`)
- Rotation to prevent large log files

**Dependencies**:

- `logging` (built-in)
- `datetime` (built-in)

## Data Models

### File Processing State

```python
ProcessedFile = {
    "filename": str,
    "processed_at": datetime,
    "status": str  # "success" | "error"
}
```

### API Request Payload

```python
AidboxPayload = {
    "filename": str,
    "content": str,  # file content as string
    "timestamp": str,
    "source": "file-processor"
}
```

### Configuration

```python
Config = {
    "directory_path": str,
    "aidbox_base_url": str,
    "aidbox_auth_token": str,
    "log_file_path": str,
    "processed_files_path": str
}
```

## Error Handling

### File System Errors

- **File not found**: Log error and continue processing other files
- **Permission denied**: Log error with file path and continue
- **Directory not accessible**: Log error and retry on next cycle

### API Errors

- **Connection timeout**: Log error and retry with exponential backoff
- **HTTP 4xx errors**: Log error details and mark file as failed
- **HTTP 5xx errors**: Log error and implement retry logic
- **Authentication errors**: Log error and halt processing

### Application Errors

- **Configuration missing**: Log error and exit gracefully
- **Logging failures**: Print to console as fallback
- **Unexpected exceptions**: Log full stack trace and continue

## Testing Strategy

### Unit Tests

- **File Processor Tests**: Mock file system operations and test file detection logic
- **Aidbox Client Tests**: Mock HTTP requests and test API communication
- **Logger Tests**: Test log file creation and message formatting
- **Main Launcher Tests**: Test scheduling logic and error handling

### Integration Tests

- **End-to-End Flow**: Test complete file processing workflow with test files
- **API Integration**: Test actual communication with Aidbox API (using test environment)
- **Error Scenarios**: Test behavior with various error conditions

### Test Structure

```
tests/
├── test_file_processor.py
├── test_aidbox_client.py
├── test_logger.py
├── test_main.py
└── fixtures/
    ├── sample_files/
    └── mock_responses/
```

### Google Cloud Functions Compatibility

- **Entry Point**: `main()` function serves as cloud function entry point
- **Dependencies**: Use `requirements.txt` for dependency management
- **Environment Variables**: Support configuration via environment variables
- **Stateless Design**: Avoid local file state that doesn't persist between function invocations
- **Cold Start Optimization**: Minimize initialization time and external dependencies
