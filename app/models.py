from datetime import datetime
from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Integer,
    Numeric, String, Text, UniqueConstraint, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str] = mapped_column(String(128), default="Telegram user")
    phone: Mapped[str | None] = mapped_column(String(32))
    role: Mapped[str] = mapped_column(String(16), default="buyer")
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    items = relationship("Item", back_populates="seller")


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("condition IN ('new','used')", name="ck_item_condition"),
        CheckConstraint("status IN ('pending','active','rejected','sold','removed')", name="ck_item_status"),
        CheckConstraint("price > 0", name="ck_item_price_positive"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(64), default="Other")
    condition: Mapped[str] = mapped_column(String(8))
    price: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="ETB")
    city: Mapped[str] = mapped_column(String(80), default="Ethiopia")
    status: Mapped[str] = mapped_column(String(12), default="pending", index=True)
    photo_file_id: Mapped[str | None] = mapped_column(String(256))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    seller = relationship("User", back_populates="items")


class Reaction(Base):
    __tablename__ = "reactions"
    __table_args__ = (UniqueConstraint("user_id", "item_id", name="uq_reaction_user_item"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"))
    reaction: Mapped[str] = mapped_column(String(8))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("status IN ('initiated','pending','paid','failed','refunded')", name="ck_payment_status"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(24), default="manual")
    provider_reference: Mapped[str | None] = mapped_column(String(128), unique=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="ETB")
    status: Mapped[str] = mapped_column(String(12), default="initiated", index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    action: Mapped[str] = mapped_column(String(64))
    object_type: Mapped[str] = mapped_column(String(32))
    object_id: Mapped[str] = mapped_column(String(64))
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
