# FundiGO Payment System Documentation

## Overview

FundiGO uses an **escrow-based payment system** where:
1. Client pays the full amount to the platform
2. Platform holds the money until job completion
3. After client approval, platform releases 85% to technician (keeps 15% commission)

## Payment Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   CLIENT    │     │  PLATFORM   │     │ TECHNICIAN  │
└─────────────┘     └─────────────┘     └─────────────┘
      │                    │                    │
      │  1. Pay via M-Pesa │                    │
      │ ──────────────────>│                    │
      │                    │                    │
      │  2. STK Push       │                    │
      │ <──────────────────│                    │
      │                    │                    │
      │  3. Enter PIN      │                    │
      │ ──────────────────>│                    │
      │                    │                    │
      │  4. Payment HELD   │                    │
      │    in escrow       │                    │
      │                    │                    │
      │                    │  5. Job Started    │
      │                    │ <─────────────────>│
      │                    │                    │
      │                    │  6. Job Completed  │
      │                    │ <──────────────────│
      │                    │                    │
      │  7. Approve Work   │                    │
      │ ──────────────────>│                    │
      │                    │                    │
      │                    │  8. Release 85%    │
      │                    │ ──────────────────>│
      │                    │                    │
      │                    │  9. Keep 15%       │
      │                    │    commission      │
      └────────────────────┴────────────────────┘
```

## API Endpoints

### Client Payment Flow

#### 1. Initiate Payment
```http
POST /api/payments/job/initiate/
Authorization: Bearer <token>

{
    "job_id": 123,
    "phone_number": "0712345678"  // Optional
}
```

Response:
```json
{
    "success": true,
    "message": "STK Push sent to your phone...",
    "payment_ref": "FG-ABC12345",
    "checkout_request_id": "ws_CO_...",
    "amount": "3000.00",
    "platform_fee": "450.00",
    "technician_amount": "2550.00"
}
```

#### 2. Check Payment Status
```http
POST /api/payments/job/status/
Authorization: Bearer <token>

{
    "payment_ref": "FG-ABC12345"
}
```

#### 3. Release Payment (After Job Completion)
```http
POST /api/payments/job/release/
Authorization: Bearer <token>

{
    "job_id": 123
}
```

### Technician Payout Flow

#### 1. Request Payout
```http
POST /api/payments/payout/request/
Authorization: Bearer <token>

{
    "amount": 2550,
    "phone_number": "0712345678",
    "payout_method": "mpesa"  // or "bank"
}
```

#### 2. Get Payout History
```http
GET /api/payments/payout/history/
Authorization: Bearer <token>
```

### Wallet Endpoints

#### Get Balance
```http
GET /api/payments/wallet/balance/
Authorization: Bearer <token>
```

#### Get Transactions
```http
GET /api/payments/wallet/transactions/
Authorization: Bearer <token>
```

## M-Pesa Callbacks

### STK Push Callback (C2B)
```http
POST /api/payments/mpesa/callback/
```

### B2C Result Callback
```http
POST /api/payments/mpesa/b2c/result/
```

### B2C Timeout Callback
```http
POST /api/payments/mpesa/b2c/timeout/
```

## Database Models

### JobPayment
Tracks payments for jobs with escrow status.

| Field | Description |
|-------|-------------|
| payment_ref | Unique reference (FG-XXXXXXXX) |
| job | Link to JobPosting |
| client | User who paid |
| technician | User who receives payment |
| amount_paid | Full amount from client |
| platform_fee | 15% commission |
| technician_amount | 85% to technician |
| status | pending/processing/paid/held/released/refunded/failed |

### Payout
Tracks payouts to technicians.

| Field | Description |
|-------|-------------|
| payout_ref | Unique reference (PO-XXXXXXXX) |
| technician | User receiving payout |
| amount | Payout amount |
| payout_method | mpesa/bank |
| status | pending/processing/completed/failed |

### Wallet
User wallet for storing earnings.

| Field | Description |
|-------|-------------|
| user | Wallet owner |
| balance | Available balance |
| held_balance | Funds in escrow |

## Environment Variables

```env
# M-Pesa STK Push (C2B)
MPESA_ENVIRONMENT=sandbox  # or production
MPESA_CONSUMER_KEY=your_consumer_key
MPESA_CONSUMER_SECRET=your_consumer_secret
MPESA_SHORTCODE=174379  # Your Paybill/Till number
MPESA_PASSKEY=your_passkey
MPESA_CALLBACK_URL=https://yourdomain.com/api/payments/mpesa/callback/

# M-Pesa B2C (Payouts)
MPESA_B2C_SHORTCODE=600000
MPESA_B2C_INITIATOR_NAME=testapi
MPESA_B2C_SECURITY_CREDENTIAL=your_security_credential
MPESA_B2C_RESULT_URL=https://yourdomain.com/api/payments/mpesa/b2c/result/
MPESA_B2C_TIMEOUT_URL=https://yourdomain.com/api/payments/mpesa/b2c/timeout/

# Platform Settings
PLATFORM_COMMISSION_RATE=0.15  # 15%
```

## Production Setup

### 1. Register with Safaricom Daraja
1. Go to https://developer.safaricom.co.ke/
2. Create an account and app
3. Get production credentials
4. Register your callback URLs

### 2. Callback URL Requirements
- Must be HTTPS
- Must be publicly accessible
- Must respond within 30 seconds
- Use ngrok for testing: `ngrok http 8000`

### 3. Security Considerations
- Never expose credentials in frontend
- Validate all callback signatures
- Use HTTPS in production
- Implement rate limiting
- Log all transactions

## Testing

### Sandbox Test Numbers
- Phone: 254708374149
- Amount: Any amount (won't actually charge)

### Test Script
```bash
python test_mpesa.py
```

## Troubleshooting

### "Invalid Access Token"
- Clear cache and retry
- Check consumer key/secret match shortcode
- Verify app has STK Push enabled

### "Bad Request - Invalid BusinessShortCode"
- Verify shortcode is correct
- Check passkey matches shortcode

### Callback Not Received
- Ensure URL is publicly accessible
- Check firewall settings
- Verify URL is registered with Safaricom

## Admin Actions

### Release Payments Manually
1. Go to Django Admin
2. Navigate to Payments > Job Payments
3. Select payments with status "held"
4. Use "Release selected payments" action

### View Platform Earnings
1. Go to Django Admin
2. Navigate to Payments > Platform Earnings
3. View commission from each job
