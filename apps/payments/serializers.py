from rest_framework import serializers
from .models import Payment, Wallet, Transaction, PayoutRequest, JobPayment, Payout, PlatformEarnings


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['customer', 'status', 'transaction_id', 'created_at', 'completed_at']


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['id', 'user', 'balance', 'held_balance', 'created_at', 'updated_at']
        read_only_fields = ['user', 'balance', 'held_balance', 'created_at', 'updated_at']


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ['wallet', 'balance_after', 'created_at']


class PayoutRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutRequest
        fields = '__all__'
        read_only_fields = ['technician', 'status', 'created_at', 'processed_at']


class JobPaymentSerializer(serializers.ModelSerializer):
    """Serializer for job payments with escrow"""
    client_name = serializers.SerializerMethodField()
    technician_name = serializers.SerializerMethodField()
    job_title = serializers.SerializerMethodField()
    
    class Meta:
        model = JobPayment
        fields = [
            'id', 'payment_ref', 'job', 'job_title',
            'client', 'client_name', 'technician', 'technician_name',
            'amount_paid', 'platform_fee', 'technician_amount',
            'payment_method', 'status', 'phone_number',
            'mpesa_receipt_number', 'created_at', 'paid_at', 'released_at'
        ]
        read_only_fields = [
            'payment_ref', 'platform_fee', 'technician_amount',
            'mpesa_checkout_request_id', 'mpesa_merchant_request_id',
            'mpesa_receipt_number', 'created_at', 'paid_at', 'released_at'
        ]
    
    def get_client_name(self, obj):
        return obj.client.get_full_name() or obj.client.email
    
    def get_technician_name(self, obj):
        return obj.technician.get_full_name() or obj.technician.email
    
    def get_job_title(self, obj):
        return obj.job.title if obj.job else None


class PayoutSerializer(serializers.ModelSerializer):
    """Serializer for technician payouts"""
    technician_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Payout
        fields = [
            'id', 'payout_ref', 'technician', 'technician_name',
            'amount', 'payout_method', 'phone_number',
            'bank_account', 'bank_name', 'status',
            'mpesa_transaction_id', 'failure_reason',
            'created_at', 'completed_at'
        ]
        read_only_fields = [
            'payout_ref', 'mpesa_conversation_id',
            'mpesa_originator_conversation_id', 'mpesa_transaction_id',
            'created_at', 'completed_at'
        ]
    
    def get_technician_name(self, obj):
        return obj.technician.get_full_name() or obj.technician.email


class PlatformEarningsSerializer(serializers.ModelSerializer):
    """Serializer for platform earnings (admin use)"""
    payment_ref = serializers.SerializerMethodField()
    
    class Meta:
        model = PlatformEarnings
        fields = ['id', 'job_payment', 'payment_ref', 'amount', 'created_at']
    
    def get_payment_ref(self, obj):
        return obj.job_payment.payment_ref if obj.job_payment else None


class InitiatePaymentSerializer(serializers.Serializer):
    """Serializer for initiating job payment"""
    job_id = serializers.IntegerField(required=True)
    phone_number = serializers.CharField(max_length=15, required=False)


class PayoutRequestCreateSerializer(serializers.Serializer):
    """Serializer for creating payout request"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    phone_number = serializers.CharField(max_length=15, required=False)
    payout_method = serializers.ChoiceField(
        choices=[('mpesa', 'M-Pesa'), ('bank', 'Bank Transfer')],
        default='mpesa'
    )
    bank_account = serializers.CharField(max_length=50, required=False)
    bank_name = serializers.CharField(max_length=100, required=False)
