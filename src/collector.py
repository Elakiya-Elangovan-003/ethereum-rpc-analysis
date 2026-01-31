"""
Main data collection script for Ethereum RPC Analysis
Polls multiple providers and records block numbers, headers, logs, and receipts
"""

import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from web3 import Web3
from typing import Dict, List, Optional
import sys

class RPCCollector:
    def __init__(self, config_path: str, db_path: str):
        """Initialize the RPC collector"""
        self.config_path = Path(config_path)
        self.db_path = Path(db_path)
        self.providers = {}
        self.load_config()
        self.connect_database()
        
    def load_config(self):
        """Load provider configuration"""
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        self.polling_interval = config['polling_interval_seconds']
        self.duration_hours = config['collection_duration_hours']
        self.block_range = config['block_range_to_check']
        
        # Initialize Web3 connections
        for provider_id, provider_info in config['providers'].items():
            try:
                w3 = Web3(Web3.HTTPProvider(provider_info['url']))
                if w3.is_connected():
                    self.providers[provider_id] = {
                        'name': provider_info['name'],
                        'web3': w3,
                        'url': provider_info['url']
                    }
                    print(f"✅ Connected to {provider_info['name']}")
                else:
                    print(f"⚠️  Failed to connect to {provider_info['name']}")
            except Exception as e:
                print(f"❌ Error connecting to {provider_info['name']}: {e}")
    
    def connect_database(self):
        """Connect to SQLite database"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        print(f"✅ Connected to database: {self.db_path}")
    
    def collect_block_numbers(self) -> Dict:
        """Collect latest block numbers from all providers"""
        results = {}
        timestamp = datetime.now()
        
        for provider_id, provider in self.providers.items():
            try:
                start_time = time.time()
                block_number = provider['web3'].eth.block_number
                latency_ms = (time.time() - start_time) * 1000
                
                # Store in database
                self.cursor.execute('''
                    INSERT INTO block_measurements 
                    (timestamp, provider, block_number, latency_ms, request_time)
                    VALUES (?, ?, ?, ?, ?)
                ''', (timestamp, provider_id, block_number, latency_ms, timestamp))
                
                results[provider_id] = {
                    'block_number': block_number,
                    'latency_ms': round(latency_ms, 2)
                }
                
            except Exception as e:
                print(f"   ❌ Error getting block from {provider['name']}: {e}")
                results[provider_id] = {'error': str(e)}
        
        self.conn.commit()
        return results
    
    def collect_block_headers(self, block_number: int) -> Dict:
        """Collect block headers from all providers for comparison"""
        results = {}
        timestamp = datetime.now()
        
        for provider_id, provider in self.providers.items():
            try:
                start_time = time.time()
                block = provider['web3'].eth.get_block(block_number)
                latency_ms = (time.time() - start_time) * 1000
                
                # Store in database
                self.cursor.execute('''
                    INSERT INTO block_headers 
                    (timestamp, provider, block_number, block_hash, parent_hash, 
                     miner, gas_used, gas_limit, latency_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    timestamp, provider_id, block_number,
                    block['hash'].hex(), block['parentHash'].hex(),
                    block.get('miner', ''), block['gasUsed'], block['gasLimit'],
                    latency_ms
                ))
                
                results[provider_id] = {
                    'hash': block['hash'].hex()[:16] + '...',
                    'latency_ms': round(latency_ms, 2)
                }
                
            except Exception as e:
                results[provider_id] = {'error': str(e)}
        
        self.conn.commit()
        return results
    
    def run_collection(self):
        """Main collection loop"""
        print("\n" + "="*60)
        print("🚀 Starting Data Collection")
        print("="*60)
        print(f"⏱️  Polling interval: {self.polling_interval} seconds")
        print(f"⏳ Duration: {self.duration_hours} hour(s)")
        print(f"📊 Active providers: {len(self.providers)}")
        print("="*60 + "\n")
        
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=self.duration_hours)
        iteration = 0
        
        try:
            while datetime.now() < end_time:
                iteration += 1
                print(f"\n📡 Iteration {iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Collect block numbers
                block_results = self.collect_block_numbers()
                
                # Display results
                print("   Block Numbers:")
                for provider_id, result in block_results.items():
                    if 'error' not in result:
                        print(f"      {self.providers[provider_id]['name']:15} Block: {result['block_number']:,}  Latency: {result['latency_ms']}ms")
                    else:
                        print(f"      {self.providers[provider_id]['name']:15} ❌ {result['error']}")
                
                # Check for block divergence
                block_numbers = [r['block_number'] for r in block_results.values() if 'block_number' in r]
                if len(block_numbers) > 1:
                    max_block = max(block_numbers)
                    min_block = min(block_numbers)
                    if max_block - min_block > 0:
                        print(f"   ⚠️  Block divergence detected: {max_block - min_block} blocks apart")
                
                # Collect headers for recent blocks
                if block_numbers:
                    latest_block = max(block_numbers)
                    # Sample a few recent blocks
                    for offset in [0, 2, 5]:
                        block_to_check = latest_block - offset
                        header_results = self.collect_block_headers(block_to_check)
                
                # Wait for next iteration
                remaining = (end_time - datetime.now()).total_seconds()
                if remaining > 0:
                    wait_time = min(self.polling_interval, remaining)
                    print(f"   ⏳ Waiting {wait_time:.0f}s... (Time remaining: {remaining/60:.1f} minutes)")
                    time.sleep(wait_time)
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Collection stopped by user (Ctrl+C)")
        
        print("\n" + "="*60)
        print("✅ Collection Complete!")
        print("="*60)
        
        # Summary
        self.cursor.execute('SELECT COUNT(*) FROM block_measurements')
        total_measurements = self.cursor.fetchone()[0]
        print(f"📊 Total measurements collected: {total_measurements}")
        print(f"⏱️  Collection duration: {(datetime.now() - start_time).total_seconds()/60:.1f} minutes")
        
        self.conn.close()

def main():
    """Main entry point"""
    config_path = "D:/ethereum-rpc-analysis/config/providers.json"
    db_path = "D:/ethereum-rpc-analysis/data/rpc_analysis.db"
    
    print("🔬 Ethereum RPC Infrastructure Analysis")
    print("📅 " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print()
    
    collector = RPCCollector(config_path, db_path)
    
    if len(collector.providers) == 0:
        print("❌ No providers available. Exiting.")
        sys.exit(1)
    
    collector.run_collection()

if __name__ == "__main__":
    main()
