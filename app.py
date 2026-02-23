from flask import Flask, jsonify, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import datetime
import os
from dotenv import load_dotenv
import uuid
from paystack_initialization import initialize_paystack_transaction
from webhook_listener import handle_paystack_webhook

import requests

load_dotenv()
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY')

app = Flask(__name__, template_folder='templates', static_folder='static')


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///donations.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'
db = SQLAlchemy(app)

class Donations(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    reference = db.Column(db.String(100), nullable=False)
    remark = db.Column(db.String(200), nullable=True)
    donor_email = db.Column(db.String(100), nullable=True)
    payment_method = db.Column(db.String(50), nullable=False)
    status= db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

@app.route('/')
def index():
    return redirect(url_for('donate'))



@app.route('/donate')
def donate():
    return render_template('donate.html')

@app.route('/payment/callback')
def payment_callback():
    # Basic callback handler, Paystack will redirect here
    reference = request.args.get('reference')
    return redirect(url_for('payment_success', reference=reference))

@app.route('/payment/success')
def payment_success():
    reference = request.args.get('reference')
    return render_template('success.html', reference=reference)





@app.route('/donate/bank_transfer', methods=['GET', 'POST'])
def donate_bank_transfer():
    if request.method == 'POST':
        data = request.get_json()
        amount = data.get('amount')
        remark = data.get('remark')

        if not amount or amount <= 0:
            return jsonify({'error': 'Invalid amount'}), 400
        
        amount = amount * 100
        
        payment_method = 'bank_transfer'
        currency = 'NGN' 

        # Generate unique reference
        reference = str(uuid.uuid4())
        placeholder_email = f"donation-{reference}@yourdomain.com"
        
        new_donation = Donations(amount=amount, reference=reference, remark=remark, donor_email=placeholder_email, payment_method=payment_method, status='pending', currency=currency)

        db.session.add(new_donation)
        db.session.commit()

        headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
        }
        payload = {
        "email": placeholder_email,
        "amount": amount,
        "currency": currency,
        "reference": reference,
        "channels": ["bank"]
        }
        try:
            paystack_data = initialize_paystack_transaction(payload, headers)
            account_number = paystack_data.get("account_number")
            bank_name = paystack_data.get("bank_name")
            reference = paystack_data.get("reference")
            expiry = paystack_data.get("expiry")
            auth_url = paystack_data.get("authorization_url")

            return jsonify({
                'account_number': account_number, 
                'bank_name': bank_name, 
                'reference': reference, 
                'expiry': expiry,
                'authorization_url': auth_url
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return render_template('bank_transfer.html')
    
    

@app.route('/webhook/handler', methods=['POST'])
def webhook_handler():
    signature = request.headers.get("X-Paystack-Signature")
    payload = request.get_data()

    
    success, reference, message = handle_paystack_webhook(payload, signature)

    if not success:
    
        return jsonify({"error": message}), 400

    
    donation = Donations.query.filter_by(reference=reference).first()

    if not donation:
        
        return jsonify({"error": "Donation not found for the given reference"}), 404

    
    if donation.status == "success":
        
        return jsonify({"message": "donation already marked as success"}), 200

    
    donation.status = "success"
    db.session.commit()

    return jsonify({"message": message}), 200
    
    
    

    

@app.route('/donate/card', methods=['GET', 'POST'])
def donate_card_handler():
    if request.method == 'GET':
        return render_template('card.html')
    
    data = request.get_json()
    amount = data.get('amount')
    if not amount or amount <= 0:
        return jsonify({'error': 'Invalid amount'}), 400

    currency = data.get('currency', 'NGN')
    if currency not in ['NGN', 'USD', 'EUR']:
        return jsonify({'error': 'Unsupported currency'}), 400

    remark = data.get('remark')
    donor_email = data.get('donor_email') or "donor_placeholder@example.com"

    # Convert amount to kobo/cent
    amount = int(amount * 100)

    # Generate unique reference
    reference = str(uuid.uuid4()) 
    placeholder_email = f"donation-{reference}@yourdomain.com"


    # Store donation as pending
    new_donation = Donations(
        amount=amount,
        reference=reference,
        remark=remark,
        donor_email=placeholder_email,
        payment_method='card',
        status='pending',
        currency=currency
    )
    db.session.add(new_donation)
    db.session.commit()

    # Initialize Paystack transaction
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "email":placeholder_email,
        "amount": amount,
        "reference": reference,
        "currency": currency,
        "callback_url": url_for('payment_callback', _external=True)
    }
    response = requests.post("https://api.paystack.co/transaction/initialize", json=payload, headers=headers)
    paystack_resp = response.json()

    if not paystack_resp.get('status'):
        return jsonify({'error': 'Failed to initialize transaction with Paystack'}), 500

    # Return authorization URL to frontend
    return jsonify({
        'authorization_url': paystack_resp['data']['authorization_url'],
        'reference': paystack_resp['data']['reference']
    }), 200
        


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)












