from django.db import models
from django.db import transaction as db_transaction
from apps.accounts.models import User
from apps.bookings.models import Booking


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Wallet: {self.user.email} - {self.balance}"
    
    def credit(self, amount, transaction_type, reference, metadata=None):
        """Add funds to wallet"""
        with db_transaction.atomic():
            self.balance += amount
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
        if self.balance < amount:
            raise ValueError("Insufficient balance")
        
        with db_transaction.atomic():
            self.balance -= amount
            self.save()
            Transaction.objects.create(
                wallet=self,
                type=transaction_type,
                amount=-amount,
                balance_after=self.balance,
                reference=reference,
                success=True,
                metadata=metadata or {}
            )


class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('topup', 'Top Up'),
        ('payment', 'Payment'),
        ('payout', 'Payout'),
        ('commission', 'Commission'),
        ('refund', 'Refund'),
        ('earning', 'Earning'),
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


class Payment(models.Model):
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
