# FundiGO Backend

Django REST API for the FundiGO platform.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## API Endpoints

### Authentication
- `POST /api/auth/signup/` - Register
- `POST /api/auth/login/` - Login
- `POST /api/auth/verify-otp/` - Verify OTP
- `POST /api/auth/token/refresh/` - Refresh token

### Profile
- `GET /api/auth/profile/` - Get profile
- `PATCH /api/auth/profile/update/` - Update profile
- `POST /api/auth/change-password/` - Change password

### Bookings
- `GET /api/bookings/` - List bookings
- `POST /api/bookings/` - Create booking

### Payments
- `GET /api/payments/wallet/` - Get wallet balance

## Admin

Access admin at http://localhost:8000/admin
