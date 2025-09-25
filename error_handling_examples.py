"""
Robust Error Handling for API Integration
Comprehensive error handling patterns for technical interviews
"""

import requests
import time
import logging
from typing import Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ErrorType(Enum):
    """Types of errors that can occur"""
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    AUTHENTICATION_ERROR = "auth_error"
    AUTHORIZATION_ERROR = "authorization_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    SERVER_ERROR = "server_error"
    CLIENT_ERROR = "client_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN_ERROR = "unknown_error"

@dataclass
class APIError:
    """Structured error information"""
    error_type: ErrorType
    message: str
    status_code: Optional[int] = None
    retry_after: Optional[int] = None
    timestamp: datetime = None
    original_exception: Optional[Exception] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class RetryStrategy:
    """Configurable retry strategy"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 60.0, backoff_factor: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
    
    def should_retry(self, error: APIError, attempt: int) -> bool:
        """Determine if request should be retried"""
        if attempt >= self.max_retries:
            return False
        
        # Don't retry client errors (4xx) except rate limiting
        if error.error_type == ErrorType.CLIENT_ERROR and error.status_code != 429:
            return False
        
        # Don't retry authentication errors
        if error.error_type == ErrorType.AUTHENTICATION_ERROR:
            return False
        
        # Retry network, timeout, server errors, and rate limiting
        retryable_errors = [
            ErrorType.NETWORK_ERROR,
            ErrorType.TIMEOUT_ERROR,
            ErrorType.SERVER_ERROR,
            ErrorType.RATE_LIMIT_ERROR
        ]
        
        return error.error_type in retryable_errors
    
    def get_delay(self, attempt: int, error: APIError) -> float:
        """Calculate delay before retry"""
        if error.error_type == ErrorType.RATE_LIMIT_ERROR and error.retry_after:
            return float(error.retry_after)
        
        # Exponential backoff with jitter
        delay = min(
            self.base_delay * (self.backoff_factor ** attempt),
            self.max_delay
        )
        
        # Add jitter to prevent thundering herd
        jitter = delay * 0.1 * (0.5 - time.time() % 1)
        return delay + jitter

class ErrorHandler:
    """Centralized error handling"""
    
    def __init__(self, retry_strategy: Optional[RetryStrategy] = None):
        self.retry_strategy = retry_strategy or RetryStrategy()
        self.error_callbacks: Dict[ErrorType, Callable] = {}
    
    def register_callback(self, error_type: ErrorType, callback: Callable):
        """Register callback for specific error type"""
        self.error_callbacks[error_type] = callback
    
    def handle_error(self, error: APIError) -> bool:
        """Handle error and return True if handled"""
        logger.error(f"Handling error: {error.error_type.value} - {error.message}")
        
        # Call registered callback if available
        if error.error_type in self.error_callbacks:
            try:
                self.error_callbacks[error.error_type](error)
                return True
            except Exception as e:
                logger.error(f"Error callback failed: {str(e)}")
        
        # Default error handling
        return self._default_error_handling(error)
    
    def _default_error_handling(self, error: APIError) -> bool:
        """Default error handling logic"""
        if error.error_type == ErrorType.AUTHENTICATION_ERROR:
            logger.critical("Authentication failed - check API credentials")
            return False
        
        elif error.error_type == ErrorType.RATE_LIMIT_ERROR:
            logger.warning(f"Rate limited - retry after {error.retry_after} seconds")
            return True
        
        elif error.error_type == ErrorType.SERVER_ERROR:
            logger.error(f"Server error {error.status_code} - will retry")
            return True
        
        elif error.error_type == ErrorType.NETWORK_ERROR:
            logger.error("Network error - will retry")
            return True
        
        else:
            logger.error(f"Unhandled error: {error.error_type.value}")
            return False

class RobustAPIClient:
    """API client with comprehensive error handling"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
        
        # Initialize error handling
        self.error_handler = ErrorHandler()
        self.retry_strategy = RetryStrategy()
        
        # Register error callbacks
        self._setup_error_callbacks()
    
    def _setup_error_callbacks(self):
        """Setup error-specific callbacks"""
        
        def handle_auth_error(error: APIError):
            logger.critical("Authentication failed - stopping all requests")
            # Could implement token refresh logic here
        
        def handle_rate_limit(error: APIError):
            logger.info(f"Rate limited - waiting {error.retry_after} seconds")
            time.sleep(error.retry_after)
        
        def handle_server_error(error: APIError):
            logger.warning(f"Server error {error.status_code} - implementing circuit breaker")
            # Could implement circuit breaker pattern here
        
        self.error_handler.register_callback(ErrorType.AUTHENTICATION_ERROR, handle_auth_error)
        self.error_handler.register_callback(ErrorType.RATE_LIMIT_ERROR, handle_rate_limit)
        self.error_handler.register_callback(ErrorType.SERVER_ERROR, handle_server_error)
    
    def _classify_error(self, exception: Exception, response: Optional[requests.Response] = None) -> APIError:
        """Classify error type based on exception and response"""
        
        if isinstance(exception, requests.exceptions.Timeout):
            return APIError(
                error_type=ErrorType.TIMEOUT_ERROR,
                message="Request timeout",
                original_exception=exception
            )
        
        elif isinstance(exception, requests.exceptions.ConnectionError):
            return APIError(
                error_type=ErrorType.NETWORK_ERROR,
                message="Connection error",
                original_exception=exception
            )
        
        elif response is not None:
            status_code = response.status_code
            
            if status_code == 401:
                return APIError(
                    error_type=ErrorType.AUTHENTICATION_ERROR,
                    message="Authentication failed",
                    status_code=status_code
                )
            
            elif status_code == 403:
                return APIError(
                    error_type=ErrorType.AUTHORIZATION_ERROR,
                    message="Access forbidden",
                    status_code=status_code
                )
            
            elif status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                return APIError(
                    error_type=ErrorType.RATE_LIMIT_ERROR,
                    message="Rate limit exceeded",
                    status_code=status_code,
                    retry_after=retry_after
                )
            
            elif 400 <= status_code < 500:
                return APIError(
                    error_type=ErrorType.CLIENT_ERROR,
                    message=f"Client error: {status_code}",
                    status_code=status_code
                )
            
            elif 500 <= status_code < 600:
                return APIError(
                    error_type=ErrorType.SERVER_ERROR,
                    message=f"Server error: {status_code}",
                    status_code=status_code
                )
        
        return APIError(
            error_type=ErrorType.UNKNOWN_ERROR,
            message=str(exception),
            original_exception=exception
        )
    
    def _make_request_with_retry(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make request with retry logic"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.retry_strategy.max_retries + 1):
            try:
                logger.info(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=30,
                    **kwargs
                )
                
                # Check for successful response
                if response.status_code == 200:
                    return {
                        'success': True,
                        'data': response.json(),
                        'status_code': response.status_code
                    }
                
                # Handle error response
                error = self._classify_error(None, response)
                
                if not self.retry_strategy.should_retry(error, attempt):
                    return {
                        'success': False,
                        'error': error.message,
                        'error_type': error.error_type.value,
                        'status_code': error.status_code
                    }
                
                # Handle error and determine if we should retry
                if not self.error_handler.handle_error(error):
                    return {
                        'success': False,
                        'error': error.message,
                        'error_type': error.error_type.value,
                        'status_code': error.status_code
                    }
                
                # Calculate delay and wait
                delay = self.retry_strategy.get_delay(attempt, error)
                logger.info(f"Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
                
            except requests.exceptions.Timeout as e:
                error = self._classify_error(e)
                if not self.retry_strategy.should_retry(error, attempt):
                    return {
                        'success': False,
                        'error': error.message,
                        'error_type': error.error_type.value
                    }
                
                delay = self.retry_strategy.get_delay(attempt, error)
                logger.warning(f"Timeout - retrying in {delay:.2f} seconds...")
                time.sleep(delay)
                
            except requests.exceptions.ConnectionError as e:
                error = self._classify_error(e)
                if not self.retry_strategy.should_retry(error, attempt):
                    return {
                        'success': False,
                        'error': error.message,
                        'error_type': error.error_type.value
                    }
                
                delay = self.retry_strategy.get_delay(attempt, error)
                logger.warning(f"Connection error - retrying in {delay:.2f} seconds...")
                time.sleep(delay)
                
            except Exception as e:
                error = self._classify_error(e)
                return {
                    'success': False,
                    'error': error.message,
                    'error_type': error.error_type.value
                }
        
        return {
            'success': False,
            'error': 'Max retries exceeded',
            'error_type': 'max_retries_exceeded'
        }
    
    def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """GET request with error handling"""
        return self._make_request_with_retry('GET', endpoint, **kwargs)
    
    def post(self, endpoint: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """POST request with error handling"""
        return self._make_request_with_retry('POST', endpoint, json=data, **kwargs)
    
    def put(self, endpoint: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """PUT request with error handling"""
        return self._make_request_with_retry('PUT', endpoint, json=data, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """DELETE request with error handling"""
        return self._make_request_with_retry('DELETE', endpoint, **kwargs)

# Example usage and testing
def demonstrate_error_handling():
    """Demonstrate error handling capabilities"""
    print("=== Error Handling Examples ===")
    
    # Initialize client
    client = RobustAPIClient(
        base_url="https://api.example.com",
        api_key="your-api-key"
    )
    
    # Test different scenarios
    print("\n1. Testing successful request...")
    response = client.get("/users")
    print(f"  Result: {response}")
    
    print("\n2. Testing error scenarios...")
    
    # Simulate different error types
    error_scenarios = [
        (ErrorType.NETWORK_ERROR, "Simulated network error"),
        (ErrorType.TIMEOUT_ERROR, "Simulated timeout"),
        (ErrorType.RATE_LIMIT_ERROR, "Simulated rate limit", 429, 60),
        (ErrorType.SERVER_ERROR, "Simulated server error", 500),
        (ErrorType.AUTHENTICATION_ERROR, "Simulated auth error", 401)
    ]
    
    for scenario in error_scenarios:
        error = APIError(*scenario)
        print(f"  Testing {error.error_type.value}: {error.message}")
        
        # Test error handling
        handled = client.error_handler.handle_error(error)
        print(f"    Handled: {handled}")
        
        # Test retry logic
        should_retry = client.retry_strategy.should_retry(error, 0)
        print(f"    Should retry: {should_retry}")
        
        if should_retry:
            delay = client.retry_strategy.get_delay(0, error)
            print(f"    Retry delay: {delay:.2f}s")

if __name__ == "__main__":
    demonstrate_error_handling()