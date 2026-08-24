import sqlite3
from config import Config

class Database:
    def __init__(self, db_path=None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.init_schema()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'INR',
                status TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                error_code TEXT,
                failure_pattern TEXT,
                timestamp TEXT NOT NULL,
                cart_abandoned INTEGER DEFAULT 0,
                recovery_status TEXT DEFAULT 'pending',
                recovery_attempts INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS customers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                segment TEXT NOT NULL,
                lifetime_value REAL NOT NULL,
                preferred_payment TEXT,
                device TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS recovery_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                confidence REAL,
                llm_reasoning TEXT,
                fallback_triggered INTEGER DEFAULT 0,
                success INTEGER,
                recovered_amount REAL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (transaction_id) REFERENCES transactions(id)
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                transaction_id TEXT,
                details TEXT,
                timestamp TEXT NOT NULL
            );

            CREATE INDEX idx_transactions_status ON transactions(status);
            CREATE INDEX idx_transactions_timestamp ON transactions(timestamp);
            CREATE INDEX idx_recovery_transaction ON recovery_actions(transaction_id);
        """)
        
        conn.commit()
        conn.close()

    def execute_query(self, query, params=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        conn.close()

    def fetch_one(self, query, params=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        result = cursor.fetchone()
        conn.close()
        return result

    def fetch_all(self, query, params=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        return results