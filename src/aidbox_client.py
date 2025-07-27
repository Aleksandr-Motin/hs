"""
Generic Aidbox API client module for REST API communication.
Provides authentication and basic HTTP operations for Aidbox integration.
"""
import json
import time
import base64
from typing import Dict, Any, Optional, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import Config, config
from .logger import log_info, log_error, log_success


class AidboxClient:
    """Client for communicating with Aidbox REST API."""
    
    def __init__(self, config: Config):
        """
        Initialize Aidbox client.
        """
        self.base_url = config.aidbox_base_url
        self.username = config.aidbox_username 
        self.password = config.aidbox_password 
        
        # Validate configuration
        if not self.base_url:
            raise ValueError("Aidbox base URL is required")

        # Validate configuration
        if not self.username or not self.password:
            raise ValueError("Aidbox username and password are required")

        # Determine auth type
        self.auth_type = 'basic'
        self.session = self._create_session()
        
        
    
    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry strategy.
        
        Returns:
            requests.Session: Configured session with retry logic
        """
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            'Content-Type': 'application/json'
        })
        
        # Create Basic auth header
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        session.headers.update({
            'Authorization': f'Basic {encoded_credentials}'
        })
        log_info(f"Using Basic authentication for user: {self.username}")
        
        return session


    def post(self, endpoint: str, payload: Dict[str, Any], timeout: int = 30) -> Tuple[bool, Optional[Dict[str, Any]], Optional[int]]:
        """
        Make a POST request to Aidbox API.
        
        Args:
            endpoint: API endpoint (e.g., 'Hl7v2Message', 'Patient', etc.)
            payload: Request payload as dictionary
            timeout: Request timeout in seconds
            
        Returns:
            Tuple[bool, Optional[Dict], Optional[int]]: (success, response_data, status_code)
        """
        try:
            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            
            response = self.session.post(
                url,
                json=payload,
                timeout=timeout
            )
            
            # Handle response
            if response.status_code in [200, 201]:
                response_data = response.json() if response.content else {}
                # Success logging handled by higher-level handlers (hl7v2_handler)
                return True, response_data, response.status_code
            
            elif response.status_code in [400, 401, 403, 404]:
                # Client errors - don't retry
                error_msg = f"Client error sending request to {endpoint}. Status: {response.status_code}, Response: {response.text}"
                log_error(error_msg)
                return False, None, response.status_code
            
            else:
                # Server errors - already handled by retry logic
                error_msg = f"Server error sending request to {endpoint}. Status: {response.status_code}, Response: {response.text}"
                log_error(error_msg)
                return False, None, response.status_code
                
        except requests.exceptions.Timeout:
            error_msg = f"Timeout error sending request to {endpoint}"
            log_error(error_msg)
            return False, None, None
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error sending request to {endpoint}: {str(e)}"
            log_error(error_msg)
            return False, None, None
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error sending request to {endpoint}: {str(e)}"
            log_error(error_msg)
            return False, None, None
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON decode error processing response from {endpoint}: {str(e)}"
            log_error(error_msg)
            return False, None, None
            
        except Exception as e:
            error_msg = f"Unexpected error sending request to {endpoint}: {str(e)}"
            log_error(error_msg)
            return False, None, None
    
    def get(self, endpoint: str, timeout: int = 30) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Make a GET request to Aidbox API.
        
        Args:
            endpoint: API endpoint (e.g., 'Patient/123', 'metadata', etc.)
            timeout: Request timeout in seconds
            
        Returns:
            Tuple[bool, Optional[Dict]]: (success, response_data)
        """
        try:
            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            
            response = self.session.get(url, timeout=timeout)
            
            if response.status_code == 200:
                response_data = response.json() if response.content else {}
                log_info(f"Successfully retrieved data from {endpoint}")
                return True, response_data
            else:
                error_msg = f"Error retrieving data from {endpoint}. Status: {response.status_code}, Response: {response.text}"
                log_error(error_msg)
                return False, None
                
        except Exception as e:
            error_msg = f"Error retrieving data from {endpoint}: {str(e)}"
            log_error(error_msg)
            return False, None
    
