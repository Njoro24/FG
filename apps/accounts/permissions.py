from rest_framework import permissions


class IsTechnician(permissions.BasePermission):
    """Permission class to check if user is a technician."""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_technician


class IsCustomer(permissions.BasePermission):
    """Permission class to check if user is a customer."""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and not request.user.is_technician


class IsVerifiedTechnician(permissions.BasePermission):
    """Permission class to check if user is a verified technician."""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated or not request.user.is_technician:
            return False
        
        try:
            return request.user.technician_profile.verification_status == 'approved'
        except AttributeError:
            return False


class IsKYCApprovedTechnician(permissions.BasePermission):
    """Permission class to check if technician has approved KYC."""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated or not request.user.is_technician:
            return False
        
        try:
            return request.user.technician_profile.kyc_status == 'approved'
        except AttributeError:
            return False
