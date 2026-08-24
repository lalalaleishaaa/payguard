import json
import time
from typing import Dict
from openai import OpenAI
from config import Config


class LLMClient:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=Config.ANTHROPIC_API_KEY
        )
        self.model = "anthropic/claude-sonnet-4"
        self.timeout = Config.LLM_TIMEOUT
        self.max_retries = Config.LLM_MAX_RETRIES

    def call_with_retry(self, prompt: str) -> str:
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=500,
                    temperature=0.2,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content

            except Exception as e:
                last_error = e
                wait_time = 2 ** attempt
                print(f"LLM call failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                time.sleep(wait_time)

        raise Exception(f"LLM call failed after {self.max_retries} attempts: {last_error}")

    def analyze_transaction(self, transaction: Dict, customer: Dict) -> Dict:
        prompt = self.build_prompt(transaction, customer)

        try:
            response_text = self.call_with_retry(prompt)
            return self.parse_response(response_text)
        except Exception as e:
            raise Exception(f"Analysis failed: {e}")

    def build_prompt(self, transaction: Dict, customer: Dict) -> str:
        return f"""You are PayGuard, an AI revenue recovery agent for Razorpay.

TASK: Analyze the failed transaction and recommend the optimal recovery action.

TRANSACTION DETAILS:
- Transaction ID: {transaction['id']}
- Amount: INR {transaction['amount']:,.2f}
- Payment Method: {transaction['payment_method']}
- Error Code: {transaction.get('error_code', 'N/A')}
- Failure Pattern: {transaction.get('failure_pattern', 'unknown')}
- Time of Failure: {transaction['timestamp']}
- Previous Recovery Attempts: {transaction.get('recovery_attempts', 0)}

CUSTOMER CONTEXT:
- Customer ID: {customer['id']}
- Name: {customer['name']}
- Segment: {customer['segment']}
- Lifetime Value: INR {customer['lifetime_value']:,.2f}
- Preferred Payment: {customer['preferred_payment']}
- Device: {customer['device']}

RECOVERY CONSTRAINTS:
1. Maximum {Config.MAX_RETRY_ATTEMPTS} recovery attempts allowed
2. Transactions above INR {Config.HIGH_VALUE_THRESHOLD:,} are high priority
3. Must provide confidence score (0.0 to 1.0)
4. Must justify recommendation with specific reasoning

RESPONSE FORMAT (JSON only):
{{
    "action": "retry_now" | "retry_later" | "switch_method" | "send_reminder" | "do_not_recover",
    "confidence": float,
    "reasoning": "string",
    "alternative_payment_method": "string or null",
    "customer_message": "string or null",
    "priority": "high" | "medium" | "low"
}}
"""

    def parse_response(self, response_text: str) -> Dict:
        try:
            response_text = response_text.strip()

            if response_text.startswith("```"):
                response_text = response_text.split("\n", 1)[1]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]

            return json.loads(response_text)

        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse LLM response: {e}")