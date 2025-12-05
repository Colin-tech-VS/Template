# Dashboard Stripe Propagation — Integration Notes

This folder contains a small blueprint and UI snippet to let the dashboard push a Stripe publishable key (`pk_...`) to all template sites.

Files
- `stripe_propagate.py` — Flask blueprint. Register in your dashboard app: `app.register_blueprint(bp)`.
- `stripe_button_snippet.html` — HTML/JS snippet to add to an admin page.

How it works
1. Admin clicks the button and enters the publishable key.
2. The dashboard endpoint `/admin/stripe/propagate` is called with `{publishable_key: 'pk_test_...'}`.
3. The blueprint retrieves the list of sites (from `current_app.config['TEMPLATE_SITES_LIST']` or adapt to your DB/ORM), then starts a background thread that calls each site's `PUT /api/export/settings/stripe_publishable_key` with header `X-API-Key: TEMPLATE_MASTER_API_KEY`.

Integration steps
1. Copy `stripe_propagate.py` into your dashboard project (e.g. `dashboard/routes/stripe_propagate.py`).
2. Register the blueprint in the dashboard app factory:

```python
from dashboard.routes.stripe_propagate import bp as stripe_propagate_bp
app.register_blueprint(stripe_propagate_bp)
```

3. Configure the dashboard app:
- `app.config['TEMPLATE_MASTER_API_KEY'] = 'template-master-key-2025'` (or read from env/secret manager)
- Set `app.config['TEMPLATE_SITES_LIST'] = ['https://site1...', 'https://site2...']` OR adapt the blueprint to read your sites from DB/ORM.

4. Add the HTML snippet to an admin page (or create a small admin form) so admins can paste the `pk_test_...` and trigger propagation.

Security and best practices
- Protect `/admin/stripe/propagate` so only authorized admins can call it (Flask-Login check, RBAC, etc.).
- Always use HTTPS.
- Only push publishable keys (`pk_...`). Never push secret keys (`sk_...`) to template sites.
- Implement retry and logging for failures.
- Prefer a background job system (Celery/RQ) for large numbers of sites.

Testing
- Run the blueprint locally and try the button with a single site in `TEMPLATE_SITES_LIST` set to `https://template.artworksdigital.fr`.
- After propagation, verify each site with `GET /api/stripe-pk`.

If you want, I can adapt the blueprint to read sites from your actual DB (provide the model/ORM) and implement a persistent results table to review success/failures.
