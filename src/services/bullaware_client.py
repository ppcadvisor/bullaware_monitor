import time
import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
from threading import Lock

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter for API requests - 10 requests per minute"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self.lock = Lock()
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limits"""
        with self.lock:
            now = time.time()
            # Remove requests older than time_window
            self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
            
            if len(self.requests) >= self.max_requests:
                # Need to wait
                oldest_request = min(self.requests)
                wait_time = self.time_window - (now - oldest_request) + 1  # +1 for safety
                logger.info(f"Rate limit reached. Waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
                # Clean up again after waiting
                now = time.time()
                self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
            
            # Record this request
            self.requests.append(now)

class BullAwareClient:
    """Client for BullAware API with rate limiting and caching"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.bullaware.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.rate_limiter = RateLimiter()
        self.cache = {}
        self.cache_ttl = {}
        
        # Default cache TTL in seconds
        self.default_ttl = {
            'investors': 3600,  # 1 hour
            'metrics': 1800,    # 30 minutes
            'portfolio': 900,   # 15 minutes
            'trades': 7200,     # 2 hours
            'risk-score': 1800, # 30 minutes
            'copiers': 3600     # 1 hour
        }
    
    def _get_cache_key(self, endpoint: str, params: Dict = None) -> str:
        """Generate cache key for request"""
        key = endpoint
        if params:
            sorted_params = sorted(params.items())
            key += "?" + "&".join([f"{k}={v}" for k, v in sorted_params])
        return key
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.cache:
            return False
        
        if cache_key not in self.cache_ttl:
            return False
        
        return time.time() < self.cache_ttl[cache_key]
    
    def _cache_response(self, cache_key: str, data: Any, ttl_seconds: int):
        """Cache response data"""
        self.cache[cache_key] = data
        self.cache_ttl[cache_key] = time.time() + ttl_seconds
    
    def _get_ttl_for_endpoint(self, endpoint: str) -> int:
        """Get TTL for specific endpoint"""
        for key, ttl in self.default_ttl.items():
            if key in endpoint:
                return ttl
        return 1800  # Default 30 minutes
    
    def _make_request(self, endpoint: str, params: Dict = None, use_cache: bool = True) -> Dict:
        """Make HTTP request to BullAware API"""
        cache_key = self._get_cache_key(endpoint, params)
        
        # Check cache first
        if use_cache and self._is_cache_valid(cache_key):
            logger.info(f"Cache hit for {endpoint}")
            return self.cache[cache_key]
        
        # Rate limiting
        self.rate_limiter.wait_if_needed()
        
        # Prepare request
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        if not params:
            params = {}
        
        try:
            logger.info(f"Making request to {url} with params {params}")
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Cache the response
            if use_cache:
                ttl = self._get_ttl_for_endpoint(endpoint)
                self._cache_response(cache_key, data, ttl)
            
            return data
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                logger.warning("Rate limit exceeded, waiting longer...")
                time.sleep(60)  # Wait 1 minute on rate limit
                return self._make_request(endpoint, params, use_cache)
            else:
                logger.error(f"HTTP error {response.status_code}: {e}")
                raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise
    
    def get_investors(self, limit: int = 100, offset: int = 0) -> Dict:
        """Get list of investors"""
        params = {'limit': limit, 'offset': offset}
        return self._make_request('investors', params)
    
    def get_investor_details(self, username: str) -> Dict:
        """Get investor details by username"""
        return self._make_request(f'investors/{username}')
    
    def get_investor_metrics(self, username: str) -> Dict:
        """Get investor metrics"""
        return self._make_request(f'investors/{username}/metrics')
    
    def get_investor_metrics_history(self, username: str) -> Dict:
        """Get investor historical metrics"""
        return self._make_request(f'investors/{username}/metrics/history')
    
    def get_investor_portfolio(self, username: str) -> Dict:
        """Get investor portfolio"""
        return self._make_request(f'investors/{username}/portfolio')
    
    def get_investor_trades(self, username: str) -> Dict:
        """Get investor trades history"""
        return self._make_request(f'investors/{username}/trades')
    
    def get_investor_risk_score_daily(self, username: str) -> Dict:
        """Get investor daily risk score"""
        return self._make_request(f'investors/{username}/risk-score/daily')
    
    def get_investor_risk_score_monthly(self, username: str) -> Dict:
        """Get investor monthly risk score"""
        return self._make_request(f'investors/{username}/risk-score/monthly')
    
    def get_investor_copiers_history(self, username: str) -> Dict:
        """Get investor copiers history"""
        return self._make_request(f'investors/{username}/copiers/history')
    
    def get_investor_copiers_countries(self, username: str) -> Dict:
        """Get investor copiers by countries"""
        return self._make_request(f'investors/{username}/copiers/countries')
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear()
        self.cache_ttl.clear()
        logger.info("Cache cleared")



# Глобальный экземпляр клиента BullAware
import os
bullaware_client = BullAwareClient(api_key=os.getenv('BULLAWARE_API_KEY', 'dbf32c91665bbf73c1a2a70fd3627dc787d281479d6b9860'))

