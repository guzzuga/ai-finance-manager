"""Transaction service — CRUD operations for transactions."""
import uuid
import secrets
import string
import logging
from datetime import date
from typing import Optional

import bcrypt
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)


def _generate_password(length: int = 8) -> str:
    """Generate a random alphanumeric password."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def _hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def _verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


class TransactionService:
    """Service layer for transaction operations."""

    @staticmethod
    def get_or_create_user(
        db: Session,
        platform: str = "web",
        platform_id: str = None,
        name: str = None,
    ) -> User:
        """Get existing user or create a new one."""
        if platform_id:
            user = db.query(User).filter(
                User.platform == platform,
                User.platform_id == platform_id,
            ).first()
            if user:
                return user

        user = User(
            id=str(uuid.uuid4()),
            platform=platform,
            platform_id=platform_id,
            name=name,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def reset_user_data(db: Session, user_id: str) -> int:
        """Delete all transactions for a user and clear Google Sheets. Returns count of deleted rows."""
        count = db.query(Transaction).filter(Transaction.user_id == user_id).delete()
        db.commit()
        
        # Also clear Google Sheets
        try:
            from app.services.google_sheets_service import clear_data
            clear_data()  # Clear both sheets
        except Exception as e:
            logger.error(f"Failed to clear Google Sheets: {e}")
        
        return count

    @staticmethod
    def add_user(db: Session, name: str, platform_id: str = None, platform: str = "telegram") -> tuple[User, str, str]:
        """Add a new user with auto-generated credentials.

        Returns (user, username, plain_password).
        """
        if not platform_id:
            platform_id = str(uuid.uuid4())

        # Generate username from name (lowercase, no spaces)
        base_username = name.lower().replace(" ", "")
        username = base_username
        counter = 1
        while db.query(User).filter(User.username == username).first():
            username = f"{base_username}{counter}"
            counter += 1

        # Generate random password
        plain_password = _generate_password(8)
        password_hash = _hash_password(plain_password)

        user = User(
            id=str(uuid.uuid4()),
            platform=platform,
            platform_id=platform_id,
            name=name,
            username=username,
            password_hash=password_hash,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user, username, plain_password

    @staticmethod
    def login_user(db: Session, username: str, password: str) -> Optional[User]:
        """Authenticate user by username and password. Returns User or None."""
        user = db.query(User).filter(User.username == username).first()
        if not user or not user.password_hash:
            return None
        if _verify_password(password, user.password_hash):
            return user
        return None

    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def create_transaction(
        db: Session,
        user_id: str,
        parsed: dict,
        raw_message: str = None,
        source: str = "web",
    ) -> Transaction:
        """Create a transaction from parsed data."""
        category_name = parsed.get("category", "lainnya")
        transaction_type = parsed.get("type", "pengeluaran")

        # Find or create category
        category = db.query(Category).filter(
            Category.name == category_name,
            (Category.user_id == user_id) | (Category.user_id.is_(None)),
        ).first()

        if not category:
            category = Category(
                id=str(uuid.uuid4()),
                name=category_name,
                type=transaction_type,
                user_id=None,
            )
            db.add(category)
            db.commit()
            db.refresh(category)

        # Extract quantity, unit, and calculate price_per_unit
        quantity = parsed.get("quantity")
        unit = parsed.get("unit")
        amount = parsed.get("amount", 0)
        price_per_unit = None
        if quantity and quantity > 0 and amount > 0:
            price_per_unit = int(amount / quantity)

        transaction = Transaction(
            id=str(uuid.uuid4()),
            user_id=user_id,
            date=str(parsed.get("date", date.today())),
            type=transaction_type,
            category_id=category.id,
            amount=amount,
            note=parsed.get("note", ""),
            source=source,
            raw_message=raw_message,
            quantity=quantity,
            unit=unit,
            price_per_unit=price_per_unit,
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        return transaction

    @staticmethod
    def get_transactions(
        db: Session,
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        type_filter: Optional[str] = None,
        category_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list:
        """Get transactions with filters."""
        query = db.query(Transaction).filter(Transaction.user_id == user_id)

        if start_date:
            query = query.filter(Transaction.date >= str(start_date))
        if end_date:
            query = query.filter(Transaction.date <= str(end_date))
        if type_filter:
            query = query.filter(Transaction.type == type_filter)
        if category_id:
            query = query.filter(Transaction.category_id == category_id)

        return query.order_by(Transaction.date.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def get_transaction(db: Session, transaction_id: str) -> Optional[Transaction]:
        """Get a single transaction by ID."""
        return db.query(Transaction).filter(Transaction.id == transaction_id).first()

    @staticmethod
    def update_transaction(db: Session, transaction_id: str, data: dict) -> Optional[Transaction]:
        """Update a transaction."""
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            return None

        for key, value in data.items():
            if hasattr(transaction, key):
                setattr(transaction, key, value)

        db.commit()
        db.refresh(transaction)
        return transaction

    @staticmethod
    def delete_transaction(db: Session, transaction_id: str) -> bool:
        """Delete a transaction."""
        transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            return False
        db.delete(transaction)
        db.commit()
        return True
