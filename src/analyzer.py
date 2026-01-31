"""
Analysis script for Ethereum RPC measurements
Analyzes block lag, divergence, and latency patterns
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
        
        print(f"\n📊 Total measurements: {total_measurements}")
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
        
        print("\n" + "="*60)
        print("✅ Analysis Complete!")
        print("="*60 + "\n")

def main():
    db_path = "D:/ethereum-rpc-analysis/data/rpc_analysis.db"
    
    analyzer = RPCAnalyzer(db_path)
    analyzer.run_full_analysis()

if __name__ == "__main__":
    main()
