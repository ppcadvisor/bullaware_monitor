#!/usr/bin/env python3
"""
Comprehensive test of the BullAware monitoring system
"""
import os
import sys
import time
import requests
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def test_api_endpoint(url, method='GET', data=None, timeout=30):
    """Test API endpoint with error handling"""
    try:
        if method == 'GET':
            response = requests.get(url, timeout=timeout)
        elif method == 'POST':
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, json=data, headers=headers, timeout=timeout)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling {url}: {e}")
        return None

def main():
    """Run comprehensive system test"""
    base_url = "http://localhost:5000/api"
    
    print("=== BullAware Monitoring System Test ===\\n")
    
    # Test 1: Basic API connection
    print("1. Testing basic API connection...")
    result = test_api_endpoint(f"{base_url}/api-test")
    if result and result.get('success'):
        print("✓ API connection successful")
        print(f"  Sample data: {len(result.get('sample_data', {}).get('items', []))} investors found")
    else:
        print("✗ API connection failed")
        return
    
    # Test 2: Test trader scoring
    print("\\n2. Testing trader scoring system...")
    test_username = "JeppeKirkBonde"  # Known good trader from API test
    result = test_api_endpoint(f"{base_url}/test/scoring", 'POST', {'username': test_username})
    if result and result.get('success'):
        trader_data = result['data']
        print(f"✓ Trader scoring successful for {test_username}")
        print(f"  Trader type: {trader_data.get('trader_type')}")
        print(f"  Score: {trader_data.get('score', 0):.3f}")
        print(f"  Key metrics:")
        metrics = trader_data.get('metrics', {})
        print(f"    - Win rate: {metrics.get('win_rate', 0):.1%}")
        print(f"    - Sharpe ratio: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"    - Max drawdown: {metrics.get('max_drawdown', 0):.1%}")
        print(f"    - Copiers: {metrics.get('copiers_count', 0):,}")
    else:
        print("✗ Trader scoring failed")
    
    # Test 3: Refresh trader rankings
    print("\\n3. Testing trader rankings refresh...")
    result = test_api_endpoint(f"{base_url}/traders/refresh-rankings", 'POST', {'limit': 10})
    if result and result.get('success'):
        print("✓ Trader rankings refresh successful")
        print(f"  Total traders analyzed: {result.get('total_traders', 0)}")
        print(f"  Day traders: {result.get('day_traders', 0)}")
        print(f"  Long-term traders: {result.get('long_term_traders', 0)}")
        
        # Show top traders
        if result.get('top_day_traders'):
            print("  Top day traders:")
            for trader in result['top_day_traders']:
                print(f"    - {trader['username']}: {trader['score']:.3f}")
        
        if result.get('top_long_term_traders'):
            print("  Top long-term traders:")
            for trader in result['top_long_term_traders']:
                print(f"    - {trader['username']}: {trader['score']:.3f}")
    else:
        print("✗ Trader rankings refresh failed")
    
    # Test 4: Get traders list
    print("\\n4. Testing traders list retrieval...")
    result = test_api_endpoint(f"{base_url}/traders?limit=5")
    if result and result.get('success'):
        traders = result.get('data', [])
        print(f"✓ Retrieved {len(traders)} traders")
        for trader in traders[:3]:  # Show first 3
            print(f"  - {trader['username']} ({trader['trader_type']}): score {trader.get('total_score', 0):.3f}")
    else:
        print("✗ Traders list retrieval failed")
    
    # Test 5: Generate trading signals
    print("\\n5. Testing signal generation...")
    result = test_api_endpoint(f"{base_url}/signals/generate", 'POST', {'strategy_type': 'all'})
    if result and result.get('success'):
        print("✓ Signal generation successful")
        print(f"  Total signals: {result.get('total_signals', 0)}")
        
        signals = result.get('signals', {})
        if 'day_trading' in signals:
            print(f"  Day trading signals: {len(signals['day_trading'])}")
        if 'long_term' in signals:
            print(f"  Long-term signals: {len(signals['long_term'])}")
    else:
        print("✗ Signal generation failed")
    
    # Test 6: Get generated signals
    print("\\n6. Testing signals retrieval...")
    result = test_api_endpoint(f"{base_url}/signals?limit=10")
    if result and result.get('success'):
        signals = result.get('data', [])
        print(f"✓ Retrieved {len(signals)} signals")
        
        # Show top signals
        for signal in signals[:3]:  # Show first 3
            print(f"  - {signal['instrument']} {signal['action'].upper()}")
            print(f"    Strategy: {signal['strategy_type']}, Confidence: {signal['confidence']:.1%}")
            print(f"    Reasoning: {signal['reasoning'][:100]}...")
    else:
        print("✗ Signals retrieval failed")
    
    # Test 7: Analytics summary
    print("\\n7. Testing analytics summary...")
    result = test_api_endpoint(f"{base_url}/analytics/summary")
    if result and result.get('success'):
        data = result['data']
        print("✓ Analytics summary successful")
        print(f"  Total traders: {data['traders']['total']}")
        print(f"  Total signals: {data['signals']['total']}")
        print(f"  Top signal: {data['top_signals'][0]['instrument']} {data['top_signals'][0]['action'].upper()}" if data['top_signals'] else "No signals")
    else:
        print("✗ Analytics summary failed")
    
    print("\\n=== Test Complete ===")
    print("\\nSystem is ready for frontend development!")

if __name__ == "__main__":
    # Wait a moment for Flask to fully start
    print("Waiting for Flask server to start...")
    time.sleep(3)
    main()

