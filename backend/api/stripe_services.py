import stripe
import logging
from api.utils import get_db

logger = logging.getLogger(__name__)

# Assumes stripe.api_key is set in settings or initialization
# But we can import it here to be safe if controllers set it globally

def get_user_balance_data(user):
    """
    Returns user balance and recharge settings.
    """
    db = get_db()
    
    # Refresh user data
    u = db.user.find_unique(where={"id": user.id})
    if not u:
        return None
        
    return {
        "balance": u.balance,
        "autoRechargeEnabled": u.autoRechargeEnabled,
        "rechargeThreshold": u.rechargeThreshold,
        "rechargeAmount": u.rechargeAmount,
        "paymentMethodSet": bool(u.stripePaymentMethodId)
    }

def create_setup_intent(user):
    """
    Creates a SetupIntent to save a card for future use without charging immediately.
    """
    db = get_db()
    u = db.user.find_unique(where={"id": user.id})
    
    # Ensure customer exists
    customer_id = u.stripeCustomerId
    if not customer_id:
        customer = stripe.Customer.create(email=user.email, name=user.name)
        customer_id = customer.id
        db.user.update(where={"id": user.id}, data={"stripeCustomerId": customer_id})
    
    intent = stripe.SetupIntent.create(
        customer=customer_id,
        usage='off_session', # Important for auto-recharge
    )
    
    return intent.client_secret

def charge_customer(user, amount_currency, description="Manual Recharge"):
    """
    Charges the customer's saved default payment method.
    amount_currency: float (e.g. 50.00)
    """
    db = get_db()
    u = db.user.find_unique(where={"id": user.id})
    
    if not u.stripeCustomerId or not u.stripePaymentMethodId:
        raise Exception("No payment method saved.")

    amount_cents = int(amount_currency * 100)
    
    # Create Payment Intent off-session
    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency='brl',
            customer=u.stripeCustomerId,
            payment_method=u.stripePaymentMethodId,
            off_session=True,
            confirm=True,
            description=description,
            metadata={'userId': u.id, 'type': 'recharge'}
        )
        return payment_intent
    except stripe.error.CardError as e:
        # Error code will be authentication_required if authentication is needed
        err = e.error
        # Check if 3DS is required
        if err.code == 'authentication_required':
             # Bring user back on-session to authenticate
             # In a real app we would handle this flow, but complexities exist for auto-recharge
             # For now, we disable auto-recharge if this happens
             db.user.update(where={"id": u.id}, data={"autoRechargeEnabled": False})
             raise Exception("Authentication required. Auto-recharge disabled.")
        elif err.code:
             db.user.update(where={"id": u.id}, data={"autoRechargeEnabled": False})
             raise Exception(f"Card error: {err.code}")
        else:
             raise e

def check_and_trigger_auto_recharge(user_id):
    """
    Checks if balance < threshold and triggers recharge if enabled.
    Should be called after balance deduction.
    """
    db = get_db()
    u = db.user.find_unique(where={"id": user_id})
    
    logger.debug(f"Checking auto-recharge for user {user_id}")
    if not u:
        logger.debug("User not found")
        return
    if not u.autoRechargeEnabled:
        logger.debug("Auto-recharge disabled")
        return
    if not u.stripePaymentMethodId:
        logger.debug("No payment method")
        return
        
    if u.balance < u.rechargeThreshold:
        logger.info(f"Triggering auto-recharge for user {u.email}. Balance: {u.balance}, Threshold: {u.rechargeThreshold}")
        try:
             charge_customer(u, u.rechargeAmount, description="Auto Recharge Trigger")
             logger.info("Charge request sent.")
             # Balance update happens in Webhook to be safe
        except Exception as e:
             logger.error(f"Auto-recharge failed: {e}")
             # Optionally notify user
    else:
        logger.debug(f"Auto-recharge skipped. Balance: {u.balance}, Threshold: {u.rechargeThreshold}")
