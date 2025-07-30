# Design Document

## Overview

This design improves the existing file processor system to handle network failures gracefully, maintain message ordering, and provide consistent logging. The improvements focus on the core processing logic in `src/file_processor.py` while maintaining compatibility with the existing architecture.

## Architecture

The improvements maintain the existing architecture but enhance the error handling and processing flow:

```
File Discovery → File Sorting → Sequential Processing → Error Handling
     ↓              ↓                    ↓                   ↓
  glob.glob()   sort(key=filename)   for each file      Network vs Local
     ↓              ↓                    ↓                   ↓
Filter files   A-Z ordering        Read → Send → Mark    Stop vs Continue
```

## Components and Interfaces

### Enhanced FileProcessor.process_new_files()

**Current Flow Issues:**

- Files marked as processed on network failures
- Processing continues after network failures
- Inconsistent logging format

**Improved Flow:**

1. **File Discovery & Sorting**
   - Get all files in directory
   - Filter out directories and tracking file
   - Sort alphabetically by filename
2. **Sequential Processing**
   - Process files in sorted order
   - Retry endlessly on network failures
   - Retry endlessly on file read errors
3. **Enhanced Error Handling**
   - Distinguish network failures from processing failures
   - Only mark files as processed when Aidbox acknowledges receipt
   - Use `break` for network failures, `continue` for file read errors

### Error Classification

**File Read Errors (Local Issues):**

- File not found, permission denied, encoding errors
- Action: Retry endlessly with configurable delay between attempts
- Logging: File-specific error with retry attempt number
- Processing: Don't mark as processed, keep retrying same file

**Network/Connection Failures:**

- HTTP request failures, timeouts, connection errors
- Action: Retry endlessly with configurable delay between attempts
- Logging: Network failure message with retry attempt number
- Processing: Don't mark as processed, keep retrying same file

**Aidbox Processing Failures:**

- HTTP 200/201 but Aidbox returns processing error
- Action: Mark as processed with "error" status
- Logging: Delivered but processing failed
- Processing: Continue to next file

## Data Models

### Configuration Parameters

**Retry Configuration:**

- `RETRY_DELAY_SECONDS`: Configurable delay between retry attempts (default: 5 seconds)
- Environment variable or config file setting
- Used for both file read errors and network failures

### Processing Status Logic

```python
if response_data and response_data.get("http_status_code") in [200, 201]:
    # Message delivered to Aidbox - mark as processed
    if success:
        mark_file_as_processed(file_path, "success")  # Processing succeeded
    else:
        mark_file_as_processed(file_path, "error")    # Processing failed but delivered
else:
    # HTTP failure - do NOT mark as processed, STOP processing
    break
```

### Log Message Format

All file-specific log messages use consistent format:

```
[filename] Operation description
[filename] HL7v2 sending message - SUCCESS {status: 201, id: abc123} | Processing - SUCCESS
[filename] Network/connection failure - stopping processing to preserve message order
```

## Error Handling

### Network Failure Handling

- Detect HTTP failures (no 200/201 response)
- Log detailed error information
- Stop processing immediately to preserve order
- Don't mark current or subsequent files as processed

### File Read Error Handling

- Log file-specific error with filename prefix
- Skip to next file without marking as processed
- Continue processing remaining files

### Exception Handling

- Catch unexpected exceptions during processing
- Stop processing to be safe (unknown if network-related)
- Log exception details with filename context

## Testing Strategy

### Unit Tests

- Test file sorting logic
- Test error classification (network vs local)
- Test processing flow control (break vs continue)
- Test log message formatting

### Integration Tests

- Test complete processing workflow with network failures
- Test file ordering preservation
- Test processed file tracking accuracy
- Test log output consistency

### Error Scenario Tests

- Network connectivity failures
- Aidbox processing failures
- File read permission errors
- Mixed success/failure scenarios
