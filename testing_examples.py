"""
Testing Strategies for API Integration
Comprehensive testing examples for technical interviews
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import requests
import json
from typing import Dict, Any, List
import time

# Import our API client classes
from api_client_example import APIClient, APIResponse
from error_handling_examples import RobustAPIClient, ErrorType, APIError

class TestAPIClient(unittest.TestCase):
    """Test cases for API client functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = APIClient(
            base_url="https://api.test.com",
            api_key="test-api-key"
        )
    
    @patch('requests.Session.request')
    def test_successful_get_request(self, mock_request):
        """Test successful GET request"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"users": [{"id": 1, "name": "John"}]}
        mock_request.return_value = mock_response
        
        # Test the method
        result = self.client.get_users(limit=10)
        
        # Assertions
        self.assertTrue(result.success)
        self.assertEqual(result.status_code, 200)
        self.assertIn("users", result.data)
        self.assertEqual(len(result.data["users"]), 1)
        
        # Verify request was made correctly
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        self.assertEqual(call_args[1]['method'], 'GET')
        self.assertIn('/users', call_args[1]['url'])
        self.assertEqual(call_args[1]['params']['limit'], 10)
    
    @patch('requests.Session.request')
    def test_authentication_error(self, mock_request):
        """Test authentication error handling"""
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_request.return_value = mock_response
        
        result = self.client.get_users()
        
        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 401)
        self.assertEqual(result.error, "Authentication failed")
    
    @patch('requests.Session.request')
    def test_rate_limiting(self, mock_request):
        """Test rate limiting handling"""
        # Mock 429 response with Retry-After header
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '60'}
        mock_request.return_value = mock_response
        
        result = self.client.get_users()
        
        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 429)
    
    @patch('requests.Session.request')
    def test_server_error_with_retry(self, mock_request):
        """Test server error with retry logic"""
        # Mock 500 response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_request.return_value = mock_response
        
        result = self.client.get_users()
        
        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 500)
    
    def test_input_validation(self):
        """Test input validation"""
        # Test invalid user ID
        result = self.client.get_user("")
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Invalid user ID")
        
        # Test malicious user ID
        result = self.client.get_user("'; DROP TABLE users; --")
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Invalid user ID format")
    
    def test_user_creation_validation(self):
        """Test user creation input validation"""
        # Test missing required fields
        result = self.client.create_user({"name": "John"})  # Missing email
        self.assertFalse(result.success)
        self.assertIn("Missing required field", result.error)
        
        # Test invalid email
        result = self.client.create_user({
            "name": "John",
            "email": "invalid-email"
        })
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Invalid email format")
    
    @patch('requests.Session.request')
    def test_timeout_handling(self, mock_request):
        """Test timeout handling"""
        # Mock timeout exception
        mock_request.side_effect = requests.exceptions.Timeout()
        
        result = self.client.get_users()
        
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Request timeout")

class TestRobustAPIClient(unittest.TestCase):
    """Test cases for robust API client with error handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = RobustAPIClient(
            base_url="https://api.test.com",
            api_key="test-api-key"
        )
    
    @patch('requests.Session.request')
    def test_retry_logic(self, mock_request):
        """Test retry logic for recoverable errors"""
        # Mock sequence: 500 error, then success
        error_response = Mock()
        error_response.status_code = 500
        
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"success": True}
        
        mock_request.side_effect = [error_response, success_response]
        
        result = self.client.get("/test")
        
        self.assertTrue(result['success'])
        self.assertEqual(mock_request.call_count, 2)
    
    @patch('requests.Session.request')
    def test_no_retry_for_auth_error(self, mock_request):
        """Test that auth errors are not retried"""
        # Mock 401 response
        error_response = Mock()
        error_response.status_code = 401
        mock_request.return_value = error_response
        
        result = self.client.get("/test")
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error_type'], 'auth_error')
        self.assertEqual(mock_request.call_count, 1)  # No retry
    
    def test_error_classification(self):
        """Test error classification logic"""
        # Test timeout error
        timeout_exception = requests.exceptions.Timeout()
        error = self.client._classify_error(timeout_exception)
        self.assertEqual(error.error_type, ErrorType.TIMEOUT_ERROR)
        
        # Test connection error
        conn_exception = requests.exceptions.ConnectionError()
        error = self.client._classify_error(conn_exception)
        self.assertEqual(error.error_type, ErrorType.NETWORK_ERROR)
    
    def test_retry_strategy(self):
        """Test retry strategy logic"""
        # Test that auth errors are not retried
        auth_error = APIError(ErrorType.AUTHENTICATION_ERROR, "Auth failed")
        should_retry = self.client.retry_strategy.should_retry(auth_error, 0)
        self.assertFalse(should_retry)
        
        # Test that server errors are retried
        server_error = APIError(ErrorType.SERVER_ERROR, "Server error", 500)
        should_retry = self.client.retry_strategy.should_retry(server_error, 0)
        self.assertTrue(should_retry)
        
        # Test max retries exceeded
        should_retry = self.client.retry_strategy.should_retry(server_error, 3)
        self.assertFalse(should_retry)

