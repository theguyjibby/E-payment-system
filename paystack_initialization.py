import requests

def initialize_paystack_transaction(payload, headers):
    """
    Initializes a Paystack transaction and returns the data.
    """
    url = "https://api.paystack.co/transaction/initialize"
    response = requests.post(url, json=payload, headers=headers)
    response_data = response.json()

    if not response_data.get('status'):
        raise Exception(response_data.get('message', 'Failed to initialize transaction with Paystack'))

    data = response_data.get('data', {})
    
    # For bank transfers, Paystack might return bank details if requested correctly
    # or the data might be nested. We extract what app.py expects.
    result = {
        "authorization_url": data.get("authorization_url"),
        "reference": data.get("reference"),
        "account_number": data.get("display_text_dict", {}).get("account_number") or data.get("bank", {}).get("account_number"),
        "bank_name": data.get("display_text_dict", {}).get("bank_name") or data.get("bank", {}).get("name"),
        "expiry": data.get("display_text_dict", {}).get("expiry")
    }
    
    # In some cases, for 'bank' option, Paystack returns these directly in 'data' 
    # if it's a specialized integration. Otherwise, the app might be expecting 
    # these fields based on a specific Paystack feature like 'Dedicated Accounts'.
    # For now, we ensure the keys exist.
    
    return result
