"""
M-Pesa Daraja API Integration
Full implementation for STK Push (C2B) and B2C Payouts
"""
import requests
import base64
from datetime import datetime
from django.conf import settings
from django.core.cache import cache
import logging
import json

logger = logging.getLogger(__name__)


class MpesaAPI:
    """M-Pesa Daraja API wrapper"""
    
    def __init__(self):
        self.environment = getattr(settings, 'MPESA_ENVIRONMENT', 'sandbox')
        self.consumer_key = getattr(settings, 'MPESA_CONSUMER_KEY', '')
        self.consumer_secret = getattr(settings, 'MPESA_CONSUMER_SECRET', '')
        self.shortcode = getattr(settings, 'MPESA_SHORTCODE', '174379')
        self.passkey = getattr(settings, 'MPESA_PASSKEY', '')
        self.callback_url = getattr(settings, 'MPESA_CALLBACK_URL', '')
        
        # B2C Configuration
        self.b2c_shortcode = getattr(settings, 'MPESA_B2C_SHORTCODE', '')
        self.b2c_initiator = getattr(settings, 'MPESA_B2C_INITIATOR_NAME', '')
        self.b2c_security_credential = getattr(settings, 'MPESA_B2C_SECURITY_CREDENTIAL', '')
        self.b2c_result_url = getattr(settings, 'MPESA_B2C_RESULT_URL', '')
        self.b2c_timeout_url = getattr(settings, 'MPESA_B2C_TIMEOUT_URL', '')
        
        if self.environment == 'sandbox':
            self.base_url = 'https://sandbox.safaricom.co.ke'
        else:
            self.base_url = 'https://api.safaricom.co.ke'
    
    def get_access_token(self):
        """Get OAuth access token from M-Pesa API"""
        cached_token = cache.get('mpesa_access_token')
        if cached_token:
            return cached_token
        
        url = f'{self.base_url}/oauth/v1/generate?grant_type=client_credentials'
        
        try:
            response = requests.get(
                url,
                auth=(self.consumer_key, self.consumer_secret),
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            token = data.get('access_token')
            
            if token:
                cache.set('mpesa_access_token', token, 3000)
                logger.info("M-Pesa access token obtained")
                return token
            else:
                raise Exception("No access token in response")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get M-Pesa access token: {e}")
            raise
    
    def generate_password(self):
        """Generate password for STK Push"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        data_to_encode = f"{self.shortcode}{self.passkey}{timestamp}"
        encoded = base64.b64encode(data_to_encode.encode())
        return encoded.decode('utf-8'), timestamp
    
    @staticmethod
    def format_phone_number(phone):
        """Format phone number to 254XXXXXXXXX format"""
        phone = str(phone).strip().replace(' ', '').replace('-', '').replace('+', '')
        
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif phone.startswith('7') or phone.startswith('1'):
            phone = '254' + phone
        elif not phone.startswith('254'):
            phone = '254' + phone
        
        return phone
    
    def stk_push(self, phone_number, amount, account_reference, transaction_desc):
        """
        Initiate STK Push (Lipa Na M-Pesa Online)
        """
        try:
            access_token = self.get_access_token()
            password, timestamp = self.generate_password()
            
            url = f'{self.base_url}/mpesa/stkpush/v1/processrequest'
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            formatted_phone = self.format_phone_number(phone_number)
            
            payload = {
                'BusinessShortCode': self.shortcode,
                'Password': password,
                'Timestamp': timestamp,
                'TransactionType': 'CustomerPayBillOnline',
                'Amount': int(float(amount)),
                'PartyA': formatted_phone,
                'PartyB': self.shortcode,
                'PhoneNumber': formatted_phone,
                'CallBackURL': self.callback_url,
                'AccountReference': account_reference[:12],
                'TransactionDesc': transaction_desc[:13]
            }
            
            logger.info(f"STK Push to {formatted_phone} for KES {amount}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            result = response.json()
            
            logger.info(f"STK Push response: {result}")
            
            if result.get('ResponseCode') == '0':
                return {
                    'success': True,
                    'checkout_request_id': result.get('CheckoutRequestID'),
                    'merchant_request_id': result.get('MerchantRequestID'),
                    'response_code': result.get('ResponseCode'),
                    'response_description': result.get('ResponseDescription'),
                    'customer_message': result.get('CustomerMessage')
                }
            else:
                error_msg = result.get('errorMessage') or result.get('ResponseDescription', 'STK Push failed')
                
                # Clear token cache if access token error
                if 'access token' in error_msg.lower():
                    cache.delete('mpesa_access_token')
                
                return {
                    'success': False,
                    'error': error_msg,
                    'response_code': result.get('ResponseCode')
                }
                
        except Exception as e:
            logger.error(f"STK Push failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def query_stk_status(self, checkout_request_id):
        """Query the status of an STK Push transaction"""
        try:
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
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            return response.json()
            
        except Exception as e:
            logger.error(f"STK status query failed: {e}")
            return None
    
    def b2c_payment(self, phone_number, amount, occasion='', remarks=''):
        """B2C Payment - Platform pays technician"""
        try:
            access_token = self.get_access_token()
            
            url = f'{self.base_url}/mpesa/b2c/v1/paymentrequest'
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            formatted_phone = self.format_phone_number(phone_number)
            
            payload = {
                'InitiatorName': self.b2c_initiator,
                'SecurityCredential': self.b2c_security_credential,
                'CommandID': 'BusinessPayment',
                'Amount': int(float(amount)),
                'PartyA': self.b2c_shortcode,
                'PartyB': formatted_phone,
                'Remarks': remarks[:100] if remarks else 'Payout',
                'QueueTimeOutURL': self.b2c_timeout_url,
                'ResultURL': self.b2c_result_url,
                'Occasion': occasion[:100] if occasion else 'Payout'
            }
            
            logger.info(f"B2C Payment to {formatted_phone} for KES {amount}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            result = response.json()
            
            if result.get('ResponseCode') == '0':
                return {
                    'success': True,
                    'conversation_id': result.get('ConversationID'),
                    'originator_conversation_id': result.get('OriginatorConversationID'),
                    'response_code': result.get('ResponseCode'),
                    'response_description': result.get('ResponseDescription')
                }
            else:
                return {
                    'success': False,
                    'error': result.get('errorMessage') or result.get('ResponseDescription', 'B2C failed')
                }
                
        except Exception as e:
            logger.error(f"B2C Payment failed: {e}")
            return {'success': False, 'error': str(e)}


def initiate_job_payment(job_payment, phone_number):
    """Initiate M-Pesa STK Push for a job payment"""
    mpesa = MpesaAPI()
    return mpesa.stk_push(
        phone_number=phone_number,
        amount=job_payment.amount_paid,
        account_reference=job_payment.payment_ref,
        transaction_desc=f'Job {job_payment.job_id}'
    )


def initiate_mpesa_payment(user, booking_id, amount):
    """Legacy function"""
    mpesa = MpesaAPI()
    phone = getattr(user, 'phone_number', '')
    return mpesa.stk_push(phone, amount, f'BK{booking_id}', f'Booking {booking_id}')


def process_technician_payout(payout):
    """Process M-Pesa B2C payout to technician"""
    mpesa = MpesaAPI()
    return mpesa.b2c_payment(
        phone_number=payout.phone_number,
        amount=payout.amount,
        occasion=f'Payout {payout.payout_ref}',
        remarks='FundiGO payout'
    )


def process_payout(technician, amount, phone_number):
    """Legacy function"""
    mpesa = MpesaAPI()
    return mpesa.b2c_payment(phone_number, amount, 'Payout', f'Payout to {technician.email}')


def verify_mpesa_payment(checkout_request_id):
    """Verify M-Pesa payment status"""
    mpesa = MpesaAPI()
    return mpesa.query_stk_status(checkout_request_id)


def parse_stk_callback(callback_data):
    """Parse M-Pesa STK Push callback data"""
    try:
        body = callback_data.get('Body', {})
        stk_callback = body.get('stkCallback', {})
        
        result = {
            'merchant_request_id': stk_callback.get('MerchantRequestID'),
            'checkout_request_id': stk_callback.get('CheckoutRequestID'),
            'result_code': stk_callback.get('ResultCode'),
            'result_desc': stk_callback.get('ResultDesc'),
        }
        
        if result['result_code'] == 0:
            callback_metadata = stk_callback.get('CallbackMetadata', {})
            items = callback_metadata.get('Item', [])
            
            for item in items:
                name = item.get('Name')
                value = item.get('Value')
                
                if name == 'Amount':
                    result['amount'] = value
                elif name == 'MpesaReceiptNumber':
                    result['mpesa_receipt'] = value
                elif name == 'TransactionDate':
                    result['transaction_date'] = value
                elif name == 'PhoneNumber':
                    result['phone_number'] = value
        
        return result
    except Exception as e:
        logger.error(f"Error parsing STK callback: {e}")
        return None


def parse_b2c_result(result_data):
    """Parse M-Pesa B2C result callback data"""
    try:
        result = result_data.get('Result', {})
        
        parsed = {
            'result_type': result.get('ResultType'),
            'result_code': result.get('ResultCode'),
            'result_desc': result.get('ResultDesc'),
            'originator_conversation_id': result.get('OriginatorConversationID'),
            'conversation_id': result.get('ConversationID'),
            'transaction_id': result.get('TransactionID'),
        }
        
        if parsed['result_code'] == 0:
            result_params = result.get('ResultParameters', {})
            params = result_params.get('ResultParameter', [])
            
            for param in params:
                name = param.get('Key')
                value = param.get('Value')
                
                if name == 'TransactionAmount':
                    parsed['amount'] = value
                elif name == 'TransactionReceipt':
                    parsed['receipt'] = value
        
        return parsed
    except Exception as e:
        logger.error(f"Error parsing B2C result: {e}")
        return None
