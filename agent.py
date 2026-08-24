import random
from datetime import datetime
from typing import Dict, List
from database import Database
from llm_client import LLMClient
from fallback import RuleBasedFallback
from config import Config

class PayGuardAgent:
    def __init__(self):
        self.db = Database()
        self.llm_client = LLMClient()
        self.fallback = RuleBasedFallback()
        self.fallback_triggered_count = 0
        self.total_recovered = 0.0
        self.actions_log = []

    def run(self):
        failed_transactions = self.get_failed_transactions()
        abandoned_carts = self.get_abandoned_carts()

        print(f"Processing {len(failed_transactions)} failed transactions")
        print(f"Processing {len(abandoned_carts)} abandoned carts")
        print("-" * 50)

        for transaction in failed_transactions:
            customer = self.get_customer(transaction["customer_id"])

            if transaction["recovery_attempts"] >= Config.MAX_RETRY_ATTEMPTS:
                self.log_audit("max_attempts_reached", transaction["id"],
                              f"Already attempted {transaction['recovery_attempts']} times")
                continue

            print(f"\nAnalyzing transaction {transaction['id']} (INR {transaction['amount']:,.2f})")

            analysis = self.analyze_transaction(transaction, customer)

            if analysis["action"] == "do_not_recover":
                self.log_audit("not_recoverable", transaction["id"], analysis["reasoning"])
                print(f"  -> Not recoverable: {analysis['reasoning']}")
                continue

            recovery_result = self.execute_recovery(transaction, analysis)

            if recovery_result["success"]:
                self.total_recovered += recovery_result["recovered_amount"]
                self.update_transaction_recovered(transaction["id"])
                print(f"  -> RECOVERED: {analysis['action']} (INR {transaction['amount']:,.2f})")
            else:
                print(f"  -> Failed: {analysis['action']}")

            self.log_recovery_action(transaction["id"], analysis, recovery_result)

        self.handle_abandoned_carts(abandoned_carts)
        self.print_summary()

    def analyze_transaction(self, transaction: Dict, customer: Dict) -> Dict:
        try:
            analysis = self.llm_client.analyze_transaction(transaction, customer)
            analysis["fallback_triggered"] = False
            return analysis

        except Exception as e:
            self.fallback_triggered_count += 1
            analysis = self.fallback.classify(transaction, customer)
            analysis["fallback_triggered"] = True
            analysis["llm_error"] = str(e)

            self.log_audit("fallback_triggered", transaction["id"],
                          f"LLM failed: {e}. Using rule-based fallback.")

            print(f"  -> LLM failed, using fallback. Reason: {e}")
            return analysis

    def execute_recovery(self, transaction: Dict, analysis: Dict) -> Dict:
        success_rates = {
            "retry_now": 0.75,
            "retry_later": 0.45,
            "switch_method": 0.60,
            "send_reminder": 0.35,
            "do_not_recover": 0.0
        }

        success_rate = success_rates.get(analysis["action"], 0.30)

        if transaction["amount"] >= Config.HIGH_VALUE_THRESHOLD:
            success_rate += 0.10

        success = random.random() < success_rate

        return {
            "transaction_id": transaction["id"],
            "action_taken": analysis["action"],
            "success": success,
            "recovered_amount": transaction["amount"] if success else 0.0,
            "timestamp": datetime.now().isoformat(),
            "fallback_triggered": analysis.get("fallback_triggered", False)
        }

    def get_failed_transactions(self) -> List[Dict]:
        return self.db.fetch_all("""
            SELECT * FROM transactions
            WHERE status = 'failed'
            AND recovery_status = 'pending'
            AND recovery_attempts < ?
            ORDER BY amount DESC
        """, (Config.MAX_RETRY_ATTEMPTS,))

    def get_abandoned_carts(self) -> List[Dict]:
        return self.db.fetch_all("""
            SELECT * FROM transactions
            WHERE cart_abandoned = 1
            AND recovery_status = 'pending'
        """)

    def get_customer(self, customer_id: str) -> Dict:
        return self.db.fetch_one("""
            SELECT * FROM customers WHERE id = ?
        """, (customer_id,))

    def update_transaction_recovered(self, transaction_id: str):
        self.db.execute_query("""
            UPDATE transactions
            SET recovery_status = 'recovered',
                recovery_attempts = recovery_attempts + 1
            WHERE id = ?
        """, (transaction_id,))

    def log_recovery_action(self, transaction_id: str, analysis: Dict, result: Dict):
        self.db.execute_query("""
            INSERT INTO recovery_actions
            (transaction_id, action_type, confidence, llm_reasoning, fallback_triggered,
             success, recovered_amount, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction_id,
            analysis["action"],
            analysis.get("confidence", 0.0),
            analysis.get("reasoning", ""),
            1 if analysis.get("fallback_triggered", False) else 0,
            1 if result["success"] else 0,
            result["recovered_amount"],
            result["timestamp"]
        ))

    def log_audit(self, event_type: str, transaction_id: str, details: str):
        self.db.execute_query("""
            INSERT INTO audit_log (event_type, transaction_id, details, timestamp)
            VALUES (?, ?, ?, ?)
        """, (event_type, transaction_id, details, datetime.now().isoformat()))

    def handle_abandoned_carts(self, abandoned_carts: List[Dict]):
        for cart in abandoned_carts:
            customer = self.get_customer(cart["customer_id"])

            if customer["segment"] in ["high_value", "enterprise"]:
                action = "send_reminder"
                message = f"Complete your purchase of INR {cart['amount']:,.2f}. Items in cart reserved for 24 hours."
            elif customer["segment"] == "regular":
                action = "send_reminder"
                message = "Your cart is waiting. Complete your order now."
            else:
                action = "do_not_recover"
                message = None

            if action != "do_not_recover":
                self.db.execute_query("""
                    UPDATE transactions
                    SET recovery_status = 'reminder_sent'
                    WHERE id = ?
                """, (cart["id"],))

                self.log_audit("cart_recovery", cart["id"], f"Sent reminder: {message}")

    def print_summary(self):
        stats = self.db.fetch_one("""
            SELECT
                COUNT(DISTINCT t.id) as total_failed,
                SUM(CASE WHEN t.recovery_status = 'recovered' THEN 1 ELSE 0 END) as recovered_count,
                SUM(CASE WHEN t.recovery_status = 'recovered' THEN t.amount ELSE 0 END) as recovered_amount,
                SUM(t.amount) as total_at_risk
            FROM transactions t
            WHERE t.status = 'failed'
        """)

        print("\n" + "=" * 50)
        print("PAYGUARD RECOVERY SUMMARY")
        print("=" * 50)
        print(f"Total failed transactions: {stats['total_failed']}")
        print(f"Recovered: {stats['recovered_count']}")
        print(f"Total at risk: INR {stats['total_at_risk']:,.2f}")
        print(f"Recovered amount: INR {stats['recovered_amount']:,.2f}")

        if stats['total_at_risk'] > 0:
            recovery_rate = (stats['recovered_amount'] / stats['total_at_risk']) * 100
            print(f"Recovery rate: {recovery_rate:.1f}%")

        print(f"Fallback triggered: {self.fallback_triggered_count} times")
        print("=" * 50)


if __name__ == "__main__":
    agent = PayGuardAgent()
    agent.run()