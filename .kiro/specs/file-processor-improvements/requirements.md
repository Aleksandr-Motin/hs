# Requirements Document

## Introduction

This feature improves the existing file processor system to handle network failures properly, maintain message ordering, and provide consistent logging. The improvements focus on ensuring data integrity and proper error handling for HL7v2 message processing with Aidbox integration.

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want files to be processed in alphabetical order, so that HL7v2 messages maintain their proper sequence.

#### Acceptance Criteria

1. WHEN the system discovers new files THEN the system SHALL sort them alphabetically by filename
2. WHEN files are processed THEN the system SHALL process them in A-Z order
3. WHEN multiple files exist THEN the system SHALL maintain consistent ordering across processing runs

### Requirement 2

**User Story:** As a data integrator, I want files to be marked as processed only when Aidbox acknowledges receipt, so that no messages are lost due to network issues.

#### Acceptance Criteria

1. WHEN Aidbox returns HTTP 200/201 with successful processing THEN the system SHALL mark the file as processed with "success" status
2. WHEN Aidbox returns HTTP 200/201 but processing fails THEN the system SHALL mark the file as processed with "error" status
3. WHEN HTTP request fails (no 200/201 response) THEN the system SHALL retry endlessly until successful delivery
4. WHEN a file cannot be read THEN the system SHALL retry endlessly until successful read

### Requirement 3

**User Story:** As a system operator, I want the system to retry endlessly on failures, so that no messages are lost and processing continues when issues are resolved.

#### Acceptance Criteria

1. WHEN an HTTP request fails due to network issues THEN the system SHALL retry the same file endlessly until successful
2. WHEN a file read error occurs THEN the system SHALL retry reading the same file endlessly until successful
3. WHEN any failure occurs THEN the system SHALL NOT proceed to the next file until the current file is successfully processed
4. WHEN retrying operations THEN the system SHALL log each retry attempt with appropriate delay between attempts

### Requirement 4

**User Story:** As a system administrator, I want consistent log formatting with filename prefixes, so that I can easily track individual file processing.

#### Acceptance Criteria

1. WHEN logging file-specific operations THEN the system SHALL include [filename] prefix in all log messages
2. WHEN processing a file THEN the system SHALL use consistent log message format
3. WHEN errors occur THEN the system SHALL include the filename context in error messages
4. WHEN successful operations complete THEN the system SHALL log with filename prefix for traceability

### Requirement 5

**User Story:** As a data integrator, I want clear distinction between delivery failures and processing failures, so that I can understand what happened to each message.

#### Acceptance Criteria

1. WHEN HTTP delivery succeeds but Aidbox processing fails THEN the system SHALL log as "delivered but processing failed"
2. WHEN HTTP delivery fails THEN the system SHALL log as "delivery failed"
3. WHEN network connectivity issues occur THEN the system SHALL distinguish from processing errors
4. WHEN logging API results THEN the system SHALL include HTTP status codes and message IDs

### Requirement 6

**User Story:** As a system administrator, I want configurable retry periods, so that I can control the delay between retry attempts based on my environment.

#### Acceptance Criteria

1. WHEN retry attempts are made THEN the system SHALL use a configurable retry delay period
2. WHEN configuration is loaded THEN the system SHALL read retry period from environment variables or config file
3. WHEN retry period is not configured THEN the system SHALL use a sensible default value
4. WHEN retrying operations THEN the system SHALL wait the configured period between attempts
