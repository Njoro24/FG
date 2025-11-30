#!/usr/bin/env python
"""
Test script for M-Pesa integration
Run: python test_mpesa.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.payments.mpesa import MpesaAPI

def test_access_token():
    """Test getting M-Pesa access token"""
    print("\n" + "="*50)
    print("Testing M-Pesa Access Token")
    print("="*50)
    
    mpesa = MpesaAPI()
    
    print(f"Environment: {mpesa.environment}")
    print(f"Base URL: {mpesa.base_url}")
    print(f"Consumer Key: {mpesa.consumer_key[:10]}..." if mpesa.consumer_key else "Consumer Key: NOT SET")
    print(f"Shortcode: {mpesa.shortcode}")
    
    try:
        token = mpesa.get_access_token()
        print(f"\n✅ Access Token obtained: {token[:20]}...")
        return True
    except Exception as e:
        print(f"\n❌ Failed to get access token: {e}")
        return False

def test_stk_push_simulation():
    """Test STK Push (simulation only - won't actually charge)"""
    print("\n" + "="*50)
    print("Testing STK Push (Sandbox)")
    print("="*50)
    
    mpesa = MpesaAPI()
    
    # Test phone number (Safaricom sandbox test number)
    test_phone = "254708374149"  # Sandbox test number
    test_amount = 1  # Minimum amount
    
    print(f"Phone: {test_phone}")
    print(f"Amount: KES {test_amount}")
    print(f"Callback URL: {mpesa.callback_url}")
    
    result = mpesa.stk_push(
        phone_number=test_phone,
        amount=test_amount,
        account_reference="TEST001",
        transaction_desc="Test Payment"
    )
    
    if result.get('success'):
        print(f"\n✅ STK Push initiated successfully!")
        print(f"   Checkout Request ID: {result.get('checkout_request_id')}")
        print(f"   Merchant Request ID: {result.get('merchant_request_id')}")
        print(f"   Customer Message: {result.get('customer_message')}")
        return True
    else:
        print(f"\n❌ STK Push failed: {result.get('error')}")
        return False

def test_phone_formatting():
    """Test phone number formatting"""
    print("\n" + "="*50)
    print("Testing Phone Number Formatting")
    print("="*50)
    
    test_numbers = [
        "0712345678",
        "+254712345678",
        "254712345678",
        "712345678",
        "07 123 456 78",
    ]
    
    for num in test_numbers:
        formatted = MpesaAPI.format_phone_number(num)
        print(f"  {num:20} → {formatted}")
    
    return True

if __name__ == "__main__":
    print("\n" + "="*60)
    print("   M-PESA INTEGRATION TEST")
    print("="*60)
    
    # Run tests
    tests = [
        ("Phone Formatting", test_phone_formatting),
        ("Access Token", test_access_token),
        ("STK Push", test_stk_push_simulation),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} test crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
    
    print("\n" + "="*50)
    print("NOTE: For STK Push to work in production:")
    print("1. Register your callback URL with Safaricom")
    print("2. Use production credentials")
    print("3. Ensure callback URL is publicly accessible")
    print("="*50 + "\n")
