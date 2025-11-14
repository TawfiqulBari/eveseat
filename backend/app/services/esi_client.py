"""
EVE Online ESI API Client

Handles OAuth 2.0 + PKCE authentication, rate limiting, ETag support, and error handling
"""
import httpx
import hashlib
import base64
import secrets
import time
import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlencode, parse_qs, urlparse
from datetime import datetime, timedelta
import redis
import json
from app.core.config import settings
from app.core.encryption import encryption

logger = logging.getLogger(__name__)


class ESIError(Exception):
    """Base exception for ESI API errors"""
    pass


class ESIRateLimitError(ESIError):
    """ESI rate limit exceeded"""
    pass


class ESITokenError(ESIError):
    """ESI token error (expired, invalid, etc.)"""
    pass


class ESIClient:
    """
    EVE Online ESI API Client
    
    Features:
    - OAuth 2.0 + PKCE authentication
    - Automatic token refresh
    - Rate limiting with Redis
    - ETag support for caching
    - Error handling with exponential backoff
    """
    
    def __init__(self):
        self.base_url = settings.ESI_BASE_URL
        self.client_id = settings.ESI_CLIENT_ID
        self.client_secret = settings.ESI_CLIENT_SECRET
        self.callback_url = settings.ESI_CALLBACK_URL
        self.sso_auth_url = settings.ESI_SSO_AUTH_URL
        self.sso_token_url = settings.ESI_SSO_TOKEN_URL
        
        # HTTP client with timeout
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
        )
        
        # Redis for rate limiting and caching
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Rate limiting will be disabled.")
            self.redis_client = None
    
    def generate_pkce_pair(self) -> Tuple[str, str]:
        """
        Generate PKCE code verifier and code challenge
        
        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        # Generate random code verifier (43-128 characters)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        
        # Generate code challenge (SHA256 hash of verifier)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode('utf-8').rstrip('=')
        
        return code_verifier, code_challenge
    
    def get_authorization_url(self, state: str = None) -> Tuple[str, str]:
        """
        Generate OAuth 2.0 authorization URL with PKCE
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Tuple of (authorization_url, code_verifier)
        """
        if state is None:
            state = secrets.token_urlsafe(32)
        
        code_verifier, code_challenge = self.generate_pkce_pair()
        
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.callback_url,
            "scope": " ".join(settings.ESI_SCOPES),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        
        auth_url = f"{self.sso_auth_url}?{urlencode(params)}"
        
        # Store code_verifier in Redis with state as key (expires in 10 minutes)
        if self.redis_client:
            try:
                self.redis_client.setex(
                    f"esi:pkce:{state}",
                    600,  # 10 minutes
                    code_verifier
                )
            except Exception as e:
                logger.warning(f"Failed to store PKCE verifier: {e}")
        
        return auth_url, code_verifier
    
    def get_pkce_verifier(self, state: str) -> Optional[str]:
        """
        Retrieve PKCE code verifier by state
        
        Args:
            state: State parameter used during authorization
            
        Returns:
            Code verifier or None if not found/expired
        """
        if not self.redis_client:
            return None
        
        try:
            return self.redis_client.get(f"esi:pkce:{state}")
        except Exception as e:
            logger.warning(f"Failed to retrieve PKCE verifier: {e}")
            return None
    
    async def exchange_code_for_token(
        self,
        code: str,
        code_verifier: str,
        state: str = None
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token
        
        Args:
            code: Authorization code from callback
            code_verifier: PKCE code verifier
            state: Optional state parameter
            
        Returns:
            Token response with access_token, refresh_token, expires_in, etc.
        """
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "code_verifier": code_verifier,
        }
        
        # EVE SSO uses HTTP Basic Auth
        auth = (self.client_id, self.client_secret)
        
        try:
            response = await self.client.post(
                self.sso_token_url,
                data=data,
                auth=auth,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Token exchange failed: {e.response.text}")
            raise ESITokenError(f"Failed to exchange code for token: {e.response.text}")
        except Exception as e:
            logger.error(f"Token exchange error: {e}")
            raise ESITokenError(f"Token exchange failed: {str(e)}")
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Encrypted refresh token (will be decrypted)
            
        Returns:
            New token response
        """
        # Decrypt refresh token
        try:
            decrypted_refresh = encryption.decrypt(refresh_token)
        except Exception as e:
            logger.error(f"Failed to decrypt refresh token: {e}")
            raise ESITokenError("Invalid refresh token")
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": decrypted_refresh,
        }
        
        auth = (self.client_id, self.client_secret)
        
        try:
            response = await self.client.post(
                self.sso_token_url,
                data=data,
                auth=auth,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Token refresh failed: {e.response.text}")
            raise ESITokenError(f"Failed to refresh token: {e.response.text}")
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise ESITokenError(f"Token refresh failed: {str(e)}")
    
    async def check_rate_limit(self, endpoint: str) -> Tuple[bool, Optional[int]]:
        """
        Check if request is within rate limits
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        if not self.redis_client:
            return True, None
        
        # ESI rate limits: 100 requests per second per endpoint
        # We'll use a sliding window approach
        key = f"esi:ratelimit:{endpoint}"
        
        try:
            current = int(self.redis_client.get(key) or 0)
            if current >= 100:
                # Check TTL for retry_after
                ttl = self.redis_client.ttl(key)
                return False, ttl if ttl > 0 else 1
            
            # Increment counter
            pipe = self.redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, 1)  # 1 second window
            pipe.execute()
            
            return True, None
        except Exception as e:
            logger.warning(f"Rate limit check failed: {e}")
            return True, None  # Allow on error
    
    async def get_etag(self, endpoint: str) -> Optional[str]:
        """
        Get stored ETag for an endpoint
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            ETag value or None
        """
        if not self.redis_client:
            return None
        
        try:
            return self.redis_client.get(f"esi:etag:{endpoint}")
        except Exception as e:
            logger.warning(f"ETag retrieval failed: {e}")
            return None
    
    def store_etag(self, endpoint: str, etag: str, ttl: int = 3600):
        """
        Store ETag for an endpoint
        
        Args:
            endpoint: API endpoint path
            etag: ETag value
            ttl: Time to live in seconds (default 1 hour)
        """
        if not self.redis_client:
            return
        
        try:
            self.redis_client.setex(f"esi:etag:{endpoint}", ttl, etag)
        except Exception as e:
            logger.warning(f"ETag storage failed: {e}")
    
    async def request(
        self,
        method: str,
        endpoint: str,
        access_token: Optional[str] = None,
        params: Optional[Dict] = None,
        use_etag: bool = True,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Make an ESI API request with rate limiting and ETag support
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path (e.g., "/characters/{character_id}/")
            access_token: Optional access token (decrypted)
            params: Optional query parameters
            use_etag: Whether to use ETag caching
            max_retries: Maximum number of retries on failure
            
        Returns:
            Response JSON data
        """
        # Check rate limit
        allowed, retry_after = await self.check_rate_limit(endpoint)
        if not allowed:
            raise ESIRateLimitError(f"Rate limit exceeded. Retry after {retry_after} seconds")
        
        # Build URL
        url = f"{self.base_url}{endpoint}"
        
        # Prepare headers
        headers = {}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        
        # Add ETag if available
        if use_etag and method.upper() == "GET":
            etag = await self.get_etag(endpoint)
            if etag:
                headers["If-None-Match"] = etag
        
        # Retry logic with exponential backoff
        last_exception = None
        for attempt in range(max_retries):
            try:
                response = await self.client.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                )
                
                # Handle 304 Not Modified (ETag hit)
                if response.status_code == 304:
                    # Return cached data if available
                    cached_data = await self.get_cached_response(endpoint)
                    if cached_data:
                        return cached_data
                    # If no cache, treat as 200
                    response = await self.client.request(method, url, headers={**headers, "If-None-Match": None}, params=params)
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if attempt < max_retries - 1:
                        await asyncio.sleep(min(retry_after, 60))
                        continue
                    raise ESIRateLimitError(f"Rate limit exceeded. Retry after {retry_after} seconds")
                
                response.raise_for_status()
                
                # Store ETag if present
                if use_etag and "ETag" in response.headers:
                    self.store_etag(endpoint, response.headers["ETag"])
                
                # Cache successful GET responses
                if method.upper() == "GET" and response.status_code == 200:
                    await self.cache_response(endpoint, response.json())
                
                return response.json()
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise ESITokenError("Authentication failed - token may be expired")
                if e.response.status_code == 429:
                    last_exception = ESIRateLimitError(f"Rate limit exceeded")
                    if attempt < max_retries - 1:
                        retry_after = int(e.response.headers.get("Retry-After", 60))
                        await asyncio.sleep(min(retry_after, 60))
                        continue
                last_exception = ESIError(f"API request failed: {e.response.text}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
            except Exception as e:
                last_exception = ESIError(f"Request failed: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
        
        if last_exception:
            raise last_exception
        raise ESIError("Request failed after retries")
    
    async def get_cached_response(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Get cached response data"""
        if not self.redis_client:
            return None
        
        try:
            cached = self.redis_client.get(f"esi:cache:{endpoint}")
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
        return None
    
    async def cache_response(self, endpoint: str, data: Dict[str, Any], ttl: int = 300):
        """Cache response data"""
        if not self.redis_client:
            return
        
        try:
            self.redis_client.setex(
                f"esi:cache:{endpoint}",
                ttl,
                json.dumps(data)
            )
        except Exception as e:
            logger.warning(f"Cache storage failed: {e}")
    
    async def get_character_info(self, character_id: int, access_token: str) -> Dict[str, Any]:
        """Get character information"""
        return await self.request(
            "GET",
            f"/characters/{character_id}/",
            access_token=access_token,
        )
    
    async def verify_token(self, access_token: str) -> Dict[str, Any]:
        """
        Verify and decode access token (JWT)
        
        Returns character information from token
        """
        # EVE SSO tokens are JWTs, but we can also use the /verify endpoint
        return await self.request(
            "GET",
            "/verify/",
            access_token=access_token,
        )
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Global instance
esi_client = ESIClient()

