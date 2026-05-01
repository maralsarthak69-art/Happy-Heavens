# WhatsApp Notifications Setup Guide

This guide will help you set up WhatsApp notifications for new orders using Twilio's WhatsApp API.

## 🚀 Quick Start

### 1. Create a Twilio Account

1. Go to [Twilio Console](https://console.twilio.com/)
2. Sign up for a free account (you get free credits to test)
3. Verify your phone number

### 2. Set Up WhatsApp Sandbox (For Testing)

Twilio provides a WhatsApp Sandbox for testing without needing approval:

1. In Twilio Console, go to **Messaging** → **Try it out** → **Send a WhatsApp message**
2. You'll see a sandbox number (e.g., `+1 415 523 8886`)
3. Follow the instructions to join the sandbox:
   - Send a WhatsApp message to the sandbox number
   - Use the code shown (e.g., "join <your-code>")
4. Once joined, you can receive messages from this sandbox number

### 3. Get Your Twilio Credentials

From the Twilio Console dashboard:

1. **Account SID**: Found on the main dashboard
2. **Auth Token**: Click "Show" next to Auth Token on dashboard
3. **WhatsApp From Number**: The sandbox number (format: `whatsapp:+14155238886`)

### 4. Configure Environment Variables

Update your `.env` file with the following:

```env
# WhatsApp Notifications via Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
ADMIN_WHATSAPP_NUMBER=whatsapp:+919876543210
```

**Important Notes:**
- Replace `+919876543210` with your actual WhatsApp number (with country code)
- Keep the `whatsapp:` prefix for both numbers
- Your admin number must have joined the Twilio sandbox (see step 2)

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install the `twilio` package.

### 6. Test the Integration

Run the test command to verify everything works:

```bash
python manage.py test_whatsapp
```

You should receive a test message on WhatsApp!

## 📱 How It Works

When a customer places an order:

1. Order is created in the database
2. Stock is decremented
3. WhatsApp notification is sent to admin with:
   - Order number and customer details
   - Items ordered with quantities
   - Total amount and payment method
   - Delivery address
   - Payment screenshot status

**Example notification:**
```
🔔 NEW ORDER RECEIVED!

📦 Order #1042
👤 Customer: Hiral Lole
📱 Phone: +919876543210

🛍️ Items:
  • Red Rose Bouquet x2 - ₹500
  • Chocolate Box x1 - ₹300

💰 Total: ₹1300
💳 Payment: QR Code Transfer

📍 Delivery Address:
123 Main Street
Mumbai, 400001

⏰ Ordered at: 12 Apr 2026, 03:45 PM

📸 Payment screenshot uploaded!

🔗 Check admin panel to verify and confirm the order.
```

## 🔧 Production Setup

For production, you need to:

1. **Apply for WhatsApp Business API Access**
   - Go to Twilio Console → Messaging → WhatsApp
   - Click "Request Access" for production WhatsApp
   - Submit your business details for approval
   - This can take a few days

2. **Get Your Own WhatsApp Number**
   - Once approved, you can use your own business number
   - Update `TWILIO_WHATSAPP_FROM` with your approved number

3. **Set Environment Variables on Render**
   - Go to your Render dashboard
   - Navigate to your service → Environment
   - Add all four WhatsApp variables
   - Redeploy your service

## 🐛 Troubleshooting

### "WhatsApp service not configured"
- Check that all four environment variables are set
- Restart your Django server after updating `.env`

### "Failed to send WhatsApp notification"
- Verify your admin number has joined the Twilio sandbox
- Check that numbers include country code and `whatsapp:` prefix
- Verify your Twilio credentials are correct

### "Twilio authentication failed"
- Double-check your Account SID and Auth Token
- Make sure there are no extra spaces in `.env` file

### Order created but no WhatsApp message
- Check Django logs for error messages
- Notification failures don't block order creation (by design)
- Verify your Twilio account has credits remaining

## 💡 Alternative: WhatsApp Cloud API (Free)

If you prefer Meta's official API instead of Twilio:

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create a WhatsApp Business App
3. Get your access token and phone number ID
4. Modify `whatsapp_service.py` to use Meta's API instead

The Meta Cloud API is free for up to 1,000 conversations per month.

## 📊 Monitoring

Check your Twilio Console to monitor:
- Message delivery status
- Failed messages
- Usage and costs
- Message logs

## 🔐 Security Notes

- Never commit `.env` file to version control
- Keep your Auth Token secret
- Rotate credentials if compromised
- Use environment variables on production servers

## 📞 Support

- Twilio Docs: https://www.twilio.com/docs/whatsapp
- Twilio Support: https://support.twilio.com/
- Django Logs: Check console output for error messages

