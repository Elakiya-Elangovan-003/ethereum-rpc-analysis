"""
Test RPC connectivity to all configured providers
"""

import json
from web3 import Web3
from pathlib import Path
import time

def test_providers():
    """Test connection to all RPC providers"""
    
    # Load provider configuration
    config_path = Path("D:/ethereum-rpc-analysis/config/providers.json")
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print("🔌 Testing RPC Provider Connectivity...\n")
    print("=" * 60)
    
    results = {}
    
    for provider_id, provider_info in config['providers'].items():
        print(f"\n📡 Testing {provider_info['name']} ({provider_info['type']})...")
        print(f"   URL: {provider_info['url']}")
        
        try:
            # Create Web3 instance
            w3 = Web3(Web3.HTTPProvider(provider_info['url']))
            
            # Test 1: Check connection
            start_time = time.time()
            is_connected = w3.is_connected()
            connection_time = (time.time() - start_time) * 1000
            
            if not is_connected:
                print(f"   ❌ Connection failed")
                results[provider_id] = {'status': 'failed', 'error': 'Not connected'}
                continue
            
            # Test 2: Get latest block number
            start_time = time.time()
            block_number = w3.eth.block_number
            block_time = (time.time() - start_time) * 1000
            
            # Test 3: Get block details
            start_time = time.time()
            block = w3.eth.get_block('latest')
            block_detail_time = (time.time() - start_time) * 1000
            
            print(f"   ✅ Connected successfully!")
            print(f"   📊 Latest block: {block_number}")
            print(f"   ⏱️  Connection time: {connection_time:.2f}ms")
            print(f"   ⏱️  Block number query: {block_time:.2f}ms")
            print(f"   ⏱️  Block details query: {block_detail_time:.2f}ms")
            print(f"   🔗 Block hash: {block['hash'].hex()[:16]}...")
            
            results[provider_id] = {
                'status': 'success',
                'block_number': block_number,
                'connection_time_ms': round(connection_time, 2),
                'block_query_time_ms': round(block_time, 2),
                'block_detail_time_ms': round(block_detail_time, 2)
            }
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            results[provider_id] = {'status': 'failed', 'error': str(e)}
    
    # Summary
    print("\n" + "=" * 60)
    print("\n📋 SUMMARY:")
    successful = sum(1 for r in results.values() if r['status'] == 'success')
    total = len(results)
    print(f"   ✅ Successful: {successful}/{total}")
    print(f"   ❌ Failed: {total - successful}/{total}")
    
    if successful > 0:
        print("\n🎉 At least one provider is working! We can proceed.")
    else:
        print("\n⚠️  All providers failed. Check your internet connection.")
    
    return results

if __name__ == "__main__":
    test_providers()
