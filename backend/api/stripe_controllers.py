import json
import stripe
import os
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .decorators import login_required
from .utils import get_db
from .stripe_services import get_user_balance_data, create_setup_intent, charge_customer

# Try to get from settings, else env, else empty
STRIPE_SECRET_KEY = getattr(settings, 'STRIPE_SECRET_KEY', os.environ.get('STRIPE_SECRET_KEY', ''))
STRIPE_WEBHOOK_SECRET = getattr(settings, 'STRIPE_WEBHOOK_SECRET', os.environ.get('STRIPE_WEBHOOK_SECRET', ''))

stripe.api_key = STRIPE_SECRET_KEY

@csrf_exempt
@login_required
def get_balance(request):
    """Returns user balance and settings"""
    if request.method != "GET":
         return JsonResponse({"error": "Method not allowed"}, status=405)
    
    data = get_user_balance_data(request.user)
    if not data:
         return JsonResponse({"error": "User not found"}, status=404)
    
    # Fetch recent transactions
    transactions = get_db().transaction.find_many(
        where={"userId": request.user.id},
        take=10,
        order={"createdAt": "desc"}
    )
    
    # Serialize transactions
    tx_list = []
    for tx in transactions:
        tx_list.append({
            "id": tx.id,
            "type": tx.type,
            "amount": tx.amount,
            "description": tx.description,
            "date": tx.createdAt.isoformat()
        })
        
    data["transactions"] = tx_list
         
    return JsonResponse(data)

@csrf_exempt
@login_required
def create_setup_checkout_session(request):
    """
    Creates a Stripe Checkout Session for saving a card (Setup Mode).
    """
    if request.method != "POST":
         return JsonResponse({"error": "Method not allowed"}, status=405)
         
    try:
        # Ensure customer exists (reuse existing logic from services)
        from .stripe_services import create_setup_intent 
        # Hack: create_setup_intent ensures customer exists on the user object
        create_setup_intent(request.user)
        
        # Refresh user to get customer ID
        u = get_db().user.find_unique(where={"id": request.user.id})
        
        # Create a Checkout Session in setup mode
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='setup',
            customer=u.stripeCustomerId, 
            success_url='http://localhost:5173/dashboard/billing?setup_success=true',
            cancel_url='http://localhost:5173/dashboard/billing?canceled=true',
            metadata={
                'userId': request.user.id
            }
        )
        return JsonResponse({"url": checkout_session.url})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
@login_required
def update_settings(request):
    """Updates auto-recharge settings"""
    if request.method != "POST":
         return JsonResponse({"error": "Method not allowed"}, status=405)
         
    try:
        body = json.loads(request.body)
        db = get_db()
        db.user.update(
            where={"id": request.user.id},
            data={
                "autoRechargeEnabled": body.get("enabled", False),
                "rechargeThreshold": float(body.get("threshold", 10.0)),
                "rechargeAmount": float(body.get("amount", 50.0))
            }
        )
        return JsonResponse({"status": "updated"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
@login_required
def create_recharge_checkout_session(request):
    """
    Creates a Stripe Checkout Session for manual recharge (Payment Mode).
    """
    if request.method != "POST":
         return JsonResponse({"error": "Method not allowed"}, status=405)
         
    try:
        body = json.loads(request.body)
        amount = float(body.get("amount", 0))
        if amount <= 0:
             return JsonResponse({"error": "Invalid amount"}, status=400)
        
        # Create product on the fly or use a generic one? 
        # Better to use price_data for dynamic amounts.
        amount_cents = int(amount * 100)
        
        # Ensure customer exists
        from .stripe_services import create_setup_intent
        create_setup_intent(request.user)
        u = get_db().user.find_unique(where={"id": request.user.id})
        
        checkout_session = stripe.checkout.Session.create(
            customer=u.stripeCustomerId,
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'brl',
                    'product_data': {
                        'name': 'Recarga de Créditos',
                    },
                    'unit_amount': amount_cents,
                },
                'quantity': 1,
            }],
            mode='payment',
            payment_intent_data={
                # IMPORTANT: Setup for future off-session usage (Auto-Recharge)
                'setup_future_usage': 'off_session', 
                'metadata': {'userId': request.user.id, 'type': 'recharge'} 
            },
            success_url='http://localhost:5173/dashboard/billing?recharge_success=true',
            cancel_url='http://localhost:5173/dashboard/billing?canceled=true',
            metadata={
                'userId': request.user.id
            }
        )
        return JsonResponse({"url": checkout_session.url})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# Keep old checkout session for backward compat if needed, or remove.
