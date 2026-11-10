from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from .models import User, Item, Reaction, AuditLog, Payment


def upsert_user(db: Session, tg_user) -> User:
    user = db.scalar(select(User).where(User.telegram_id == tg_user.id))
    if user:
        user.username = tg_user.username
        user.first_name = tg_user.first_name or "Telegram user"
    else:
        user = User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name or "Telegram user",
        )
        db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_item(db: Session, seller: User, data: dict) -> Item:
    item = Item(
        seller_id=seller.id, title=data["title"], description=data["description"],
        category=data["category"], condition=data["condition"],
        price=Decimal(data["price"]), currency="ETB", city=data["city"],
        photo_file_id=data.get("photo_file_id"), status="pending",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_active_items(db: Session, offset=0, limit=5):
    return list(db.scalars(
        select(Item).where(Item.status == "active").order_by(Item.created_at.desc(), Item.id.desc())
        .offset(offset).limit(limit)
    ))


def get_item(db: Session, item_id: int):
    return db.scalar(select(Item).where(Item.id == item_id))


def set_reaction(db: Session, user: User, item_id: int, reaction: str) -> bool:
    item = db.scalar(select(Item).where(Item.id == item_id, Item.status == "active"))
    if not item:
        return False
    existing = db.scalar(select(Reaction).where(
        Reaction.user_id == user.id, Reaction.item_id == item_id
    ))
    if existing:
        existing.reaction = reaction
    else:
        db.add(Reaction(user_id=user.id, item_id=item_id, reaction=reaction))
    db.commit()
    return True


def audit(db: Session, actor_id: int, action: str, object_type: str, object_id: str, details=""):
    db.add(AuditLog(actor_telegram_id=actor_id, action=action,
                    object_type=object_type, object_id=str(object_id), details=details[:2000]))
    db.commit()


def stats(db: Session):
    return {
        "users": db.scalar(select(func.count(User.id))) or 0,
        "pending": db.scalar(select(func.count(Item.id)).where(Item.status == "pending")) or 0,
        "active": db.scalar(select(func.count(Item.id)).where(Item.status == "active")) or 0,
        "payments": db.scalar(select(func.count(Payment.id))) or 0,
    }
