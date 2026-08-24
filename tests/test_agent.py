import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database
from fallback import RuleBasedFallback
from config import Config


@pytest.fixture
def db():
    database = Database()
    yield database


@pytest.fixture
def fallback():
    return RuleBasedFallback()


def test_database_connection(db):
    result = db.fetch_one("SELECT COUNT(*) as c FROM transactions")
    assert result["c"] > 0


def test_failed_transactions_exist(db):
    result = db.fetch_one("SELECT COUNT(*) as c FROM transactions WHERE status = 'failed'")
    assert result["c"] > 0


def test_customers_exist(db):
    result = db.fetch_one("SELECT COUNT(*) as c FROM customers")
    assert result["c"] > 0


def test_recovery_actions_logged(db):
    result = db.fetch_one("SELECT COUNT(*) as c FROM recovery_actions")
    assert result["c"] > 0


def test_audit_log_exists(db):
    result = db.fetch_one("SELECT COUNT(*) as c FROM audit_log")
    assert result["c"] >= 0


def test_fallback_network_issue(fallback):
    transaction = {
        "id": "TEST001",
        "error_code": "upi_timeout",
        "amount": 1000,
        "payment_method": "UPI"
    }
    customer = {
        "id": "CUST001",
        "name": "Test User",
        "segment": "regular",
        "lifetime_value": 50000,
        "preferred_payment": "UPI",
        "device": "mobile"
    }
    result = fallback.classify(transaction, customer)
    assert result["action"] == "retry_now"
    assert result["confidence"] > 0.5


def test_fallback_insufficient_funds(fallback):
    transaction = {
        "id": "TEST002",
        "error_code": "card_declined",
        "amount": 2000,
        "payment_method": "Credit Card"
    }
    customer = {
        "id": "CUST002",
        "name": "Test User 2",
        "segment": "regular",
        "lifetime_value": 30000,
        "preferred_payment": "Credit Card",
        "device": "desktop"
    }
    result = fallback.classify(transaction, customer)
    assert result["action"] == "switch_method"
    assert result["alternative_payment_method"] is not None


def test_fallback_high_value(fallback):
    transaction = {
        "id": "TEST003",
        "error_code": "unknown_error",
        "amount": 10000,
        "payment_method": "Net Banking"
    }
    customer = {
        "id": "CUST003",
        "name": "Test User 3",
        "segment": "high_value",
        "lifetime_value": 200000,
        "preferred_payment": "Net Banking",
        "device": "desktop"
    }
    result = fallback.classify(transaction, customer)
    assert result["action"] == "send_reminder"
    assert result["priority"] == "high"


def test_fallback_authentication(fallback):
    transaction = {
        "id": "TEST004",
        "error_code": "otp_expired",
        "amount": 500,
        "payment_method": "UPI"
    }
    customer = {
        "id": "CUST004",
        "name": "Test User 4",
        "segment": "new_customer",
        "lifetime_value": 1000,
        "preferred_payment": "UPI",
        "device": "mobile"
    }
    result = fallback.classify(transaction, customer)
    assert result["action"] == "retry_now"


def test_fallback_default(fallback):
    transaction = {
        "id": "TEST005",
        "error_code": "unknown_error",
        "amount": 100,
        "payment_method": "Wallet"
    }
    customer = {
        "id": "CUST005",
        "name": "Test User 5",
        "segment": "new_customer",
        "lifetime_value": 500,
        "preferred_payment": "Wallet",
        "device": "mobile"
    }
    result = fallback.classify(transaction, customer)
    assert result["action"] == "do_not_recover"
    assert result["confidence"] < 0.5


def test_config_values():
    assert Config.MAX_RETRY_ATTEMPTS > 0
    assert Config.HIGH_VALUE_THRESHOLD > 0
    assert Config.LLM_MAX_RETRIES > 0