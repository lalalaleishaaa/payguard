from database import Database

db = Database()

llm_actions = db.fetch_one("SELECT COUNT(*) as c FROM recovery_actions WHERE fallback_triggered = 0")
fallback_actions = db.fetch_one("SELECT COUNT(*) as c FROM recovery_actions WHERE fallback_triggered = 1")
total_actions = db.fetch_one("SELECT COUNT(*) as c FROM recovery_actions")
audit_entries = db.fetch_one("SELECT COUNT(*) as c FROM audit_log")
recovered = db.fetch_one("SELECT COUNT(*) as c FROM transactions WHERE recovery_status = 'recovered'")

print(f"LLM actions: {llm_actions['c']}")
print(f"Fallback actions: {fallback_actions['c']}")
print(f"Total actions: {total_actions['c']}")
print(f"Audit entries: {audit_entries['c']}")
print(f"Recovered transactions: {recovered['c']}")