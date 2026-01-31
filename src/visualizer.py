"""
Create visualizations for RPC analysis
"""

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime

class RPCVisualizer:
    def __init__(self, db_path: str, output_dir: str):
        self.db_path = Path(db_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        
        # Set style
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (12, 6)
        
    def plot_latency_over_time(self):
        """Plot latency trends over time"""
        query = '''
            SELECT timestamp, provider, latency_ms
            FROM block_measurements
            ORDER BY timestamp
        '''
        df = pd.read_sql_query(query, self.conn)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        plt.figure(figsize=(14, 6))
        
        for provider in df['provider'].unique():
            provider_data = df[df['provider'] == provider]
            plt.plot(provider_data['timestamp'], provider_data['latency_ms'], 
                    label=provider, alpha=0.7, linewidth=1)
        
        plt.xlabel('Time')
        plt.ylabel('Latency (ms)')
        plt.title('RPC Provider Latency Over Time')
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        output_path = self.output_dir / 'latency_over_time.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✅ Saved: {output_path}")
        
    def plot_latency_distribution(self):
        """Plot latency distribution comparison"""
        query = '''
            SELECT provider, latency_ms
            FROM block_measurements
            WHERE latency_ms < 2000
        '''
        df = pd.read_sql_query(query, self.conn)
        
        plt.figure(figsize=(12, 6))
        
        for provider in df['provider'].unique():
            provider_data = df[df['provider'] == provider]['latency_ms']
            plt.hist(provider_data, bins=50, alpha=0.6, label=provider, edgecolor='black')
        
        plt.xlabel('Latency (ms)')
        plt.ylabel('Frequency')
        plt.title('RPC Provider Latency Distribution (< 2000ms)')
        plt.legend()
        plt.tight_layout()
        
        output_path = self.output_dir / 'latency_distribution.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✅ Saved: {output_path}")
        
    def plot_block_progression(self):
        """Plot block number progression"""
        query = '''
            SELECT timestamp, provider, block_number
            FROM block_measurements
            ORDER BY timestamp
        '''
        df = pd.read_sql_query(query, self.conn)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        plt.figure(figsize=(14, 6))
        
        for provider in df['provider'].unique():
            provider_data = df[df['provider'] == provider]
            plt.plot(provider_data['timestamp'], provider_data['block_number'], 
                    label=provider, alpha=0.8, linewidth=1.5)
        
        plt.xlabel('Time')
        plt.ylabel('Block Number')
        plt.title('Block Number Progression Across Providers')
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        output_path = self.output_dir / 'block_progression.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✅ Saved: {output_path}")
        
    def plot_divergence_timeline(self):
        """Plot when block divergences occurred"""
        query = '''
            SELECT timestamp, provider, block_number
            FROM block_measurements
            ORDER BY timestamp
        '''
        df = pd.read_sql_query(query, self.conn)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Calculate divergences
        divergences = []
        for ts in df['timestamp'].unique():
            snapshot = df[df['timestamp'] == ts]
            blocks = snapshot.set_index('provider')['block_number']
            if len(blocks) > 1:
                diff = blocks.max() - blocks.min()
                if diff > 0:
                    divergences.append({'timestamp': ts, 'divergence': diff})
        
        if divergences:
            div_df = pd.DataFrame(divergences)
            
            plt.figure(figsize=(14, 6))
            plt.scatter(div_df['timestamp'], div_df['divergence'], 
                       alpha=0.6, s=50, color='red')
            plt.axhline(y=0, color='green', linestyle='--', label='In Sync')
            plt.xlabel('Time')
            plt.ylabel('Block Difference')
            plt.title('Block Divergence Events Over Time')
            plt.legend()
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            output_path = self.output_dir / 'divergence_timeline.png'
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"✅ Saved: {output_path}")
        
    def plot_latency_boxplot(self):
        """Box plot comparing provider latencies"""
        query = '''
            SELECT provider, latency_ms
            FROM block_measurements
            WHERE latency_ms < 2000
        '''
        df = pd.read_sql_query(query, self.conn)
        
        plt.figure(figsize=(10, 6))
        df.boxplot(column='latency_ms', by='provider', grid=True)
        plt.xlabel('Provider')
        plt.ylabel('Latency (ms)')
        plt.title('Latency Comparison by Provider')
        plt.suptitle('')
        plt.tight_layout()
        
        output_path = self.output_dir / 'latency_boxplot.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✅ Saved: {output_path}")
    
    def create_all_visualizations(self):
        """Generate all visualizations"""
        print("\n📊 Creating Visualizations...")
        print("="*60)
        
        self.plot_latency_over_time()
        self.plot_latency_distribution()
        self.plot_block_progression()
        self.plot_divergence_timeline()
        self.plot_latency_boxplot()
        
        print("\n✅ All visualizations created!")
        print(f"📁 Saved to: {self.output_dir}")

def main():
    db_path = "D:/ethereum-rpc-analysis/data/rpc_analysis.db"
    output_dir = "D:/ethereum-rpc-analysis/results"
    
    visualizer = RPCVisualizer(db_path, output_dir)
    visualizer.create_all_visualizations()

if __name__ == "__main__":
    main()
