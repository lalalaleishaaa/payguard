from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from database import Database
import json

app = FastAPI(title="PayGuard", description="AI Revenue Recovery Agent")
db = Database()


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    metrics = get_metrics()
    recent_actions = get_recent_actions()
    llm_stats = get_llm_stats()
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PayGuard - AI Revenue Recovery</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #0a0e17;
                color: #e2e8f0;
                min-height: 100vh;
                padding: 20px;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                padding: 20px;
                background: #1a2332;
                border-radius: 12px;
            }}
            .header h1 {{ font-size: 28px; font-weight: 700; color: #fff; }}
            .header .subtitle {{ font-size: 14px; color: #94a3b8; margin-top: 4px; }}
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .metric-card {{
                background: #1a2332;
                border-radius: 12px;
                padding: 24px;
                border: 1px solid #2d3748;
            }}
            .metric-label {{
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: #94a3b8;
                margin-bottom: 8px;
            }}
            .metric-value {{ font-size: 32px; font-weight: 700; color: #fff; }}
            .metric-value.positive {{ color: #10b981; }}
            .metric-value.warning {{ color: #f59e0b; }}
            .content-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
            }}
            .panel {{
                background: #1a2332;
                border-radius: 12px;
                padding: 20px;
                border: 1px solid #2d3748;
            }}
            .panel h3 {{ font-size: 18px; margin-bottom: 16px; color: #fff; }}
            .feed {{ max-height: 400px; overflow-y: auto; }}
            .feed-item {{
                padding: 12px;
                border-bottom: 1px solid #2d3748;
                font-size: 14px;
            }}
            .feed-item .action {{ font-weight: 600; color: #60a5fa; }}
            .feed-item .success {{ color: #10b981; font-weight: 600; }}
            .feed-item .failed {{ color: #ef4444; font-weight: 600; }}
            .feed-item .amount {{ font-weight: 600; }}
            .feed-item .time {{ color: #64748b; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <h1>PayGuard</h1>
                <div class="subtitle">AI-Powered Revenue Recovery Agent</div>
            </div>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Revenue at Risk</div>
                <div class="metric-value warning">INR {metrics['total_at_risk']:,.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Recovered Revenue</div>
                <div class="metric-value positive">INR {metrics['recovered_amount']:,.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Recovery Rate</div>
                <div class="metric-value">{metrics['recovery_rate']}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Transactions Recovered</div>
                <div class="metric-value">{metrics['total_recovered']} / {metrics['total_failed']}</div>
            </div>
        </div>

        <div class="content-grid">
            <div class="panel">
                <h3>Recovery Feed</h3>
                <div class="feed">
                    {get_feed_html(recent_actions)}
                </div>
            </div>
            <div class="panel">
                <h3>LLM vs Fallback</h3>
                <div id="pieChart"></div>
            </div>
        </div>

        <script>
            const llmData = [{{
                values: [{llm_stats['llm_actions']}, {llm_stats['fallback_actions']}],
                labels: ['LLM Actions', 'Fallback Actions'],
                type: 'pie',
                marker: {{ colors: ['#10b981', '#f59e0b'] }}
            }}];
            Plotly.newPlot('pieChart', llmData, {{
                paper_bgcolor: 'rgba(0,0,0,0)',
                font: {{ color: '#fff' }}
            }});
        </script>
    </body>
    </html>
    """
    return html


def get_feed_html(actions):
    html = ""
    for action in actions:
        status_class = "success" if action["success"] else "failed"
        status_text = "SUCCESS" if action["success"] else "FAILED"
        fallback_html = '<br><span class="failed">Fallback triggered</span>' if action["fallback_triggered"] else ""
        
        html += f"""
        <div class="feed-item">
            <span class="action">{action['action_type']}</span>
            <span class="{status_class}">{status_text}</span>
            <br>
            <span class="amount">INR {action['amount']:,.2f}</span>
            <span> - {action['customer_name']}</span>
            <br>
            <span class="time">{action['timestamp']}</span>
            {fallback_html}
        </div>
        """
    return html


@app.get("/api/metrics")
async def metrics():
    return get_metrics()


@app.get("/api/recent-actions")
async def recent_actions(limit: int = 20):
    return get_recent_actions(limit)


@app.get("/api/llm-stats")
async def llm_stats():
    return get_llm_stats()


def get_metrics():
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


def get_recent_actions(limit=20):
    return db.fetch_all("""
        SELECT r.*, t.amount, c.name as customer_name
        FROM recovery_actions r
        JOIN transactions t ON r.transaction_id = t.id
        JOIN customers c ON t.customer_id = c.id
        ORDER BY r.timestamp DESC
        LIMIT ?
    """, (limit,))


def get_llm_stats():
    total = db.fetch_one("SELECT COUNT(*) as c FROM recovery_actions")["c"]
    fallback = db.fetch_one("SELECT COUNT(*) as c FROM recovery_actions WHERE fallback_triggered = 1")["c"]
    llm = total - fallback

    return {
        "total_actions": total,
        "llm_actions": llm,
        "fallback_actions": fallback,
        "fallback_rate": round((fallback / total * 100), 1) if total > 0 else 0
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)