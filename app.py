from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from database import Database
import uvicorn
import os

app = FastAPI(title="PayGuard", description="AI Revenue Recovery Agent")
db = Database()


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    with open("payguard_story.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@app.get("/api/metrics")
async def metrics():
    total_failed = db.fetch_one("SELECT COUNT(*) as c FROM transactions WHERE status = 'failed'")["c"]
    total_recovered = db.fetch_one("SELECT COUNT(*) as c FROM transactions WHERE recovery_status = 'recovered'")["c"]
    total_at_risk = db.fetch_one("SELECT COALESCE(SUM(amount), 0) as s FROM transactions WHERE status = 'failed'")["s"]
    recovered_amount = db.fetch_one("SELECT COALESCE(SUM(amount), 0) as s FROM transactions WHERE recovery_status = 'recovered'")["s"]
    recovery_rate = (total_recovered / total_failed * 100) if total_failed > 0 else 0

    return {
        "total_failed": total_failed,
        "total_recovered": total_recovered,
        "total_at_risk": total_at_risk,
        "recovered_amount": recovered_amount,
        "recovery_rate": round(recovery_rate, 1)
    }


@app.get("/api/recent-actions")
async def recent_actions(limit: int = 20):
    return db.fetch_all("""
        SELECT r.*, t.amount, c.name as customer_name
        FROM recovery_actions r
        JOIN transactions t ON r.transaction_id = t.id
        JOIN customers c ON t.customer_id = c.id
        ORDER BY r.timestamp DESC
        LIMIT ?
    """, (limit,))


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)