// static/js/stripe-init.js
// Init Stripe from server-provided publishable key

async function initStripeFromServer() {
  try {
    const res = await fetch('/api/stripe-pk');
    if (!res.ok) {
      console.warn('Stripe publishable key not found on server');
      return null;
    }
    const json = await res.json();
    if (json.success && json.publishable_key) {
      window.STRIPE_PK = json.publishable_key;
      if (window.Stripe) {
        window.STRIPE = Stripe(window.STRIPE_PK);
      } else {
        console.warn('Stripe.js not loaded');
      }
      return window.STRIPE;
    } else {
      console.warn('No publishable key in response:', json);
      return null;
    }
  } catch (e) {
    console.error('initStripeFromServer error', e);
    return null;
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  await initStripeFromServer();
});
