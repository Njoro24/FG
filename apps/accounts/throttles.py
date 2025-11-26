from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class OTPRequestThrottle(AnonRateThrottle):
    """Throttle OTP requests to prevent abuse"""
    rate = '5/hour'
    scope = 'otp'


class OTPVerifyThrottle(AnonRateThrottle):
    """Throttle OTP verification attempts"""
    rate = '10/hour'
    scope = 'otp_verify'
