"""
Database setup for Ethereum RPC Analysis Project
Creates SQLite database with tables for storing measurements
"""

import sqlite3
from pathlib import Path
import json
from datetime import datetime

def create_database():
    """Create SQLite database and all required tables"""
    
    db_path = Path("D:/ethereum-rpc-analysis/data/rpc_analysis.db")
    
    print("🗄️  Creating SQLite database...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Table 1: Block number measurements
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS block_measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            provider TEXT NOT NULL,
            block_number INTEGER NOT NULL,
            latency_ms REAL NOT NULL,
            request_time DATETIME NOT NULL
        )
    ''')
    
    # Table 2: Block header comparisons
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS block_headers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            provider TEXT NOT NULL,
            block_number INTEGER NOT NULL,
            block_hash TEXT NOT NULL,
            parent_hash TEXT NOT NULL,
            miner TEXT,
            gas_used INTEGER,
            gas_limit INTEGER,
            latency_ms REAL NOT NULL
        )
    ''')
    
    # Table 3: Log retrieval measurements
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS log_measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            provider TEXT NOT NULL,
            from_block INTEGER NOT NULL,
            to_block INTEGER NOT NULL,
            log_count INTEGER NOT NULL,
            latency_ms REAL NOT NULL,
            filter_params TEXT
        )
    ''')
    
    # Table 4: Receipt comparisons
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS receipt_measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            provider TEXT NOT NULL,
            tx_hash TEXT NOT NULL,
            block_number INTEGER,
            status INTEGER,
            gas_used INTEGER,
            latency_ms REAL NOT NULL
        )
    ''')
    
    # Create indexes for better query performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_block_timestamp ON block_measurements(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_block_provider ON block_measurements(provider)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_header_block ON block_headers(block_number)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_log_timestamp ON log_measurements(timestamp)')
    
    conn.commit()
    
    print("✅ Database created successfully!")
    print(f"📍 Location: {db_path}")
    print("\n📊 Tables created:")
    print("   1. block_measurements - Track latest block numbers over time")
    print("   2. block_headers - Store full block headers for comparison")
    print("   3. log_measurements - Record log retrieval results")
    print("   4. receipt_measurements - Store transaction receipt data")
    print("\n✨ Database ready for data collection!")
    
    conn.close()
    return True

if __name__ == "__main__":
    create_database()
