import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException, Request
from telegram import Update
from .config import get_settings
from .db import Base, engine
from .bot import build_application

settings = get_settings()
logging.basicConfig(level=settings.log_level.upper())
log = logging.getLogger("marketplace.api")
telegram_app = build_application()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # For a small single web instance this creates missing tables.
    # Use Alembic migrations for schema changes in production.
    Base.metadata.create_all(bind=engine)
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.bot.set_webhook(
        url=settings.webhook_url,
        secret_token=settings.telegram_webhook_secret,
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=False,
    )
    log.info("Telegram webhook registered: %s", settings.webhook_url)
    yield
    await telegram_app.bot.delete_webhook(drop_pending_updates=False)
    await telegram_app.stop()
    await telegram_app.shutdown()


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.app_name}


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    payload = await request.json()
    update = Update.de_json(payload, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}
