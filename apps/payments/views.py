"""
Payment Views - Full M-Pesa Payment Flow with Escrow System

Flow:
1. Client initiates payment → STK Push sent to phone
2. Client confirms on phone → Callback received
3. Money held in escrow until job completion
4. Job completed + approved → Release payment to technician (minus 15%)
"""
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction as db_transaction
from decimal import Decimal
import logging

from .models import (
    Payment, Wallet, Transaction, PayoutRequest,
    JobPayment, Payout, PlatformEarnings
)
from .serializers import (
    PaymentSerializer, WalletSerializer, TransactionSerializer,
    PayoutRequestSerializer, JobPaymentSerializer, PayoutSerializer
)
from .mpesa import (
    MpesaAPI, initiate_job_payment, verify_mpesa_payment,
    parse_stk_callback, parse_b2c_result, process_technician_payout
)
from apps.bookings.models import JobPosting
from apps.accounts.permissions import IsTechnician

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_job_payment_view(request):
    """Client initiates payment for a job - sends STK Push"""
    job_id = request.data.get('job_id')
    phone_number = request.data.get('phone_number')
    
    if not job_id:
        return Response({'success': False, 'error': 'job_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        job = JobPosting.objects.get(id=job_id)
        
        if job.customer != request.user:
            return Response({'success': False, 'error': 'You can only pay for your own jobs'}, status=status.HTTP_403_FORBIDDEN)
        
        if not job.assigned_technician:
            return Response({'success': False, 'error': 'Job must have an assigned technician'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not job.final_price:
            return Response({'success': False, 'error': 'Job must have a final price set'}, status=status.HTTP_400_BAD_REQUEST)
        
        if hasattr(job, 'job_payment') and job.job_payment.status in ['paid', 'held', 'released']:
            return Response({'success': False, 'error': 'Payment already made for this job'}, status=status.HTTP_400_BAD_REQUEST)
        
        payment_phone = phone_number or getattr(request.user, 'phone_number', '')
        if not payment_phone:
            return Response({'success': False, 'error': 'Phone number is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        job_payment, created = JobPayment.objects.get_or_create(
            job=job,
            defaults={
                'client': request.user,
                'technician': job.assigned_technician,
                'amount_paid': job.final_price,
                'phone_number': payment_phone,
                'payment_method': 'mpesa'
            }
        )
        
        if not created:
            job_payment.phone_number = payment_phone
            job_payment.status = 'processing'
            job_payment.save()
        
        result = initiate_job_payment(job_payment, payment_phone)
        
        if result.get('success'):
            job_payment.mpesa_checkout_request_id = result.get('checkout_request_id', '')
            job_payment.mpesa_merchant_request_id = result.get('merchant_request_id', '')
            job_payment.status = 'processing'
            job_payment.save()
            
            return Response({
                'success': True,
                'message': 'STK Push sent to your phone. Enter your M-Pesa PIN to complete payment.',
                'payment_ref': job_payment.payment_ref,
                'checkout_request_id': result.get('checkout_request_id'),
                'amount': str(job_payment.amount_paid),
                'platform_fee': str(job_payment.platform_fee),
                'technician_amount': str(job_payment.technician_amount)
            })
        else:
            job_payment.status = 'failed'
            job_payment.save()
            return Response({'success': False, 'error': result.get('error', 'Payment failed')}, status=status.HTTP_400_BAD_REQUEST)
            
    except JobPosting.DoesNotExist:
        return Response({'success': False, 'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Payment error: {e}")
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def mpesa_stk_callback(request):
    """M-Pesa STK Push callback - called by Safaricom
    
    Security Note: In production, you should:
    1. Whitelist Safaricom IPs
    2. Verify the callback signature if available
    3. Use HTTPS only
    """
    # Log callback for debugging (remove sensitive data in production)
    logger.info(f"M-Pesa Callback received from IP: {request.META.get('REMOTE_ADDR')}")
    
    # Basic validation - ensure we have the expected structure
    if not request.data or 'Body' not in request.data:
        logger.warning("Invalid callback structure received")
        return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})
    
    try:
        callback_data = parse_stk_callback(request.data)
        if not callback_data:
            return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})
        
        checkout_request_id = callback_data.get('checkout_request_id')
        result_code = callback_data.get('result_code')
        
        if not checkout_request_id:
            logger.warning("Missing checkout_request_id in callback")
            return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})
        
        try:
            job_payment = JobPayment.objects.get(mpesa_checkout_request_id=checkout_request_id)
        except JobPayment.DoesNotExist:
            logger.error(f"Payment not found: {checkout_request_id}")
            return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})
        
        if result_code == 0:
            with db_transaction.atomic():
                job_payment.status = 'held'
                job_payment.mpesa_receipt_number = callback_data.get('mpesa_receipt', '')
                job_payment.paid_at = timezone.now()
                job_payment.save()
                
                job = job_payment.job
                job.payment_status = 'paid'
                job.save()
                
                PlatformEarnings.objects.get_or_create(
                    job_payment=job_payment,
                    defaults={'amount': job_payment.platform_fee}
                )
                
            logger.info(f"Payment {job_payment.payment_ref} successful - HELD in escrow")
        else:
            job_payment.status = 'failed'
            job_payment.save()
            logger.info(f"Payment {job_payment.payment_ref} failed")
        
        return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})
    except Exception as e:
        logger.error(f"Callback error: {e}")
        return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_payment_status(request):
    """Check payment status"""
    payment_ref = request.data.get('payment_ref')
    checkout_request_id = request.data.get('checkout_request_id')
    
    try:
        if payment_ref:
            job_payment = JobPayment.objects.get(payment_ref=payment_ref)
        elif checkout_request_id:
            job_payment = JobPayment.objects.get(mpesa_checkout_request_id=checkout_request_id)
        else:
            return Response({'success': False, 'error': 'payment_ref or checkout_request_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if job_payment.status == 'processing' and job_payment.mpesa_checkout_request_id:
            mpesa_status = verify_mpesa_payment(job_payment.mpesa_checkout_request_id)
            if mpesa_status and mpesa_status.get('ResultCode') == '0':
                job_payment.status = 'held'
                job_payment.paid_at = timezone.now()
                job_payment.save()
        
        return Response({
            'success': True,
            'payment_ref': job_payment.payment_ref,
            'status': job_payment.status,
            'amount_paid': str(job_payment.amount_paid),
            'mpesa_receipt': job_payment.mpesa_receipt_number,
            'paid_at': job_payment.paid_at
        })
    except JobPayment.DoesNotExist:
        return Response({'success': False, 'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def release_payment(request):
    """Release payment to technician after job completion"""
    job_id = request.data.get('job_id')
    
    if not job_id:
        return Response({'success': False, 'error': 'job_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        job = JobPosting.objects.get(id=job_id)
        
        if job.customer != request.user:
            return Response({'success': False, 'error': 'Only job owner can release payment'}, status=status.HTTP_403_FORBIDDEN)
        
        if job.status != 'completed':
            return Response({'success': False, 'error': 'Job must be completed first'}, status=status.HTTP_400_BAD_REQUEST)
        
        job_payment = job.job_payment
        
        if job_payment.status != 'held':
            return Response({'success': False, 'error': f'Cannot release. Status: {job_payment.status}'}, status=status.HTTP_400_BAD_REQUEST)
        
        with db_transaction.atomic():
            technician_wallet, _ = Wallet.objects.get_or_create(user=job_payment.technician)
            technician_wallet.credit(
                amount=job_payment.technician_amount,
                transaction_type='earning',
                reference=job_payment.payment_ref,
                metadata={'job_id': job.id, 'job_title': job.title}
            )
            
            job_payment.status = 'released'
            job_payment.released_at = timezone.now()
            job_payment.save()
            
            job.payment_status = 'released'
            job.save()
        
        return Response({
            'success': True,
            'message': 'Payment released to technician',
            'technician_amount': str(job_payment.technician_amount),
            'platform_fee': str(job_payment.platform_fee)
        })
    except JobPosting.DoesNotExist:
        return Response({'success': False, 'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTechnician])
def request_payout(request):
    """Technician requests payout"""
    amount = request.data.get('amount')
    phone_number = request.data.get('phone_number')
    payout_method = request.data.get('payout_method', 'mpesa')
    
    if not amount:
        return Response({'success': False, 'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        amount = Decimal(str(amount))
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        
        if wallet.balance < amount:
            return Response({'success': False, 'error': f'Insufficient balance. Available: KES {wallet.balance}'}, status=status.HTTP_400_BAD_REQUEST)
        
        if amount < 100:
            return Response({'success': False, 'error': 'Minimum payout is KES 100'}, status=status.HTTP_400_BAD_REQUEST)
        
        payout_phone = phone_number or getattr(request.user, 'phone_number', '')
        
        if payout_method == 'mpesa' and not payout_phone:
            return Response({'success': False, 'error': 'Phone number required for M-Pesa'}, status=status.HTTP_400_BAD_REQUEST)
        
        with db_transaction.atomic():
            wallet.debit(amount, 'payout', 'Payout request', {'method': payout_method})
            
            payout = Payout.objects.create(
                technician=request.user,
                amount=amount,
                payout_method=payout_method,
                phone_number=payout_phone,
                status='pending'
            )
        
        if payout_method == 'mpesa':
            result = process_technician_payout(payout)
            
            if result.get('success'):
                payout.status = 'processing'
                payout.mpesa_conversation_id = result.get('conversation_id', '')
                payout.save()
                
                return Response({
                    'success': True,
                    'message': 'Payout initiated. You will receive the money shortly.',
                    'payout_ref': payout.payout_ref,
                    'amount': str(payout.amount)
                })
            else:
                wallet.credit(amount, 'refund', f'Payout failed: {payout.payout_ref}')
                payout.status = 'failed'
                payout.failure_reason = result.get('error', 'Unknown error')
                payout.save()
                return Response({'success': False, 'error': result.get('error')}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                'success': True,
                'message': 'Bank transfer request submitted. Processed within 24-48 hours.',
                'payout_ref': payout.payout_ref
            })
    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def mpesa_b2c_result(request):
    """M-Pesa B2C result callback"""
    logger.info(f"B2C Result: {request.data}")
    
    try:
        result_data = parse_b2c_result(request.data)
        if not result_data:
            return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})
        
        conversation_id = result_data.get('conversation_id')
        
        try:
            payout = Payout.objects.get(mpesa_conversation_id=conversation_id)
        except Payout.DoesNotExist:
            return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})
        
        if result_data.get('result_code') == 0:
            payout.status = 'completed'
            payout.mpesa_transaction_id = result_data.get('transaction_id', '')
            payout.completed_at = timezone.now()
            payout.save()
        else:
            wallet = Wallet.objects.get(user=payout.technician)
            wallet.credit(payout.amount, 'refund', f'Payout failed: {payout.payout_ref}')
            payout.status = 'failed'
            payout.failure_reason = result_data.get('result_desc', 'Unknown')
            payout.save()
        
        return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})
    except Exception as e:
        logger.error(f"B2C result error: {e}")
        return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})


@api_view(['POST'])
@permission_classes([AllowAny])
def mpesa_b2c_timeout(request):
    """M-Pesa B2C timeout callback"""
    logger.warning(f"B2C Timeout: {request.data}")
    return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_wallet_balance(request):
    """Get wallet balance"""
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    return Response({'balance': str(wallet.balance), 'held_balance': str(wallet.held_balance)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_wallet_transactions(request):
    """Get wallet transactions"""
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    transactions = Transaction.objects.filter(wallet=wallet)[:50]
    return Response({'transactions': TransactionSerializer(transactions, many=True).data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_payments(request):
    """Get client's payment history"""
    payments = JobPayment.objects.filter(client=request.user)
    return Response({'payments': JobPaymentSerializer(payments, many=True).data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_earnings(request):
    """Get technician's earnings"""
    payments = JobPayment.objects.filter(technician=request.user, status__in=['held', 'released'])
    total_earned = sum(p.technician_amount for p in payments.filter(status='released'))
    pending = sum(p.technician_amount for p in payments.filter(status='held'))
    
    return Response({
        'total_earned': str(total_earned),
        'pending_release': str(pending),
        'payments': JobPaymentSerializer(payments, many=True).data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_payouts(request):
    """Get payout history"""
    payouts = Payout.objects.filter(technician=request.user)
    return Response({'payouts': PayoutSerializer(payouts, many=True).data})


# Legacy ViewSets
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Payment.objects.filter(customer=self.request.user)


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Wallet.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def balance(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        return Response({'balance': str(wallet.balance)})


class PayoutRequestViewSet(viewsets.ModelViewSet):
    queryset = PayoutRequest.objects.all()
    serializer_class = PayoutRequestSerializer
    permission_classes = [IsAuthenticated, IsTechnician]
    
    def get_queryset(self):
        return PayoutRequest.objects.filter(technician=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    """Legacy payment endpoint"""
    from .mpesa import initiate_mpesa_payment
    
    booking_id = request.data.get('booking_id')
    amount = request.data.get('amount')
    
    if not booking_id or not amount:
        return Response({'error': 'Booking ID and amount required'}, status=status.HTTP_400_BAD_REQUEST)
    
    result = initiate_mpesa_payment(request.user, booking_id, amount)
    return Response(result)


@api_view(['POST'])
@permission_classes([AllowAny])
def mpesa_callback(request):
    """Legacy callback"""
    return mpesa_stk_callback(request)
