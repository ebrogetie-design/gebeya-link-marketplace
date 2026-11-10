# Gebeya Link — Enterprise Telegram Marketplace (ETB)

## Included
- Telegram webhook bot hosted as a Render Web Service
- PostgreSQL persistence via SQLAlchemy
- Seller item submission flow with optional photo
- Moderation queue: listings stay `pending` until admin approval
- Active listing feed, reactions, seller contact
- Admin dashboard and audit log
- Health endpoint and webhook secret validation
- Payment boundary that fails closed until a real Ethiopian payment provider is integrated

## 1. Create Telegram bot
1. Talk to `@BotFather`, create a bot and copy its token.
2. Get your numeric Telegram user ID and set it in `ADMIN_IDS`.
3. Do not put the token in source control or share it in chat.

## 2. Deploy to Render
1. Push this project to a **private Git repository**.
2. In Render, create a Blueprint from the repository (`render.yaml`).
3. Render provisions a Web Service and PostgreSQL database.
4. Set `BOT_TOKEN`, `ADMIN_IDS`, and `PUBLIC_BASE_URL` in the service environment.
   `PUBLIC_BASE_URL` must be the exact HTTPS service URL, e.g. `https://your-service.onrender.com`.
5. Deploy. Check `https://your-service.onrender.com/health`.
6. Open the Telegram bot and send `/start`.

The app registers Telegram's webhook during startup and validates
`X-Telegram-Bot-Api-Secret-Token` on every incoming webhook request.

### Render notes
- A paid always-on web service is recommended for a production bot.
- Keep one web instance unless you implement a distributed webhook/update lock.
- PostgreSQL is the source of truth. Persistent disk is only for local uploads; Telegram `file_id` is stored for photos in this starter.
- Back up PostgreSQL and test restore procedures.
- The included Blueprint plans are starting defaults; change them to fit expected traffic and current Render pricing/availability.

## 3. Run locally
Python 3.11+ recommended:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill .env with real values
uvicorn app.main:app --reload --port 8000
```
For local Telegram webhook testing, expose HTTPS with a tunnel and set `PUBLIC_BASE_URL` to that public URL.
Do not run polling and webhook mode for the same bot token at the same time.

## 4. Main user journey
- `/start` — home menu
- `/post` — guided listing submission (title, description, category, condition, ETB price, city, photo)
- `/cancel` — cancel listing
- Admin receives approve/reject buttons for new listings.
- Approved items appear in the public feed.

## 5. Payment integration is intentionally not enabled
`PAYMENT_PROVIDER=manual` is the safe default. No payment is accepted or marked paid.
Before enabling a payment provider:
1. Open a merchant account with a supported provider (for example Chapa or Telebirr, subject to current merchant eligibility and product availability).
2. Obtain official API credentials and current integration documentation directly from that provider.
3. Implement server-side payment initialization and signature/authenticity verification for callbacks.
4. Verify payment status server-to-server; never trust a browser redirect or user-supplied reference.
5. Add idempotency, reconciliation, refunds, chargeback/dispute workflows, and test-mode coverage.
6. Have a local legal/accounting review for tax, consumer protection, AML/KYC, and payment-provider obligations.

## 6. Production checklist
- [ ] Rotate token if it was ever exposed; store secrets only in Render environment variables.
- [ ] Set at least one trusted admin ID; keep admin accounts protected.
- [ ] Change the default service/database plans to production-appropriate sizes.
- [ ] Confirm database backups and perform a restore drill.
- [ ] Configure monitoring/alerts and inspect logs.
- [ ] Add rate limiting and abuse controls before public launch.
- [ ] Add seller verification and moderation policy.
- [ ] Add privacy policy, terms, retention/deletion workflow, and support contact.
- [ ] Complete payment provider integration and security review before taking money.
- [ ] Add automated tests, CI, and Alembic migration workflow before schema changes.

## Scope and limitations
This is a production-oriented foundation, not a claim of fully certified enterprise readiness.
It does not yet implement real payment collection, KYC, escrow, refund processing,
advanced image storage/CDN, full broker directory management, or customer dispute resolution.
