from rest_framework import permissions


class IsTechnician(permissions.BasePermission):
    """Permission class to check if user is a technician."""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'technician'


class IsCustomer(permissions.BasePermission):
    """Permission class to check if user is a customer."""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'customer'


class IsVerifiedTechnician(permissions.BasePermission):
    """Permission class to check if user is a verified technician."""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated or request.user.user_type != 'technician':
            return False
        
        try:
            return request.user.technician_profile.verification_status == 'verified'
        except:
            return False
