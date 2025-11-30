from django.db import models
from django.db import transaction as db_transaction
from apps.accounts.models import User
from apps.bookings.models import Booking, JobPosting
from decimal import Decimal
import uuid


class Wallet(models.Model):
    """User wallet for storing earnings (technicians) or balance (clients)"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    held_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Escrow
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Wallet: {self.user.email} - Balance: {self.balance}, Held: {self.held_balance}"
    
    def credit(self, amount, transaction_type, reference, metadata=None):
        """Add funds to wallet"""
        with db_transaction.atomic():
            self.balance += Decimal(str(amount))
            self.save()
            Transaction.objects.create(
                wallet=self,
                type=transaction_type,
                amount=amount,
                balance_after=self.balance,
                reference=reference,
                success=True,
                metadata=metadata or {}
            )
    
    def debit(self, amount, transaction_type, reference, metadata=None):
        """Remove funds from wallet"""
        if self.balance < Decimal(str(amount)):
            raise ValueError("Insufficient balance")
        
        with db_transaction.atomic():
            self.balance -= Decimal(str(amount))
            self.save()
            Transaction.objects.create(
                wallet=self,
                type=transaction_type,
                amount=-Decimal(str(amount)),
                balance_after=self.balance,
                reference=reference,
                success=True,
                metadata=metadata or {}
            )
    
    def hold(self, amount, reference, metadata=None):
        """Hold funds in escrow"""
        with db_transaction.atomic():
            self.held_balance += Decimal(str(amount))
            self.save()
            Transaction.objects.create(
                wallet=self,
                type='escrow_hold',
                amount=amount,
                balance_after=self.balance,
                reference=reference,
                success=True,
                metadata=metadata or {}
            )
    
    def release_hold(self, amount, reference, metadata=None):
        """Release held funds from escrow"""
        if self.held_balance < Decimal(str(amount)):
            raise ValueError("Insufficient held balance")
        
        with db_transaction.atomic():
            self.held_balance -= Decimal(str(amount))
            self.save()


class Transaction(models.Model):
    """Transaction history for wallets"""
    TRANSACTION_TYPES = (
        ('topup', 'Top Up'),
        ('payment', 'Payment'),
        ('payout', 'Payout'),
        ('commission', 'Commission'),
        ('refund', 'Refund'),
        ('earning', 'Earning'),
        ('escrow_hold', 'Escrow Hold'),
        ('escrow_release', 'Escrow Release'),
    )
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100)
    success = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.type} - {self.amount} - {self.wallet.user.email}"


class JobPayment(models.Model):
    """
    Main payment record for job postings - ESCROW SYSTEM
    Client pays → Platform holds → Job completed → Platform releases to technician (minus 15%)
    """
    PAYMENT_STATUS = (
        ('pending', 'Pending'),           # Payment not yet made
        ('processing', 'Processing'),      # STK Push sent, waiting for confirmation
        ('paid', 'Paid'),                  # Client paid, money in platform escrow
        ('held', 'Held in Escrow'),        # Money held until job completion
        ('released', 'Released'),          # Money released to technician
        ('refunded', 'Refunded'),          # Money refunded to client
        ('failed', 'Failed'),              # Payment failed
    )
    
    PAYMENT_METHOD = (
        ('mpesa', 'M-Pesa'),
        ('bank', 'Bank Transfer'),
    )
    
    # Unique payment reference
    payment_ref = models.CharField(max_length=50, unique=True, editable=False)
    
    # Link to job
    job = models.OneToOneField(JobPosting, on_delete=models.CASCADE, related_name='job_payment')
    
    # Parties involved
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='client_payments')
    technician = models.ForeignKey(User, on_delete=models.CASCADE, related_name='technician_payments')
    
    # Amounts
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)  # Full amount from client
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2)  # 15% commission
    technician_amount = models.DecimalField(max_digits=10, decimal_places=2)  # 85% to technician
    
    # Payment details
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD, default='mpesa')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # M-Pesa specific fields
    mpesa_checkout_request_id = models.CharField(max_length=100, blank=True)
    mpesa_merchant_request_id = models.CharField(max_length=100, blank=True)
    mpesa_receipt_number = models.CharField(max_length=100, blank=True)
    mpesa_transaction_date = models.DateTimeField(null=True, blank=True)
    
    # Phone number used for payment
    phone_number = models.CharField(max_length=15, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.payment_ref:
            self.payment_ref = f"FG-{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate fees if amount is set
        if self.amount_paid and not self.platform_fee:
            self.calculate_fees()
        
        super().save(*args, **kwargs)
    
    def calculate_fees(self):
        """Calculate 15% platform fee and 85% technician amount"""
        commission_rate = Decimal('0.15')
        self.platform_fee = self.amount_paid * commission_rate
        self.technician_amount = self.amount_paid - self.platform_fee
    
    def __str__(self):
        return f"Payment {self.payment_ref} - Job #{self.job_id} - KES {self.amount_paid}"


class Payout(models.Model):
    """
    Payout records for technicians - B2C payments
    """
    PAYOUT_STATUS = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    PAYOUT_METHOD = (
        ('mpesa', 'M-Pesa'),
        ('bank', 'Bank Transfer'),
    )
    
    # Unique payout reference
    payout_ref = models.CharField(max_length=50, unique=True, editable=False)
    
    # Link to job payment (optional - can be manual payout)
    job_payment = models.ForeignKey(JobPayment, on_delete=models.SET_NULL, null=True, blank=True, related_name='payouts')
    
    # Technician receiving payout
    technician = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payouts')
    
    # Amount
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payout details
    payout_method = models.CharField(max_length=20, choices=PAYOUT_METHOD, default='mpesa')
    phone_number = models.CharField(max_length=15, blank=True)  # For M-Pesa
    bank_account = models.CharField(max_length=50, blank=True)  # For bank transfer
    bank_name = models.CharField(max_length=100, blank=True)
    
    status = models.CharField(max_length=20, choices=PAYOUT_STATUS, default='pending')
    
    # M-Pesa B2C specific fields
    mpesa_conversation_id = models.CharField(max_length=100, blank=True)
    mpesa_originator_conversation_id = models.CharField(max_length=100, blank=True)
    mpesa_transaction_id = models.CharField(max_length=100, blank=True)
    
    # Failure reason if any
    failure_reason = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.payout_ref:
            self.payout_ref = f"PO-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Payout {self.payout_ref} - {self.technician.email} - KES {self.amount}"


# Keep legacy models for backward compatibility
class Payment(models.Model):
    """Legacy payment model - keeping for backward compatibility"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    
    PAYMENT_METHOD = (
        ('mpesa', 'M-Pesa'),
        ('wallet', 'Wallet'),
        ('cash', 'Cash'),
    )
    
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    mpesa_receipt = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Payment #{self.id} - {self.customer.email} - {self.amount}"


class PayoutRequest(models.Model):
    """Legacy payout request model"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    )
    
    technician = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payout_requests')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    phone_number = models.CharField(max_length=15)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True)
    mpesa_transaction_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Payout Request #{self.id} - {self.technician.email} - {self.amount}"


class PlatformEarnings(models.Model):
    """Track platform earnings (15% commission from each job)"""
    job_payment = models.OneToOneField(JobPayment, on_delete=models.CASCADE, related_name='platform_earning')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Platform Earnings"
    
    def __str__(self):
        return f"Platform Earning - KES {self.amount} from {self.job_payment.payment_ref}"
