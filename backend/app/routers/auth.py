"""Auth routes — login/logout/session for multi-tenant dashboard."""
import logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.transaction_service import TransactionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Login with username/password. Returns user info."""
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Username dan password wajib diisi")
    
    user = TransactionService.login_user(db, req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Username atau password salah")
    
    return {
        "success": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "name": user.name,
        }
    }
