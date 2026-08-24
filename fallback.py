from typing import Dict, Optional

class RuleBasedFallback:
    def __init__(self):
        self.rules = [
            self.rule_network_issues,
            self.rule_insufficient_funds,
            self.rule_high_value,
            self.rule_authentication,
            self.rule_default
        ]

    def classify(self, transaction: Dict, customer: Dict) -> Dict:
        for rule in self.rules:
            result = rule(transaction, customer)
            if result:
                return result

        return self.rule_default(transaction, customer)

    def rule_network_issues(self, transaction: Dict, customer: Dict) -> Optional[Dict]:
        network_errors = ["upi_timeout", "network_error", "bank_server_unreachable", "connection_reset"]

        if transaction.get("error_code") in network_errors:
            return {
                "action": "retry_now",
                "confidence": 0.85,
                "reasoning": "Network errors are typically transient and resolve quickly",
                "alternative_payment_method": None,
                "customer_message": None,
                "priority": "medium"
            }
        return None

    def rule_insufficient_funds(self, transaction: Dict, customer: Dict) -> Optional[Dict]:
        if transaction.get("error_code") in ["card_declined", "insufficient_funds"]:
            alternative = "UPI" if transaction["payment_method"] != "UPI" else "Net Banking"

            return {
                "action": "switch_method",
                "confidence": 0.70,
                "reasoning": "Insufficient funds on current method, likely has alternative",
                "alternative_payment_method": alternative,
                "customer_message": f"Your {transaction['payment_method']} has insufficient balance. Try {alternative} instead.",
                "priority": "medium"
            }
        return None

    def rule_high_value(self, transaction: Dict, customer: Dict) -> Optional[Dict]:
        if transaction["amount"] >= 5000 and customer["segment"] in ["high_value", "enterprise"]:
            return {
                "action": "send_reminder",
                "confidence": 0.75,
                "reasoning": "High-value customer, personalized follow-up likely effective",
                "alternative_payment_method": None,
                "customer_message": f"Dear {customer['name']}, your payment of INR {transaction['amount']:,.2f} is pending. Complete to avoid disruption.",
                "priority": "high"
            }
        return None

    def rule_authentication(self, transaction: Dict, customer: Dict) -> Optional[Dict]:
        if transaction.get("error_code") in ["3ds_failed", "otp_expired", "authentication_failed"]:
            return {
                "action": "retry_now",
                "confidence": 0.65,
                "reasoning": "Authentication failures often succeed on retry",
                "alternative_payment_method": None,
                "customer_message": "Your OTP expired. Please try again.",
                "priority": "medium"
            }
        return None

    def rule_default(self, transaction: Dict, customer: Dict) -> Dict:
        return {
            "action": "do_not_recover",
            "confidence": 0.30,
            "reasoning": "No specific recovery strategy identified",
            "alternative_payment_method": None,
            "customer_message": None,
            "priority": "low"
        }