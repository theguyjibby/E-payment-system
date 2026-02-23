from flask import Flask, request, jsonify
import hmac, hashlib
import os
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")

# This is your webhook listener function
def handle_paystack_webhook(payload, signature):
    # Verify signature
    computed_signature = hmac.new(
        PAYSTACK_SECRET_KEY.encode(),
        msg=payload,
        digestmod=hashlib.sha512
    ).hexdigest()
    
    if computed_signature != signature:
        return False,'no reference',  "Invalid signature"
    
    # Parse JSON
    data = request.json.get("data", {})
    event = request.json.get("event")
    
    # Handle bank transfer success
    if event == "charge.success":
        reference = data.get("reference")
        amount = data.get("amount")
        currency = data.get("currency")
        payment_type = data.get("payment_type")
        
        # Lookup donation in DB and mark as success
        
    return True, reference, "Payment processed"

