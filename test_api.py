#!/usr/bin/env python3
"""
Test script for BullAware API integration
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.services.bullaware_client import BullAwareClient
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_api():
    """Test BullAware API connection and basic endpoints"""
    
    # Load API key from environment
    api_key = "dbf32c91665bbf73c1a2a70fd3627dc787d281479d6b9860"
    base_url = "https://api.bullaware.com/v1"
    
    print(f"Testing BullAware API with key: {api_key[:10]}...")
    
    # Initialize client
    client = BullAwareClient(api_key, base_url)
    
    try:
        # Test 1: Get list of investors
        print("\n=== Test 1: Get investors list ===")
        investors = client.get_investors(limit=5)
        print(f"Response type: {type(investors)}")
        print(f"Response keys: {list(investors.keys()) if isinstance(investors, dict) else 'Not a dict'}")
        print(f"First few investors: {json.dumps(investors, indent=2)[:500]}...")
        
        # Test 2: Get specific investor details (if we have any)
        if isinstance(investors, dict) and 'data' in investors and investors['data']:
            first_investor = investors['data'][0]
            username = first_investor.get('username') or first_investor.get('name') or first_investor.get('id')
            
            if username:
                print(f"\n=== Test 2: Get investor details for {username} ===")
                details = client.get_investor_details(username)
                print(f"Details: {json.dumps(details, indent=2)[:500]}...")
                
                print(f"\n=== Test 3: Get investor metrics for {username} ===")
                metrics = client.get_investor_metrics(username)
                print(f"Metrics: {json.dumps(metrics, indent=2)[:500]}...")
                
                print(f"\n=== Test 4: Get investor portfolio for {username} ===")
                portfolio = client.get_investor_portfolio(username)
                print(f"Portfolio: {json.dumps(portfolio, indent=2)[:500]}...")
        
        print("\n=== API Test Completed Successfully ===")
        return True
        
    except Exception as e:
        print(f"\n=== API Test Failed ===")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_api()