# Removing for clarity as we are migrating to Balance.

@csrf_exempt
def webhook(request):
    """
    Handles Stripe Webhooks.
    """
    payload = request.body
    sig_header = request.headers.get('Stripe-Signature')
    
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        print("WEBHOOK ERROR: Invalid payload")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(f"WEBHOOK ERROR: Signature failed. Secret: {STRIPE_WEBHOOK_SECRET[:5]}...")
        return HttpResponse(status=400)
    except Exception as e:
        print(f"WEBHOOK ERROR: {str(e)}")
        return HttpResponse(status=400)

    # Handle the event
    db = get_db()
    
    if event['type'] == 'setup_intent.succeeded':
        # Payment method attached
        setup_intent = event['data']['object']
        customer_id = setup_intent.get('customer')
        payment_method_id = setup_intent.get('payment_method')
        
        # Find user by customer_id
        # In a real app we might query using raw SQL or by iterating if schema doesn't support unique search on customerId
        # Ideally we stored userId in metadata
        # setup_intent usually doesn't allow metadata on creation easily in all flows, but let's assume we can map back via Customer ID
        # For simplicity MVP: Update valid user
        user = db.user.find_first(where={"stripeCustomerId": customer_id})
        if user and payment_method_id:
             db.user.update(where={"id": user.id}, data={"stripePaymentMethodId": payment_method_id})

    elif event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        
        metadata = getattr(payment_intent, 'metadata', {})
        user_id = metadata.get('userId') if isinstance(metadata, dict) else getattr(metadata, 'userId', None)
        if not user_id and hasattr(payment_intent, 'get'):
            user_id = payment_intent.get('metadata', {}).get('userId')

        amount_received = getattr(payment_intent, 'amount_received', 0) # in cents
        
        if user_id:
            # Credit balance
            amount_currency = amount_received / 100.0
            
            # Atomic increment
            db.user.update(
                where={"id": user_id},
                data={
                    "balance": {"increment": amount_currency}
                }
            )
            
            # Record Transaction
            db.transaction.create(data={
                "userId": user_id,
                "type": "CREDIT",
                "amount": amount_currency,
                "description": "Recarga de Créditos (Stripe)"
            })
            
            print(f"Credited ${amount_currency} to user {user_id}")
            
            try:
                user_record = db.user.find_unique(where={"id": user_id})
                if user_record:
                    from .emails import send_recharge_receipt
                    import datetime
                    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    send_recharge_receipt(user_record.email, user_record.name, amount_currency, "Cartão de Crédito (Stripe)", date_str)
            except Exception as e:
                print(f"Error sending recharge receipt: {e}")
                 
    return HttpResponse(status=200)
    """
    Creates a Stripe Checkout Session for a subscription.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        if not STRIPE_SECRET_KEY:
            return JsonResponse({"error": "Stripe is not configured (Missing Secret Key)"}, status=500)

        body = json.loads(request.body)
        price_id = body.get("priceId") # e.g. price_H5ggYJ...
        
        if not price_id:
            return JsonResponse({"error": "Price ID is required"}, status=400)

        checkout_session = stripe.checkout.Session.create(
            customer_email=request.user.email,
            line_items=[
                {
                    'price': price_id,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url='http://localhost:5173/dashboard/billing?success=true',
            cancel_url='http://localhost:5173/dashboard/billing?canceled=true',
            metadata={
                'userId': request.user.id
            }
        )

        return JsonResponse({"url": checkout_session.url})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
@login_required
def create_portal_session(request):
    """
    Creates a Customer Portal session for managing subscriptions.
    """
    if request.method != "POST":
         return JsonResponse({"error": "Method not allowed"}, status=405)
         
    try:
        db = get_db()
        subscription = db.subscription.find_unique(where={"userId": request.user.id})
        
        if not subscription or not subscription.stripeCustomerId:
            return JsonResponse({"error": "No active subscription found"}, status=404)
            
        portal_session = stripe.billing_portal.Session.create(
            customer=subscription.stripeCustomerId,
            return_url='http://localhost:5173/dashboard/billing',
        )
        
        return JsonResponse({"url": portal_session.url})
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)




