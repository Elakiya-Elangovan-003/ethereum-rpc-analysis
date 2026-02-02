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
    
    def collect_logs(self, from_block: int, to_block: int) -> Dict:
        """Collect logs from all providers for comparison"""
        results = {}
        timestamp = datetime.now()
        
        # Filter for Transfer events (most common, ERC20 standard)
        # This is the keccak256 hash of "Transfer(address,address,uint256)"
        filter_params = {
            'fromBlock': from_block,
            'toBlock': to_block,
            'topics': ['0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef']
        }
        
        for provider_id, provider in self.providers.items():
            try:
                start_time = time.time()
                logs = provider['web3'].eth.get_logs(filter_params)
                latency_ms = (time.time() - start_time) * 1000
                
                # Store in database
                self.cursor.execute('''
                    INSERT INTO log_measurements 
                    (timestamp, provider, from_block, to_block, log_count, latency_ms, filter_params)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    timestamp, provider_id, from_block, to_block,
                    len(logs), latency_ms, str(filter_params)
                ))
                
                results[provider_id] = {
                    'log_count': len(logs),
                    'latency_ms': round(latency_ms, 2)
                }
                
            except Exception as e:
                results[provider_id] = {'error': str(e)}
                print(f"      ❌ {self.providers[provider_id]['name']}: {str(e)}")

        self.conn.commit()
        return results
    
    def collect_receipts(self, block_number: int) -> Dict:
        """Collect transaction receipts from all providers for comparison"""
        results = {}
        timestamp = datetime.now()
        
        # First, get transactions from the block
        try:
            # Use first provider to get block transactions
            first_provider = list(self.providers.values())[0]
            block = first_provider['web3'].eth.get_block(block_number, full_transactions=True)
            
            if len(block['transactions']) == 0:
                return {'info': 'No transactions in block'}
            
            # Sample up to 3 transactions (to avoid too many requests)
            sample_txs = block['transactions'][:min(3, len(block['transactions']))]
            
            for tx in sample_txs:
                tx_hash = tx['hash'].hex()
                
                for provider_id, provider in self.providers.items():
                    try:
                        start_time = time.time()
                        receipt = provider['web3'].eth.get_transaction_receipt(tx_hash)
                        latency_ms = (time.time() - start_time) * 1000
                        
                        # Store in database
                        self.cursor.execute('''
                            INSERT INTO receipt_measurements 
                            (timestamp, provider, tx_hash, block_number, status, gas_used, latency_ms)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            timestamp, provider_id, tx_hash, receipt['blockNumber'],
                            receipt['status'], receipt['gasUsed'], latency_ms
                        ))
                        
                        if provider_id not in results:
                            results[provider_id] = []
                        
                        results[provider_id].append({
                            'tx': tx_hash[:10] + '...',
                            'status': receipt['status'],
                            'gas_used': receipt['gasUsed'],
                            'latency_ms': round(latency_ms, 2)
                        })
                        
                    except Exception as e:
                        if provider_id not in results:
                            results[provider_id] = []
                        results[provider_id].append({'error': str(e)})
            
        except Exception as e:
            results = {'error': f'Failed to get block transactions: {e}'}
        
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
                
                # NEW: Collect logs every 5 iterations (to avoid too many requests)
                if iteration % 5 == 0 and block_numbers:
                    latest_block = max(block_numbers)
                    from_block = latest_block - 10
                    to_block = latest_block
                    
                    print(f"   📋 Collecting logs from blocks {from_block} to {to_block}...")
                    log_results = self.collect_logs(from_block, to_block)
                    
                    for provider_id, result in log_results.items():
                        if 'error' not in result:
                            print(f"      {self.providers[provider_id]['name']:15} Logs: {result['log_count']}  Latency: {result['latency_ms']}ms")
                        else:
                            print(f"      {self.providers[provider_id]['name']:15} ❌ Error: {result['error']}")
                
                # NEW: Collect receipts every 10 iterations
                if iteration % 10 == 0 and block_numbers:
                    latest_block = max(block_numbers)
                    
                    print(f"   🧾 Collecting receipts from block {latest_block}...")
                    receipt_results = self.collect_receipts(latest_block)
                    
                    if 'error' not in receipt_results and 'info' not in receipt_results:
                        for provider_id, receipts in receipt_results.items():
                            if receipts:
                                print(f"      {self.providers[provider_id]['name']:15} Receipts: {len(receipts)}")
                
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