"""
Analysis script for Ethereum RPC measurements
Analyzes block lag, divergence, latency patterns, logs, and receipts
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
import json

class RPCAnalyzer:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        
    def get_block_measurements(self) -> pd.DataFrame:
        """Load all block measurements"""
        query = '''
            SELECT timestamp, provider, block_number, latency_ms, request_time
            FROM block_measurements
            ORDER BY timestamp
        '''
        df = pd.read_sql_query(query, self.conn)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    
    def get_block_headers(self) -> pd.DataFrame:
        """Load all block header measurements"""
        query = '''
            SELECT timestamp, provider, block_number, block_hash, 
                   parent_hash, gas_used, gas_limit, latency_ms
            FROM block_headers
            ORDER BY timestamp, block_number
        '''
        df = pd.read_sql_query(query, self.conn)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    
    def get_log_measurements(self) -> pd.DataFrame:
        """Load all log measurements"""
        query = '''
            SELECT timestamp, provider, from_block, to_block, 
                   log_count, latency_ms, filter_params
            FROM log_measurements
            ORDER BY timestamp
        '''
        try:
            df = pd.read_sql_query(query, self.conn)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        except:
            return pd.DataFrame()
    
    def get_receipt_measurements(self) -> pd.DataFrame:
        """Load all receipt measurements"""
        query = '''
            SELECT timestamp, provider, tx_hash, block_number,
                   status, gas_used, latency_ms
            FROM receipt_measurements
            ORDER BY timestamp
        '''
        try:
            df = pd.read_sql_query(query, self.conn)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        except:
            return pd.DataFrame()
    
    def analyze_head_lag(self) -> dict:
        """Calculate head block lag between providers"""
        df = self.get_block_measurements()
        
        print("\n" + "="*60)
        print("📊 HEAD BLOCK LAG ANALYSIS")
        print("="*60)
        
        # Group by timestamp to compare providers at same time
        results = {}
        
        for timestamp in df['timestamp'].unique():
            snapshot = df[df['timestamp'] == timestamp]
            blocks = snapshot.set_index('provider')['block_number']
            
            if len(blocks) > 1:
                max_block = blocks.max()
                min_block = blocks.min()
                lag = max_block - min_block
                
                if lag > 0:
                    leader = blocks.idxmax()
                    results[timestamp] = {
                        'lag': lag,
                        'leader': leader,
                        'blocks': blocks.to_dict()
                    }
        
        if results:
            print(f"\n⚠️  Detected {len(results)} instances of block divergence:")
            for ts, data in list(results.items())[:5]:  # Show first 5
                print(f"   {ts}: {data['leader']} ahead by {data['lag']} blocks")
                for provider, block in data['blocks'].items():
                    print(f"      {provider}: {block}")
        else:
            print("\n✅ No block divergence detected - all providers in sync!")
        
        return results
    
    def analyze_latency(self) -> dict:
        """Analyze latency patterns per provider"""
        df = self.get_block_measurements()
        
        print("\n" + "="*60)
        print("⏱️  LATENCY ANALYSIS")
        print("="*60)
        
        stats = df.groupby('provider')['latency_ms'].agg([
            'count', 'mean', 'std', 'min', 'max'
        ]).round(2)
        
        print("\nLatency Statistics (milliseconds):")
        print(stats.to_string())
        
        return stats.to_dict()
    
    def analyze_block_headers(self) -> dict:
        """Check if providers agree on block hashes"""
        df = self.get_block_headers()
        
        print("\n" + "="*60)
        print("🔗 BLOCK HASH CONSISTENCY ANALYSIS")
        print("="*60)
        
        if df.empty:
            print("\n⚠️  No block header data collected yet")
            return {}
        
        # Group by block number to compare hashes
        divergences = []
        
        for block_num in df['block_number'].unique():
            block_data = df[df['block_number'] == block_num]
            hashes = block_data.groupby('provider')['block_hash'].first()
            
            if len(hashes.unique()) > 1:
                divergences.append({
                    'block': block_num,
                    'hashes': hashes.to_dict()
                })
        
        if divergences:
            print(f"\n⚠️  Found {len(divergences)} blocks with hash disagreements:")
            for div in divergences[:3]:
                print(f"   Block {div['block']}:")
                for provider, hash_val in div['hashes'].items():
                    print(f"      {provider}: {hash_val[:16]}...")
        else:
            print(f"\n✅ All {len(df['block_number'].unique())} blocks have matching hashes across providers!")
        
        return {'divergences': len(divergences), 'total_blocks': len(df['block_number'].unique())}
    
    def analyze_logs(self) -> dict:
        """Analyze log retrieval consistency"""
        df = self.get_log_measurements()
        
        print("\n" + "="*60)
        print("📋 LOG RETRIEVAL ANALYSIS")
        print("="*60)
        
        if df.empty:
            print("\n⚠️  No log data collected yet")
            return {}
        
        # Group by timestamp to compare providers
        log_divergences = []
        
        for ts in df['timestamp'].unique():
            snapshot = df[df['timestamp'] == ts]
            log_counts = snapshot.set_index('provider')['log_count']
            
            if len(log_counts.unique()) > 1:
                log_divergences.append({
                    'timestamp': ts,
                    'counts': log_counts.to_dict()
                })
        
        # Calculate statistics
        stats = df.groupby('provider')['log_count'].agg(['mean', 'min', 'max', 'std']).round(2)
        latency_stats = df.groupby('provider')['latency_ms'].agg(['mean', 'min', 'max']).round(2)
        
        print(f"\n📊 Total log queries: {len(df)}")
        print(f"\nLog Count Statistics:")
        print(stats.to_string())
        print(f"\nLog Query Latency (ms):")
        print(latency_stats.to_string())
        
        if log_divergences:
            print(f"\n⚠️  Found {len(log_divergences)} instances where providers returned different log counts:")
            for div in log_divergences[:3]:
                print(f"   {div['timestamp']}:")
                for provider, count in div['counts'].items():
                    print(f"      {provider}: {count} logs")
        else:
            print(f"\n✅ All providers returned consistent log counts!")
        
        return {
            'total_queries': len(df),
            'divergences': len(log_divergences),
            'stats': stats.to_dict()
        }
    
    def analyze_receipts(self) -> dict:
        """Analyze transaction receipt consistency"""
        df = self.get_receipt_measurements()
        
        print("\n" + "="*60)
        print("🧾 RECEIPT RETRIEVAL ANALYSIS")
        print("="*60)
        
        if df.empty:
            print("\n⚠️  No receipt data collected yet")
            return {}
        
        # Group by tx_hash to compare providers
        receipt_divergences = []
        
        for tx_hash in df['tx_hash'].unique():
            tx_data = df[df['tx_hash'] == tx_hash]
            gas_used = tx_data.groupby('provider')['gas_used'].first()
            status = tx_data.groupby('provider')['status'].first()
            
            # Check if gas_used or status differs
            if len(gas_used.unique()) > 1 or len(status.unique()) > 1:
                receipt_divergences.append({
                    'tx_hash': tx_hash,
                    'gas_used': gas_used.to_dict(),
                    'status': status.to_dict()
                })
        
        # Calculate statistics
        latency_stats = df.groupby('provider')['latency_ms'].agg(['mean', 'min', 'max', 'count']).round(2)
        
        print(f"\n📊 Total receipt queries: {len(df)}")
        print(f"   Unique transactions: {df['tx_hash'].nunique()}")
        print(f"\nReceipt Query Latency (ms):")
        print(latency_stats.to_string())
        
        if receipt_divergences:
            print(f"\n⚠️  Found {len(receipt_divergences)} transactions with inconsistent receipts:")
            for div in receipt_divergences[:3]:
                print(f"   TX: {div['tx_hash'][:16]}...")
                print(f"      Gas used: {div['gas_used']}")
                print(f"      Status: {div['status']}")
        else:
            print(f"\n✅ All providers returned consistent receipt data!")
        
        return {
            'total_queries': len(df),
            'unique_txs': df['tx_hash'].nunique(),
            'divergences': len(receipt_divergences)
        }
    
    def generate_summary(self):
        """Generate overall analysis summary"""
        print("\n" + "="*60)
        print("📋 COLLECTION SUMMARY")
        print("="*60)
        
        # Basic stats
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM block_measurements')
        total_measurements = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT provider) FROM block_measurements')
        num_providers = cursor.fetchone()[0]
        
        cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM block_measurements')
        start, end = cursor.fetchone()
        
        cursor.execute('SELECT MIN(block_number), MAX(block_number) FROM block_measurements')
        min_block, max_block = cursor.fetchone()
        
        # Log and receipt counts
        cursor.execute('SELECT COUNT(*) FROM log_measurements')
        log_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM receipt_measurements')
        receipt_count = cursor.fetchone()[0]
        
        print(f"\n📊 Total block measurements: {total_measurements}")
        print(f"📋 Total log queries: {log_count}")
        print(f"🧾 Total receipt queries: {receipt_count}")
        print(f"🔌 Providers monitored: {num_providers}")
        print(f"⏱️  Time range: {start} to {end}")
        print(f"📦 Block range: {min_block:,} to {max_block:,} ({max_block - min_block} blocks)")
        
    def run_full_analysis(self):
        """Run complete analysis"""
        print("\n🔬 ETHEREUM RPC INFRASTRUCTURE ANALYSIS")
        print("📅 " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        self.generate_summary()
        self.analyze_latency()
        self.analyze_head_lag()
        self.analyze_block_headers()
        self.analyze_logs()
        self.analyze_receipts()
        
        print("\n" + "="*60)
        print("✅ Analysis Complete!")
        print("="*60 + "\n")

def main():
    db_path = "D:/ethereum-rpc-analysis/data/rpc_analysis.db"
    
    analyzer = RPCAnalyzer(db_path)
    analyzer.run_full_analysis()

if __name__ == "__main__":
    main()