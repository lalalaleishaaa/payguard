# PayGuard - AI Revenue Recovery Agent
## Live Demo

🔗 [View Live Demo]https://payguard-gules.vercel.app/

## Overview

PayGuard is an AI-powered revenue recovery agent built for Razorpay that automatically detects failed transactions, diagnoses root causes using LLM intelligence, and executes recovery actions to convert lost revenue into recovered payments.

## Problem Statement

Indian businesses lose INR 15,000+ crores annually to failed payments. Traditional systems simply log the error and require manual intervention. This leads to:
- Revenue leakage from recoverable failures
- Poor customer experience
- High operational costs for support teams
- No systematic recovery process

## Solution

PayGuard automatically:
1. **Detects** failed transactions in real-time
2. **Diagnoses** root cause using Claude LLM
3. **Recovers** revenue through intelligent actions
4. **Logs** every decision for complete auditability

## Results

| Metric | Value |
|--------|-------|
| Failed transactions processed | 23 |
| Successfully recovered | 12 |
| Recovery rate | 55.1% |
| Revenue recovered | INR 226,093.01 |
| Average recovery time | < 5 seconds |
| Fallback triggered | 0 times |

## Architecture

```text
+-------------+     +-------------+     +-------------+
|  Detection  |---->|  Diagnosis  |---->|  Recovery   |
|             |     |             |     |             |
|  Scan DB    |     |  LLM Call   |     |  Execute    |
|  for failed |     |  + Fallback |     |  Action     |
|  txns       |     |  rules      |     |             |
+-------------+     +-------------+     +-------------+
       |                   |                   |
       +-------------------+-------------------+
                           |
                           v
                +-------------------+
                |   Audit Trail     |
                |  Every decision   |
                |  is logged with   |
                |  reasoning        |
                +-------------------+
```

## Recovery Actions

| Action | Description | When Used |
|--------|-------------|-----------|
| `retry_now` | Immediate retry | Network errors, OTP expiry |
| `retry_later` | Delayed retry | Bank maintenance windows |
| `switch_method` | Suggest alternative payment | Card declined, insufficient funds |
| `send_reminder` | Personalized follow-up | High-value customers |
| `do_not_recover` | Skip recovery | Unrecoverable errors |

## Fallback System

When LLM is unavailable, a rule-based classifier handles common patterns:

| Error Code | Action | Confidence |
|-----------|--------|-----------|
| `upi_timeout` | retry_now | 0.85 |
| `card_declined` | switch_method | 0.70 |
| `otp_expired` | retry_now | 0.65 |
| High-value + any error | send_reminder | 0.75 |
| Unknown | do_not_recover | 0.30 |

## Safety Constraints

- Maximum 2 recovery attempts per transaction
- High-value threshold: INR 5,000+ gets extra attention
- Exponential backoff for LLM retries (2s, 4s, 8s)
- Complete audit trail for every action

## Testing

```text
11 passed in 0.15s

test_database_connection PASSED
test_failed_transactions_exist PASSED
test_customers_exist PASSED
test_recovery_actions_logged PASSED
test_audit_log_exists PASSED
test_fallback_network_issue PASSED
test_fallback_insufficient_funds PASSED
test_fallback_high_value PASSED
test_fallback_authentication PASSED
test_fallback_default PASSED
test_config_values PASSED
```

## Tech Stack

- **Backend**: Python, FastAPI
- **AI/LLM**: Claude (via OpenRouter)
- **Database**: SQLite
- **Testing**: pytest (11 tests)
- **Demo**: HTML/CSS/JS scroll-story

## Setup Instructions

### Prerequisites
- Python 3.8+
- OpenRouter API key (or Anthropic API key)

### Installation

```bash
git clone https://github.com/lalalaleishaaa/payguard.git
cd payguard
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt