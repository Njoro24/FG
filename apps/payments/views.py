from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Payment, Wallet, Transaction, PayoutRequest
from .serializers import PaymentSerializer, WalletSerializer, TransactionSerializer, PayoutRequestSerializer
from .mpesa import initiate_mpesa_payment, process_payout
from apps.accounts.permissions import IsTechnician
import logging

logger = logging.getLogger(__name__)


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
        """Get current wallet balance"""
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        return Response({'balance': wallet.balance})
    
    @action(detail=False, methods=['get'])
    def transactions(self, request):
        """Get wallet transaction history"""
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        transactions = Transaction.objects.filter(wallet=wallet)[:50]
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)


class PayoutRequestViewSet(viewsets.ModelViewSet):
    queryset = PayoutRequest.objects.all()
    serializer_class = PayoutRequestSerializer
    permission_classes = [IsAuthenticated, IsTechnician]
    
    def get_queryset(self):
        return PayoutRequest.objects.filter(technician=self.request.user)
    
    def create(self, request):
        """Create a payout request"""
        amount = request.data.get('amount')
        phone_number = request.data.get('phone_number')
        
        if not amount or not phone_number:
            return Response({
                'error': 'Amount and phone number are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check wallet balance
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        if wallet.balance < float(amount):
            return Response({
                'error': 'Insufficient balance'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create payout request
        payout = PayoutRequest.objects.create(
            technician=request.user,
            amount=amount,
            phone_number=phone_number
        )
        
        return Response(PayoutRequestSerializer(payout).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    """Initiate M-Pesa payment"""
    booking_id = request.data.get('booking_id')
    amount = request.data.get('amount')
    
    if not booking_id or not amount:
        return Response({
            'error': 'Booking ID and amount are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = initiate_mpesa_payment(request.user, booking_id, amount)
        
        if result.get('success'):
            # Create payment record
            Payment.objects.create(
                booking_id=booking_id,
                customer=request.user,
                amount=amount,
                payment_method='mpesa',
                transaction_id=result.get('checkout_request_id')
            )
        
        return Response(result)
    except Exception as e:
        logger.error(f"Payment initiation failed: {e}")
        return Response({
            'error': 'Payment initiation failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([])  # Public endpoint for M-Pesa callback
def mpesa_callback(request):
    """Handle M-Pesa payment callback"""
    logger.info(f"M-Pesa callback received: {request.data}")
    
    # TODO: Implement callback processing
    # 1. Validate callback authenticity
    # 2. Extract transaction details
    # 3. Update payment status
    # 4. Credit wallet if needed
    # 5. Update booking status
    
    return Response({'ResultCode': 0, 'ResultDesc': 'Accepted'})
