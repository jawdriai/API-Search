"""
Security Best Practices for API Integration
Common security patterns you should implement in your interview
"""

import hashlib
import hmac
import secrets
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import re

class SecurityUtils:
    """Security utilities for API interactions"""
    
    @staticmethod
    def validate_input(data: Any, field_name: str, max_length: int = 255) -> tuple[bool, str]:
        """Validate and sanitize input data"""
        if data is None:
            return False, f"{field_name} cannot be null"
        
        if isinstance(data, str):
            # Check length
            if len(data) > max_length:
                return False, f"{field_name} exceeds maximum length of {max_length}"
            
            # Check for SQL injection patterns
            sql_patterns = [
                r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b)",
                r"(\b(UNION|OR|AND)\b.*\b(SELECT|INSERT|UPDATE|DELETE)\b)",
                r"(--|\#|\/\*|\*\/)",
                r"(\b(script|javascript|vbscript|onload|onerror)\b)",
            ]
            
            for pattern in sql_patterns:
                if re.search(pattern, data, re.IGNORECASE):
                    return False, f"{field_name} contains potentially malicious content"
            
            return True, data.strip()
        
        return True, data
    
    @staticmethod
    def sanitize_email(email: str) -> Optional[str]:
        """Validate and sanitize email address"""
        if not email or not isinstance(email, str):
            return None
        
        email = email.strip().lower()
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return None
        
        return email
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate cryptographically secure random token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 for password hashing
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 100,000 iterations
        )
        
        return base64.b64encode(password_hash).decode('utf-8'), salt
    
    @staticmethod
    def verify_password(password: str, stored_hash: str, salt: str) -> bool:
        """Verify password against stored hash"""
        password_hash, _ = SecurityUtils.hash_password(password, salt)
        return hmac.compare_digest(password_hash, stored_hash)
    
    @staticmethod
    def create_hmac_signature(data: str, secret: str) -> str:
        """Create HMAC signature for request authentication"""
        return hmac.new(
            secret.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def validate_hmac_signature(data: str, signature: str, secret: str) -> bool:
        """Validate HMAC signature"""
        expected_signature = SecurityUtils.create_hmac_signature(data, secret)
        return hmac.compare_digest(signature, expected_signature)

class SecureAPIClient:
    """Enhanced API client with security features"""
    
    def __init__(self, base_url: str, api_key: str, secret_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.secret_key = secret_key
        self.nonce = None
        self.timestamp = None
    
    def _create_secure_headers(self, method: str, endpoint: str, body: str = "") -> Dict[str, str]:
        """Create secure headers with authentication"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'SecureAPIClient/1.0',
            'X-Request-ID': SecurityUtils.generate_secure_token(16)
        }
        
        # Add timestamp and nonce for replay attack prevention
        self.timestamp = str(int(datetime.now().timestamp()))
        self.nonce = SecurityUtils.generate_secure_token(16)
        
        headers['X-Timestamp'] = self.timestamp
        headers['X-Nonce'] = self.nonce
        
        # Create signature if secret key is provided
        if self.secret_key:
            # Create signature from method, endpoint, timestamp, nonce, and body
            signature_data = f"{method.upper()}{endpoint}{self.timestamp}{self.nonce}{body}"
            signature = SecurityUtils.create_hmac_signature(signature_data, self.secret_key)
            headers['X-Signature'] = signature
        
        return headers
    
    def _validate_response_security(self, response_headers: Dict[str, str]) -> bool:
        """Validate response security headers"""
        security_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Strict-Transport-Security'
        ]
        
        # Check for security headers (not all APIs provide these)
        for header in security_headers:
            if header in response_headers:
                print(f"✓ Security header present: {header}")
        
        return True
    
    def secure_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make secure API request with validation"""
        import requests
        import json
        
        # Validate and sanitize input data
        if data:
            sanitized_data = {}
            for key, value in data.items():
                is_valid, sanitized_value = SecurityUtils.validate_input(value, key)
                if not is_valid:
                    return {
                        'success': False,
                        'error': f'Invalid input: {sanitized_value}',
                        'field': key
                    }
                sanitized_data[key] = sanitized_value
            data = sanitized_data
        
        # Prepare request
        body = json.dumps(data) if data else ""
        headers = self._create_secure_headers(method, endpoint, body)
        
        try:
            # Make request
            response = requests.request(
                method=method,
                url=f"{self.base_url}/{endpoint.lstrip('/')}",
                headers=headers,
                data=body,
                timeout=30
            )
            
            # Validate response security
            self._validate_response_security(response.headers)
            
            return {
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'data': response.json() if response.content else None,
                'headers': dict(response.headers)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Request failed: {str(e)}'
            }

# Example usage
def demonstrate_security():
    """Demonstrate security features"""
    print("=== Security Examples ===")
    
    # Input validation
    print("\n1. Input Validation:")
    validator = SecurityUtils()
    
    test_inputs = [
        ("John Doe", "name"),
        ("john@example.com", "email"),
        ("'; DROP TABLE users; --", "malicious_input"),
        ("<script>alert('xss')</script>", "xss_input")
    ]
    
    for value, field in test_inputs:
        is_valid, result = validator.validate_input(value, field)
        print(f"  {field}: {value} -> Valid: {is_valid}, Result: {result}")
    
    # Email validation
    print("\n2. Email Validation:")
    emails = ["user@example.com", "invalid-email", "user@domain.co.uk", ""]
    for email in emails:
        sanitized = validator.sanitize_email(email)
        print(f"  {email} -> {sanitized}")
    
    # Password hashing
    print("\n3. Password Hashing:")
    password = "mySecurePassword123"
    hashed, salt = validator.hash_password(password)
    print(f"  Password: {password}")
    print(f"  Hash: {hashed}")
    print(f"  Salt: {salt}")
    print(f"  Verification: {validator.verify_password(password, hashed, salt)}")
    
    # HMAC signature
    print("\n4. HMAC Signature:")
    data = "GET/api/users1234567890abcdef"
    secret = "my-secret-key"
    signature = validator.create_hmac_signature(data, secret)
    print(f"  Data: {data}")
    print(f"  Signature: {signature}")
    print(f"  Valid: {validator.validate_hmac_signature(data, signature, secret)}")

if __name__ == "__main__":
    demonstrate_security()