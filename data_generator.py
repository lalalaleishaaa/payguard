import random
from datetime import datetime, timedelta
from database import Database

random.seed(42)

INDIAN_NAMES = [
    "Aarav Patel", "Diya Sharma", "Arjun Singh", "Ananya Gupta", "Vihaan Kumar",
    "Ishita Reddy", "Reyansh Nair", "Saanvi Iyer", "Aditya Menon", "Aadhya Rao",
    "Krishna Joshi", "Pari Desai", "Arnav Mehta", "Myra Kapoor", "Shaurya Malhotra",
    "Anika Agarwal", "Dhruv Bhat", "Navya Chopra", "Ishaan Khanna", "Riya Saxena",
    "Kabir Choudhary", "Zara Hussain", "Ayaan Sheikh", "Prisha Pillai",
    "Rudra Banerjee", "Anvi Mukherjee", "Advait Chatterjee", "Meera Krishnan",
    "Vivaan Subramanian", "Kiara Raman"
]

SEGMENTS = ["high_value", "regular", "new_customer", "dormant", "enterprise"]

PAYMENT_METHODS = ["UPI", "Credit Card", "Debit Card", "Net Banking", "Wallet"]

FAILURE_PATTERNS = {
    "upi_network_timeout": {
        "error_codes": ["upi_timeout", "network_error", "bank_server_unreachable"],
        "recovery_success_rate": 0.85,
        "optimal_action": "retry_now"
    },
    "card_insufficient_funds": {
        "error_codes": ["card_declined", "insufficient_funds"],
        "recovery_success_rate": 0.15,
        "optimal_action": "switch_method"
    },
    "otp_expired": {
        "error_codes": ["3ds_failed", "otp_expired", "authentication_failed"],
        "recovery_success_rate": 0.70,
        "optimal_action": "retry_now"
    },
    "risk_engine_block": {
        "error_codes": ["velocity_check_failed", "risk_score_high"],
        "recovery_success_rate": 0.30,
        "optimal_action": "send_reminder"
    },
    "wallet_insufficient_balance": {
        "error_codes": ["wallet_balance_low", "wallet_limit_exceeded"],
        "recovery_success_rate": 0.65,
        "optimal_action": "switch_method"
    },
    "bank_maintenance": {
        "error_codes": ["bank_down", "maintenance_window"],
        "recovery_success_rate": 0.75,
        "optimal_action": "retry_later"
    }
}

class DataGenerator:
    def __init__(self):
        self.db = Database()
        self.customers = []
        self.transactions = []

    def generate_customers(self, count=50):
        for i in range(count):
            customer_id = f"CUST{str(i+1).zfill(4)}"
            segment = random.choices(
                SEGMENTS,
                weights=[0.15, 0.40, 0.25, 0.10, 0.10]
            )[0]
            
            lifetime_value_map = {
                "high_value": random.uniform(100000, 500000),
                "regular": random.uniform(10000, 100000),
                "new_customer": random.uniform(0, 5000),
                "dormant": random.uniform(5000, 50000),
                "enterprise": random.uniform(500000, 2000000)
            }
            
            customer = {
                "id": customer_id,
                "name": random.choice(INDIAN_NAMES),
                "email": f"customer{i+1}@example.com",
                "phone": f"98{random.randint(10000000, 99999999)}",
                "segment": segment,
                "lifetime_value": round(lifetime_value_map[segment], 2),
                "preferred_payment": random.choice(PAYMENT_METHODS),
                "device": random.choice(["mobile", "desktop", "tablet"]),
                "created_at": (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat()
            }
            self.customers.append(customer)

    def generate_transactions(self, count=150):
        now = datetime.now()
        
        for i in range(count):
            customer = random.choice(self.customers)
            amount = self._generate_amount(customer)
            
            status_roll = random.random()
            if customer["segment"] == "high_value" and amount > 5000:
                status = "failed" if status_roll < 0.35 else "success"
            elif customer["segment"] == "enterprise":
                status = "failed" if status_roll < 0.25 else "success"
            else:
                status = "failed" if status_roll < 0.20 else "success"
            
            failure_pattern = None
            error_code = None
            if status == "failed":
                failure_pattern = random.choice(list(FAILURE_PATTERNS.keys()))
                error_code = random.choice(FAILURE_PATTERNS[failure_pattern]["error_codes"])
            
            transaction = {
                "id": f"TXN{str(i+1).zfill(6)}",
                "customer_id": customer["id"],
                "amount": amount,
                "currency": "INR",
                "status": status,
                "payment_method": customer["preferred_payment"] if random.random() < 0.6 else random.choice(PAYMENT_METHODS),
                "error_code": error_code,
                "failure_pattern": failure_pattern,
                "timestamp": (now - timedelta(minutes=random.randint(5, 2880))).isoformat(),
                "cart_abandoned": 1 if random.random() < 0.15 else 0,
                "recovery_status": "pending" if status == "failed" else "not_needed",
                "recovery_attempts": 0
            }
            self.transactions.append(transaction)

    def _generate_amount(self, customer):
        if customer["segment"] == "enterprise":
            return round(random.uniform(10000, 100000), 2)
        elif customer["segment"] == "high_value":
            return round(random.uniform(5000, 50000), 2)
        elif customer["segment"] == "dormant":
            return round(random.uniform(1000, 10000), 2)
        elif customer["segment"] == "new_customer":
            return round(random.uniform(200, 2000), 2)
        else:
            return round(random.uniform(500, 15000), 2)

    def save_to_database(self):
        for customer in self.customers:
            self.db.execute_query("""
                INSERT OR REPLACE INTO customers 
                (id, name, email, phone, segment, lifetime_value, preferred_payment, device, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                customer["id"], customer["name"], customer["email"], customer["phone"],
                customer["segment"], customer["lifetime_value"], customer["preferred_payment"],
                customer["device"], customer["created_at"]
            ))
        
        for transaction in self.transactions:
            self.db.execute_query("""
                INSERT OR REPLACE INTO transactions
                (id, customer_id, amount, currency, status, payment_method, error_code, 
                 failure_pattern, timestamp, cart_abandoned, recovery_status, recovery_attempts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                transaction["id"], transaction["customer_id"], transaction["amount"],
                transaction["currency"], transaction["status"], transaction["payment_method"],
                transaction["error_code"], transaction["failure_pattern"], transaction["timestamp"],
                transaction["cart_abandoned"], transaction["recovery_status"], transaction["recovery_attempts"]
            ))

    def run(self):
        self.generate_customers(50)
        self.generate_transactions(150)
        self.save_to_database()
        
        failed_count = sum(1 for t in self.transactions if t["status"] == "failed")
        abandoned_count = sum(1 for t in self.transactions if t["cart_abandoned"] == 1)
        
        print(f"Generated {len(self.customers)} customers")
        print(f"Generated {len(self.transactions)} transactions")
        print(f"Failed transactions: {failed_count}")
        print(f"Abandoned carts: {abandoned_count}")
        print(f"Total at-risk revenue: INR {sum(t['amount'] for t in self.transactions if t['status'] == 'failed'):,.2f}")

if __name__ == "__main__":
    generator = DataGenerator()
    generator.run()