class TestSecurityUtils(unittest.TestCase):
    """Test cases for security utilities"""
    
    def test_input_validation(self):
        """Test input validation and sanitization"""
        from security_examples import SecurityUtils
        
        # Test valid input
        is_valid, result = SecurityUtils.validate_input("John Doe", "name")
        self.assertTrue(is_valid)
        self.assertEqual(result, "John Doe")
        
        # Test SQL injection attempt
        is_valid, result = SecurityUtils.validate_input("'; DROP TABLE users; --", "name")
        self.assertFalse(is_valid)
        self.assertIn("malicious", result)
        
        # Test XSS attempt
        is_valid, result = SecurityUtils.validate_input("<script>alert('xss')</script>", "name")
        self.assertFalse(is_valid)
        self.assertIn("malicious", result)
    
    def test_email_validation(self):
        """Test email validation"""
        from security_examples import SecurityUtils
        
        # Test valid email
        result = SecurityUtils.sanitize_email("user@example.com")
        self.assertEqual(result, "user@example.com")
        
        # Test invalid email
        result = SecurityUtils.sanitize_email("invalid-email")
        self.assertIsNone(result)
        
        # Test email sanitization
        result = SecurityUtils.sanitize_email("  USER@EXAMPLE.COM  ")
        self.assertEqual(result, "user@example.com")
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        from security_examples import SecurityUtils
        
        password = "testPassword123"
        hashed, salt = SecurityUtils.hash_password(password)
        
        # Test that hash is different from password
        self.assertNotEqual(hashed, password)
        self.assertIsNotNone(salt)
        
        # Test password verification
        is_valid = SecurityUtils.verify_password(password, hashed, salt)
        self.assertTrue(is_valid)
        
        # Test wrong password
        is_valid = SecurityUtils.verify_password("wrongPassword", hashed, salt)
        self.assertFalse(is_valid)

class TestIntegration(unittest.TestCase):
    """Integration tests for complete API workflow"""
    
    @patch('requests.Session.request')
    def test_complete_user_workflow(self, mock_request):
        """Test complete user CRUD workflow"""
        client = APIClient("https://api.test.com", "test-key")
        
        # Mock responses for different operations
        responses = [
            # GET users
            Mock(status_code=200, json=lambda: {"users": [{"id": 1, "name": "John"}]}),
            # GET specific user
            Mock(status_code=200, json=lambda: {"id": 1, "name": "John", "email": "john@test.com"}),
            # CREATE user
            Mock(status_code=201, json=lambda: {"id": 2, "name": "Jane", "email": "jane@test.com"}),
            # UPDATE user
            Mock(status_code=200, json=lambda: {"id": 1, "name": "John Updated", "email": "john@test.com"}),
            # DELETE user
            Mock(status_code=204, json=lambda: None)
        ]
        
        mock_request.side_effect = responses
        
        # Test workflow
        # 1. Get users
        result = client.get_users()
        self.assertTrue(result.success)
        
        # 2. Get specific user
        result = client.get_user("1")
        self.assertTrue(result.success)
        
        # 3. Create user
        result = client.create_user({"name": "Jane", "email": "jane@test.com"})
        self.assertTrue(result.success)
        
        # 4. Update user
        result = client.update_user("1", {"name": "John Updated"})
        self.assertTrue(result.success)
        
        # 5. Delete user
        result = client.delete_user("1")
        self.assertTrue(result.success)

class MockAPIServer:
    """Mock API server for testing"""
    
    def __init__(self):
        self.users = {}
        self.next_id = 1
    
    def handle_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Handle mock API requests"""
        if endpoint == "/users":
            if method == "GET":
                return {"users": list(self.users.values())}
            elif method == "POST":
                user_id = str(self.next_id)
                self.next_id += 1
                user = {"id": user_id, **data}
                self.users[user_id] = user
                return user
        
        elif endpoint.startswith("/users/"):
            user_id = endpoint.split("/")[-1]
            
            if method == "GET":
                if user_id in self.users:
                    return self.users[user_id]
                else:
                    return {"error": "User not found"}, 404
            
            elif method == "PUT":
                if user_id in self.users:
                    self.users[user_id].update(data)
                    return self.users[user_id]
                else:
                    return {"error": "User not found"}, 404
            
            elif method == "DELETE":
                if user_id in self.users:
                    del self.users[user_id]
                    return None, 204
                else:
                    return {"error": "User not found"}, 404
        
        return {"error": "Not found"}, 404

def run_performance_tests():
    """Run performance tests"""
    print("=== Performance Tests ===")
    
    # Test concurrent requests
    import threading
    import time
    
    results = []
    
    def make_request(client, endpoint):
        start_time = time.time()
        result = client.get(endpoint)
        end_time = time.time()
        results.append({
            'endpoint': endpoint,
            'success': result['success'],
            'duration': end_time - start_time
        })
    
    # Create multiple threads
    client = RobustAPIClient("https://api.test.com", "test-key")
    threads = []
    
    for i in range(10):
        thread = threading.Thread(target=make_request, args=(client, f"/test/{i}"))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Analyze results
    successful_requests = sum(1 for r in results if r['success'])
    avg_duration = sum(r['duration'] for r in results) / len(results)
    
    print(f"Successful requests: {successful_requests}/{len(results)}")
    print(f"Average duration: {avg_duration:.3f}s")

if __name__ == "__main__":
    # Run unit tests
    print("Running unit tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run performance tests
    print("\n" + "="*50)
    run_performance_tests()