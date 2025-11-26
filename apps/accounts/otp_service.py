import random
import string
from django.core.cache import cache
from django.conf import settings


def generate_otp(length=None):
    """Generate a random OTP code"""
    length = length or getattr(settings, 'OTP_LENGTH', 6)
    return ''.join(random.choices(string.digits, k=length))


def store_otp(email, otp, ttl=None):
    """Store OTP in Redis with expiry"""
    ttl = ttl or getattr(settings, 'OTP_EXPIRY_SECONDS', 600)
    key = f"otp:{email}"
    cache.set(key, otp, ttl)
    return True


def verify_otp(email, otp):
    """Verify OTP from Redis"""
    key = f"otp:{email}"
    stored_otp = cache.get(key)
    
    if stored_otp and stored_otp == otp:
        cache.delete(key)  # Delete after successful verification
        return True
    return False


def delete_otp(email):
    """Delete OTP from Redis"""
    key = f"otp:{email}"
    cache.delete(key)
    return True


def get_remaining_ttl(email):
    """Get remaining TTL for OTP"""
    key = f"otp:{email}"
    return cache.ttl(key)
