"""
Spendora — SQLAlchemy ORM models.

Design principles:
- Money is stored as INTEGER paise (minor units) — never as FLOAT.
- transaction_date is a DATE (no time) for clean calendar arithmetic.
- created_at / updated_at use UTC datetime for auditing only.
- All foreign keys are enforced at the SQLAlchemy level.
- Category source tracks whether each category was system-seeded, AI-suggested,
  or user-created — AI suggestions must never silently overwrite user data.
"""

from __future__ import annotations

import enum
from datetime import date, datetime, timezone
from typing import List, Optional


def utcnow() -> datetime:
    """Return timezone-naive UTC datetime for SQLite compatibility without deprecation warnings."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """Shared declarative base for all Spendora ORM models."""
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TransactionType(str, enum.Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class CategorySource(str, enum.Enum):
    SYSTEM = "SYSTEM"       # Seeded by the application for the profession.
    AI = "AI"               # Suggested by AI, accepted by user.
    USER = "USER"           # Created entirely by the user.


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(Base):
    """
    Represents a single user profile.

    The application is designed for a single primary user per device (Phase 1).
    The schema supports multiple users for future cloud-sync features.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    profession: Mapped[str] = mapped_column(String(100), nullable=False)
    # If profession == "Other", the user's custom profession text is stored here.
    profession_custom: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Monetary values stored as integer paise to avoid float errors.
    # NULL means the user did not provide this information.
    monthly_income_paise: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fixed_expenses_paise: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    is_onboarding_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    # Relationships
    categories: Mapped[List["Category"]] = relationship(
        "Category", back_populates="user", cascade="all, delete-orphan"
    )
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
    preferences: Mapped[List["UserPreference"]] = relationship(
        "UserPreference", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} name={self.name!r} profession={self.profession!r}>"


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

class Category(Base):
    """
    An expense/income category owned by a user.

    Categories can be system-seeded (based on profession), AI-suggested, or
    user-created. The source field preserves this distinction so that the AI
    layer can never silently overwrite user-created categories.
    """
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)   # Hex colour, e.g. "#FF6B6B"
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)   # MDI icon name
    source: Mapped[CategorySource] = mapped_column(
        Enum(CategorySource), nullable=False, default=CategorySource.USER
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="categories")
    subcategories: Mapped[List["Subcategory"]] = relationship(
        "Subcategory", back_populates="category", cascade="all, delete-orphan"
    )
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="category"
    )

    __table_args__ = (
        Index("ix_categories_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name!r} user_id={self.user_id}>"


# ---------------------------------------------------------------------------
# Subcategory
# ---------------------------------------------------------------------------

class Subcategory(Base):
    """A subcategory belonging to a Category (optional hierarchy)."""
    __tablename__ = "subcategories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[CategorySource] = mapped_column(
        Enum(CategorySource), nullable=False, default=CategorySource.USER
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    # Relationships
    category: Mapped["Category"] = relationship("Category", back_populates="subcategories")
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="subcategory"
    )

    __table_args__ = (
        Index("ix_subcategories_category_id", "category_id"),
    )

    def __repr__(self) -> str:
        return f"<Subcategory id={self.id} name={self.name!r} category_id={self.category_id}>"


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

class Transaction(Base):
    """
    A single financial transaction (income or expense).

    amount_paise is stored as a POSITIVE integer regardless of transaction_type.
    The sign is determined by transaction_type at calculation time.
    This prevents sign confusion bugs.
    """
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    subcategory_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("subcategories.id", ondelete="SET NULL"), nullable=True
    )

    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)  # Always positive.
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType), nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="transactions")
    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="transactions")
    subcategory: Mapped[Optional["Subcategory"]] = relationship(
        "Subcategory", back_populates="transactions"
    )

    __table_args__ = (
        Index("ix_transactions_user_id", "user_id"),
        Index("ix_transactions_date", "transaction_date"),
        Index("ix_transactions_user_date", "user_id", "transaction_date"),
        Index("ix_transactions_category", "category_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} type={self.transaction_type.value} "
            f"amount_paise={self.amount_paise} date={self.transaction_date}>"
        )


# ---------------------------------------------------------------------------
# UserPreference
# ---------------------------------------------------------------------------

class UserPreference(Base):
    """
    Key-value store for user-specific preferences.
    Allows adding new settings without schema migrations.
    """
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="preferences")

    __table_args__ = (
        Index("ix_preferences_user_key", "user_id", "key", unique=True),
    )

    def __repr__(self) -> str:
        return f"<UserPreference user_id={self.user_id} key={self.key!r}>"

