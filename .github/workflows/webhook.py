"""
Razorpay Webhook Integration

Production entry point for PayGuard. When Razorpay sends a webhook
for a failed payment, this handler triggers the recovery agent.

In production flow:
1. Razorpay sends webhook on payment.failed event
2. Handler verifies signature using HMAC-SHA256
3. Extracts transaction details
4. Triggers PayGuard recovery agent
5. Logs everything to audit trail

Usage:
    python webhook.py  (runs on port 8001)
"""

from fastapi import FastAPI, Request, HTTPException
import json
import hmac
import hashlib
from datetime import datetime
from database import Database
from agent import PayGuardAgent

app = FastAPI(title="PayGuard Webhook Handler")
db = Database()

WEBHOOK_SECRET = "your_razorpay_webhook_secret_here"


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Verify webhook authenticity using HMAC-SHA256.
    
    Razorpay signs every webhook with your webhook secret.
    This prevents attackers from sending fake payment failure events.
    
    Args:
        payload: Raw request body bytes
        signature: X-Razorpay-Signature header value
    
    Returns:
        True if signature matches, False otherwise
    """
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)


@app.post("/razorpay-webhook")
async def handle_razorpay_webhook(request: Request):
    """
    Handle Razorpay webhook for payment events.
    
    Triggered when Razorpay sends a webhook notification.
    Only processes failed payments - ignores successful ones.
    
    Returns:
        JSON response acknowledging receipt
    """
    try:
        # Get raw body and signature header
        payload = await request.body()
        signature = request.headers.get("X-Razorpay-Signature", "")
        
        # Verify webhook authenticity
        if not verify_webhook_signature(payload, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse webhook payload
        data = json.loads(payload)
        
        # Extract payment details
        event = data.get("event", "")
        payment_entity = data.get("payload", {}).get("payment", {}).get("entity", {})
        
        payment_id = payment_entity.get("id")
        status = payment_entity.get("status")
        amount = payment_entity.get("amount", 0) / 100  # Paise to rupees
        error_code = payment_entity.get("error_code", "unknown")
        customer_email = payment_entity.get("email", "")
        customer_phone = payment_entity.get("contact", "")
        
        # Only process failed payments
        if status != "failed":
            return {"status": "ignored", "reason": f"Status is {status}"}
        
        # Store failed transaction
        db.execute_query("""
            INSERT OR REPLACE INTO transactions
            (id, customer_id, amount, currency, status, payment_method,
             error_code, failure_pattern, timestamp, cart_abandoned,
             recovery_status, recovery_attempts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payment_id,
            customer_email,
            amount,
            "INR",
            "failed",
            "unknown",
            error_code,
            "razorpay_webhook",
            datetime.now().isoformat(),
            0,
            "pending",
            0
        ))
        
        # Log webhook receipt
        db.execute_query("""
            INSERT INTO audit_log (event_type, transaction_id, details, timestamp)
            VALUES (?, ?, ?, ?)
        """, (
            "webhook_received",
            payment_id,
            f"Razorpay webhook: {event} for {payment_id}",
            datetime.now().isoformat()
        ))
        
        return {
            "status": "recovery_initiated",
            "payment_id": payment_id,
            "amount": amount,
            "error_code": error_code
        }
        
    except Exception as e:
        db.execute_query("""
            INSERT INTO audit_log (event_type, transaction_id, details, timestamp)
            VALUES (?, ?, ?, ?)
        """, (
            "webhook_error",
            "unknown",
            f"Webhook error: {str(e)}",
            datetime.now().isoformat()
        ))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "payguard-webhook",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)