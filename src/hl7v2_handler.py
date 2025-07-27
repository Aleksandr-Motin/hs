"""
HL7v2 message handler for Aidbox integration.
Handles the specific logic for sending HL7v2 messages to Aidbox.
"""

from typing import Dict, Any, Optional, Tuple
from .aidbox_client import AidboxClient
from .config import config
from .logger import log_info, log_error


# Global client instance - lazy initialization
_aidbox_client: Optional[AidboxClient] = None


def get_client() -> AidboxClient:
    """Get or create the global Aidbox client instance."""
    global _aidbox_client
    if _aidbox_client is None:
        _aidbox_client = AidboxClient(config)
    return _aidbox_client


def send_hl7v2_message(message_content: str, filename: str = None, max_retries: int = 3) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Send HL7v2 message to Aidbox with retry logic.
    
    Args:
        message_content: HL7v2 message content
        filename: Optional filename for logging purposes
        max_retries: Maximum number of retry attempts for failed HTTP requests
        
    Returns:
        Tuple[bool, Optional[Dict]]: (success, response_data_with_status)
        response_data_with_status includes: original response + http_status_code + error_message if applicable
    """
    prefix = f"[{filename}] " if filename else ""
    log_info(f"{prefix}Sending HL7v2 message to Aidbox")
    
    # Prepare HL7v2Message resource payload
    payload = {
        "resourceType": "Hl7v2Message",
        "src": message_content.strip(),
        "status": "received",
        "config": {
            "resourceType": "Hl7v2Config",
            "id": "default"
        }
    }
    
    client = get_client()
    
    # Retry logic for HTTP request failures
    for attempt in range(max_retries + 1):
        success, response_data, status_code = client.post("Hl7v2Message", payload)
        
        if success and response_data:
            # HTTP request was successful, check HL7v2 processing status
            hl7_status = response_data.get("status", "unknown")
            message_id = response_data.get("id", "unknown")
            
            # Add HTTP status to response data for structured logging
            enhanced_response = {
                **response_data,
                "http_status_code": status_code
            }
            
            if hl7_status == "error":
                # HTTP 200/201 but processing failed
                return False, enhanced_response
            
            elif hl7_status == "processed":
                # Both HTTP and HL7v2 processing successful
                return True, enhanced_response
            
            else:
                # Unknown processing status
                return False, enhanced_response
        
        else:
            # HTTP request failed - retry or return error info
            if attempt < max_retries:
                # Log retry attempt
                log_info(f"{prefix}HL7v2 message send failed (attempt {attempt + 1}/{max_retries + 1}), retrying in {attempt + 1} seconds...")
                
                # Add a small delay before retry
                import time
                time.sleep(1 * (attempt + 1))  # Exponential backoff: 1s, 2s, 3s
            else:
                # Final attempt failed - return error info
                log_error(f"{prefix}HL7v2 message send failed after {max_retries + 1} attempts")
                
                error_response = {
                    "http_status_code": status_code,
                    "error_message": f"Failed to send HL7v2 message after {max_retries + 1} attempts",
                    "final_attempt": True
                }
                return False, error_response
    
    # All attempts failed (shouldn't reach here, but safety fallback)
    return False, {"error_message": "All retry attempts failed", "http_status_code": None}
