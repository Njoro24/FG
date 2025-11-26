from django.contrib import admin
from .models import Payment, Wallet, Transaction, PayoutRequest


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'amount', 'payment_method', 'status', 'created_at']
    list_filter = ['status', 'payment_method']
    search_fields = ['customer__email', 'transaction_id']


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance', 'updated_at']
    search_fields = ['user__email']
    readonly_fields = ['balance', 'created_at', 'updated_at']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['wallet', 'type', 'amount', 'balance_after', 'success', 'created_at']
    list_filter = ['type', 'success']
    search_fields = ['wallet__user__email', 'reference']
    readonly_fields = ['created_at']


@admin.register(PayoutRequest)
class PayoutRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'technician', 'amount', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['technician__email', 'phone_number']
    actions = ['approve_payout', 'reject_payout']
    
    def approve_payout(self, request, queryset):
        queryset.update(status='approved')
        self.message_user(request, f"{queryset.count()} payout requests approved")
    approve_payout.short_description = "Approve selected payout requests"
    
    def reject_payout(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, f"{queryset.count()} payout requests rejected")
    reject_payout.short_description = "Reject selected payout requests"
