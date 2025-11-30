from django.contrib import admin
from .models import (
    Wallet, Transaction, Payment, PayoutRequest,
    JobPayment, Payout, PlatformEarnings
)


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance', 'held_balance', 'created_at', 'updated_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['balance', 'held_balance', 'created_at', 'updated_at']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'wallet', 'type', 'amount', 'balance_after', 'reference', 'created_at']
    list_filter = ['type', 'success', 'created_at']
    search_fields = ['wallet__user__email', 'reference']
    readonly_fields = ['wallet', 'type', 'amount', 'balance_after', 'reference', 'metadata', 'created_at']


@admin.register(JobPayment)
class JobPaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_ref', 'job', 'client', 'technician',
        'amount_paid', 'platform_fee', 'technician_amount',
        'status', 'payment_method', 'created_at'
    ]
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = [
        'payment_ref', 'client__email', 'technician__email',
        'mpesa_receipt_number'
    ]
    readonly_fields = [
        'payment_ref', 'platform_fee', 'technician_amount',
        'mpesa_checkout_request_id', 'mpesa_merchant_request_id',
        'mpesa_receipt_number', 'mpesa_transaction_date',
        'created_at', 'paid_at', 'released_at'
    ]
    
    fieldsets = (
        ('Payment Info', {
            'fields': ('payment_ref', 'job', 'client', 'technician', 'status')
        }),
        ('Amounts', {
            'fields': ('amount_paid', 'platform_fee', 'technician_amount')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'phone_number')
        }),
        ('M-Pesa Details', {
            'fields': (
                'mpesa_checkout_request_id', 'mpesa_merchant_request_id',
                'mpesa_receipt_number', 'mpesa_transaction_date'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'paid_at', 'released_at')
        }),
    )
    
    actions = ['release_payments']
    
    def release_payments(self, request, queryset):
        """Admin action to release held payments"""
        from django.utils import timezone
        from django.db import transaction as db_transaction
        
        released = 0
        for payment in queryset.filter(status='held'):
            with db_transaction.atomic():
                # Credit technician wallet
                wallet, _ = Wallet.objects.get_or_create(user=payment.technician)
                wallet.credit(
                    amount=payment.technician_amount,
                    transaction_type='earning',
                    reference=payment.payment_ref,
                    metadata={'admin_release': True}
                )
                
                payment.status = 'released'
                payment.released_at = timezone.now()
                payment.save()
                released += 1
        
        self.message_user(request, f'{released} payment(s) released successfully.')
    
    release_payments.short_description = "Release selected payments to technicians"


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = [
        'payout_ref', 'technician', 'amount', 'payout_method',
        'status', 'created_at', 'completed_at'
    ]
    list_filter = ['status', 'payout_method', 'created_at']
    search_fields = ['payout_ref', 'technician__email', 'phone_number']
    readonly_fields = [
        'payout_ref', 'mpesa_conversation_id',
        'mpesa_originator_conversation_id', 'mpesa_transaction_id',
        'created_at', 'completed_at'
    ]


@admin.register(PlatformEarnings)
class PlatformEarningsAdmin(admin.ModelAdmin):
    list_display = ['id', 'job_payment', 'amount', 'created_at']
    list_filter = ['created_at']
    search_fields = ['job_payment__payment_ref']
    readonly_fields = ['job_payment', 'amount', 'created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


# Legacy models
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'booking', 'customer', 'amount', 'payment_method', 'status', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['customer__email', 'transaction_id', 'mpesa_receipt']


@admin.register(PayoutRequest)
class PayoutRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'technician', 'amount', 'phone_number', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['technician__email', 'phone_number']
