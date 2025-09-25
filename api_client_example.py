"""
Example API Client Implementation
This demonstrates common patterns you might need in a technical interview
"""

import requests
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class APIResponse:
    """Standardized response object"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class APIClient:
    """
    Secure API client with authentication, retry logic, and error handling
    """
    
    def __init__(self, base_url: str, api_key: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        
        # Set up default headers
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'SecureAPIClient/1.0'
        })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> APIResponse:
        """
        Make HTTP request with retry logic and error handling
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Making {method} request to {url} (attempt {attempt + 1})")
                
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.timeout,
                    **kwargs
                )
                
                # Handle different status codes
                if response.status_code == 200:
                    return APIResponse(
                        success=True,
                        data=response.json(),
                        status_code=response.status_code
                    )
                elif response.status_code == 401:
                    return APIResponse(
                        success=False,
                        error="Authentication failed",
                        status_code=response.status_code
                    )
                elif response.status_code == 429:
                    # Rate limiting - wait and retry
                    wait_time = int(response.headers.get('Retry-After', retry_delay))
                    logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                elif response.status_code >= 500:
                    # Server error - retry
                    if attempt < max_retries - 1:
                        logger.warning(f"Server error {response.status_code}. Retrying...")
                        time.sleep(retry_delay * (2 ** attempt))
                        continue
                    else:
                        return APIResponse(
                            success=False,
                            error=f"Server error: {response.status_code}",
                            status_code=response.status_code
                        )
                else:
                    return APIResponse(
                        success=False,
                        error=f"Request failed: {response.status_code}",
                        status_code=response.status_code
                    )
                    
            except requests.exceptions.Timeout:
                logger.error(f"Request timeout (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                else:
                    return APIResponse(
                        success=False,
                        error="Request timeout"
                    )
                    
            except requests.exceptions.ConnectionError:
                logger.error(f"Connection error (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                else:
                    return APIResponse(
                        success=False,
                        error="Connection error"
                    )
                    
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                return APIResponse(
                    success=False,
                    error=f"Unexpected error: {str(e)}"
                )
        
        return APIResponse(
            success=False,
            error="Max retries exceeded"
        )
    
    def get_users(self, limit: int = 100, offset: int = 0) -> APIResponse:
        """Get list of users with pagination"""
        params = {
            'limit': min(limit, 1000),  # Security: cap max limit
            'offset': max(offset, 0)  # Security: ensure non-negative
        }
        return self._make_request('GET', '/users', params=params)
    
    def get_user(self, user_id: str) -> APIResponse:
        """Get specific user by ID"""
        # Input validation
        if not user_id or not isinstance(user_id, str):
            return APIResponse(
                success=False,
                error="Invalid user ID"
            )
        
        # Sanitize user ID to prevent injection
        user_id = user_id.strip()
        if not user_id.isalnum():
            return APIResponse(
                success=False,
                error="Invalid user ID format"
            )
        
        return self._make_request('GET', f'/users/{user_id}')
    
    def create_user(self, user_data: Dict[str, Any]) -> APIResponse:
        """Create a new user"""
        # Input validation
        required_fields = ['name', 'email']
        for field in required_fields:
            if field not in user_data or not user_data[field]:
                return APIResponse(
                    success=False,
                    error=f"Missing required field: {field}"
                )
        
        # Validate email format
        email = user_data.get('email', '')
        if '@' not in email or '.' not in email.split('@')[-1]:
            return APIResponse(
                success=False,
                error="Invalid email format"
            )
        
        # Sanitize data
        sanitized_data = {
            'name': str(user_data['name']).strip()[:100],  # Limit length
            'email': str(user_data['email']).strip().lower(),
            'age': user_data.get('age', 0) if isinstance(user_data.get('age'), int) else 0
        }
        
        return self._make_request('POST', '/users', json=sanitized_data)
    
    def update_user(self, user_id: str, update_data: Dict[str, Any]) -> APIResponse:
        """Update user information"""
        # Input validation
        if not user_id or not isinstance(user_id, str):
            return APIResponse(
                success=False,
                error="Invalid user ID"
            )
        
        if not update_data:
            return APIResponse(
                success=False,
                error="No update data provided"
            )
        
        # Sanitize update data
        allowed_fields = ['name', 'email', 'age']
        sanitized_data = {}
        
        for field, value in update_data.items():
            if field in allowed_fields:
                if field == 'name':
                    sanitized_data[field] = str(value).strip()[:100]
                elif field == 'email':
                    if '@' in str(value) and '.' in str(value).split('@')[-1]:
                        sanitized_data[field] = str(value).strip().lower()
                elif field == 'age':
                    if isinstance(value, int) and 0 <= value <= 150:
                        sanitized_data[field] = value
        
        if not sanitized_data:
            return APIResponse(
                success=False,
                error="No valid fields to update"
            )
        
        return self._make_request('PUT', f'/users/{user_id}', json=sanitized_data)
    
    def delete_user(self, user_id: str) -> APIResponse:
        """Delete a user"""
        # Input validation
        if not user_id or not isinstance(user_id, str):
            return APIResponse(
                success=False,
                error="Invalid user ID"
            )
        
        return self._make_request('DELETE', f'/users/{user_id}')

# Example usage and testing
def main():
    """Example usage of the API client"""
    
    # Initialize client
    client = APIClient(
        base_url="https://api.example.com",
        api_key="your-api-key-here"
    )
    
    # Test different operations
    print("=== Testing API Client ===")
    
    # Get users
    print("\n1. Getting users...")
    response = client.get_users(limit=10)
    if response.success:
        print(f"Success: Found {len(response.data.get('users', []))} users")
    else:
        print(f"Error: {response.error}")
    
    # Get specific user
    print("\n2. Getting specific user...")
    response = client.get_user("123")
    if response.success:
        print(f"Success: User data retrieved")
    else:
        print(f"Error: {response.error}")
    
    # Create user
    print("\n3. Creating user...")
    new_user = {
        'name': 'John Doe',
        'email': 'john@example.com',
        'age': 30
    }
    response = client.create_user(new_user)
    if response.success:
        print(f"Success: User created with ID {response.data.get('id')}")
    else:
        print(f"Error: {response.error}")
    
    # Update user
    print("\n4. Updating user...")
    update_data = {'name': 'John Smith', 'age': 31}
    response = client.update_user("123", update_data)
    if response.success:
        print("Success: User updated")
    else:
        print(f"Error: {response.error}")

if __name__ == "__main__":
    main()