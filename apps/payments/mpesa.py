"""
M-Pesa Daraja API Integration
"""
import requests
import base64
from datetime import datetime
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class MpesaAPI:
    def __init__(self):
        self.environment = getattr(settings, 'MPESA_ENVIRONMENT', 'sandbox')
        self.consumer_key = getattr(settings, 'MPESA_CONSUMER_KEY', '')
        self.consumer_secret = getattr(settings, 'MPESA_CONSUMER_SECRET', '')
        self.shortcode = getattr(settings, 'MPESA_SHORTCODE', '')
        self.passkey = getattr(settings, 'MPESA_PASSKEY', '')
        self.callback_url = getattr(settings, 'MPESA_CALLBACK_URL', '')
        
        if self.environment == 'sandbox':
            self.base_url = 'https://sandbox.safaricom.co.ke'
        else:
            self.base_url = 'https://api.safaricom.co.ke'
    
    def get_access_token(self):
        """Get OAuth access token from M-Pesa API"""
        # Check cache first
        cached_token = cache.get('mpesa_access_token')
        if cached_token:
            return cached_token
        
        url = f'{self.base_url}/oauth/v1/generate?grant_type=client_credentials'
        
        try:
            response = requests.get(
                url,
                auth=(self.consumer_key, self.consumer_secret)
            )
            response.raise_for_status()
            
            token = response.json().get('access_token')
            # Cache token for 50 minutes (expires in 1 hour)
            cache.set('mpesa_access_token', token, 3000)
            
            return token
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get M-Pesa access token: {e}")
            raise
    
    def generate_password(self):
        """Generate password for STK Push"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        data_to_encode = f"{self.shortcode}{self.passkey}{timestamp}"
        encoded = base64.b64encode(data_to_encode.encode())
        return encoded.decode('utf-8'), timestamp
    
    def stk_push(self, phone_number, amount, account_reference, transaction_desc):
        """
        Initiate STK Push (Lipa Na M-Pesa Online)
        
        Args:
            phone_number: Customer phone number (format: 254XXXXXXXXX)
            amount: Amount to charge
            account_reference: Reference for the transaction
            transaction_desc: Description of the transaction
        
        Returns:
            dict: Response from M-Pesa API
        """
        access_token = self.get_access_token()
        password, timestamp = self.generate_password()
        
        url = f'{self.base_url}/mpesa/stkpush/v1/processrequest'
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'BusinessShortCode': self.shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(amount),
            'PartyA': phone_number,
            'PartyB': self.shortcode,
            'PhoneNumber': phone_number,
            'CallBackURL': self.callback_url,
            'AccountReference': account_reference,
            'TransactionDesc': transaction_desc
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"STK Push initiated: {result}")
            
            return {
                'success': True,
                'checkout_request_id': result.get('CheckoutRequestID'),
                'merchant_request_id': result.get('MerchantRequestID'),
                'response_code': result.get('ResponseCode'),
                'response_description': result.get('ResponseDescription'),
                'customer_message': result.get('CustomerMessage')
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"STK Push failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def query_stk_status(self, checkout_request_id):
        """Query the status of an STK Push transaction"""
        access_token = self.get_access_token()
        password, timestamp = self.generate_password()
        
        url = f'{self.base_url}/mpesa/stkpushquery/v1/query'
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'BusinessShortCode': self.shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'CheckoutRequestID': checkout_request_id
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"STK status query failed: {e}")
            return None
    
    def b2c_payment(self, phone_number, amount, occasion='', remarks=''):
        """
        B2C Payment (Business to Customer) - for payouts
        
        Args:
            phone_number: Recipient phone number (format: 254XXXXXXXXX)
            amount: Amount to send
            occasion: Occasion for the payment
            remarks: Remarks/notes
        
        Returns:
            dict: Response from M-Pesa API
        """
        access_token = self.get_access_token()
        
        url = f'{self.base_url}/mpesa/b2c/v1/paymentrequest'
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'InitiatorName': 'testapi',  # Replace with actual initiator name
            'SecurityCredential': '',  # Replace with actual security credential
            'CommandID': 'BusinessPayment',
            'Amount': int(amount),
            'PartyA': self.shortcode,
            'PartyB': phone_number,
            'Remarks': remarks or 'Payout',
            'QueueTimeOutURL': f'{self.callback_url}/timeout',
            'ResultURL': f'{self.callback_url}/result',
            'Occasion': occasion or 'Payout'
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"B2C Payment initiated: {result}")
            
            return {
                'success': True,
                'conversation_id': result.get('ConversationID'),
                'originator_conversation_id': result.get('OriginatorConversationID'),
                'response_code': result.get('ResponseCode'),
                'response_description': result.get('ResponseDescription')
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"B2C Payment failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Convenience functions
def initiate_mpesa_payment(user, booking_id, amount):
    """Initiate M-Pesa payment for a booking"""
    mpesa = MpesaAPI()
    
    # Format phone number (remove + and ensure it starts with 254)
    phone = user.phone_number.replace('+', '')
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    
    result = mpesa.stk_push(
        phone_number=phone,
        amount=amount,
        account_reference=f'BOOKING{booking_id}',
        transaction_desc=f'Payment for booking #{booking_id}'
    )
    
    return result


def process_payout(technician, amount, phone_number):
    """Process payout to technician"""
    mpesa = MpesaAPI()
    
    # Format phone number
    phone = phone_number.replace('+', '')
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    
    result = mpesa.b2c_payment(
        phone_number=phone,
        amount=amount,
        occasion='Technician Payout',
        remarks=f'Payout to {technician.email}'
    )
    
    return result


def verify_mpesa_payment(checkout_request_id):
    """Verify M-Pesa payment status"""
    mpesa = MpesaAPI()
    return mpesa.query_stk_status(checkout_request_id)
