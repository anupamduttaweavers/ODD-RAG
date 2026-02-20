"""Business-logic layer for admin user management and activity logging.

All database access is encapsulated here so the router never touches
SQLModel sessions directly (Dependency-Inversion principle).
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import Session, select

from app.admin.database import get_admin_session
from app.admin.exceptions import (
    AuthenticationError,
    UserAlreadyExistsError,
    UserInactiveError,
    UserNotFoundError,
)
from app.admin.models import AdminActivityLog, AdminUser
from app.admin.security import hash_password, verify_password
from app.core.config import settings

logger = logging.getLogger("app.admin")


# ── User CRUD ────────────────────────────────────────────────


def seed_superadmin() -> None:
    """Ensure the .env superadmin account exists in the database.

    Called once during application startup.  If the user already exists
    the password is re-hashed so a changed .env value takes effect on
    next restart.
    """
    session = get_admin_session()
    try:
        stmt = select(AdminUser).where(AdminUser.username == settings.ADMIN_SUPERUSER_USERNAME)
        existing = session.exec(stmt).first()
        if existing is None:
            user = AdminUser(
                username=settings.ADMIN_SUPERUSER_USERNAME,
                hashed_password=hash_password(settings.ADMIN_SUPERUSER_PASSWORD),
                role="superadmin",
                is_active=True,
                created_by="system",
            )
            session.add(user)
            session.commit()
            logger.info("[ADMIN] Superadmin '%s' seeded from .env", settings.ADMIN_SUPERUSER_USERNAME)
        else:
            existing.hashed_password = hash_password(settings.ADMIN_SUPERUSER_PASSWORD)
            existing.role = "superadmin"
            existing.is_active = True
            existing.updated_at = datetime.now(timezone.utc)
            session.add(existing)
            session.commit()
            logger.info("[ADMIN] Superadmin '%s' password synced from .env", settings.ADMIN_SUPERUSER_USERNAME)
    finally:
        session.close()


def authenticate_user(username: str, password: str) -> AdminUser:
    """Verify credentials and return the user row.

    Raises:
        AuthenticationError: bad credentials
        UserInactiveError: account deactivated
    """
    session = get_admin_session()
    try:
        stmt = select(AdminUser).where(AdminUser.username == username)
        user = session.exec(stmt).first()
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError()
        if not user.is_active:
            raise UserInactiveError()
        return user
    finally:
        session.close()


def get_user_by_username(username: str) -> Optional[AdminUser]:
    session = get_admin_session()
    try:
        return session.exec(select(AdminUser).where(AdminUser.username == username)).first()
    finally:
        session.close()


def get_user_by_id(user_id: int) -> AdminUser:
    session = get_admin_session()
    try:
        user = session.get(AdminUser, user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        return user
    finally:
        session.close()


def list_users() -> List[AdminUser]:
    session = get_admin_session()
    try:
        return list(session.exec(select(AdminUser).order_by(AdminUser.created_at)).all())
    finally:
        session.close()


def create_user(username: str, password: str, role: str, created_by: str) -> AdminUser:
    session = get_admin_session()
    try:
        if session.exec(select(AdminUser).where(AdminUser.username == username)).first():
            raise UserAlreadyExistsError(username)
        user = AdminUser(
            username=username,
            hashed_password=hash_password(password),
            role=role,
            created_by=created_by,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        logger.info("[ADMIN] User '%s' created by '%s'", username, created_by)
        return user
    finally:
        session.close()


def update_user(
    user_id: int,
    *,
    password: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> AdminUser:
    session = get_admin_session()
    try:
        user = session.get(AdminUser, user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        if password is not None:
            user.hashed_password = hash_password(password)
        if role is not None:
            user.role = role
        if is_active is not None:
            user.is_active = is_active
        user.updated_at = datetime.now(timezone.utc)
        session.add(user)
        session.commit()
        session.refresh(user)
        logger.info("[ADMIN] User id=%s updated", user_id)
        return user
    finally:
        session.close()


def delete_user(user_id: int) -> AdminUser:
    """Soft-delete by deactivating the account."""
    return update_user(user_id, is_active=False)


# ── Activity Logging ─────────────────────────────────────────


def log_activity(
    username: str,
    action: str,
    detail: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Persist an admin activity record."""
    session = get_admin_session()
    try:
        entry = AdminActivityLog(
            username=username,
            action=action,
            detail=json.dumps(detail) if detail else None,
            ip_address=ip_address,
        )
        session.add(entry)
        session.commit()
    except Exception:
        logger.exception("[ADMIN] Failed to write activity log")
    finally:
        session.close()


def get_activity_logs(
    page: int = 1,
    page_size: int = 50,
    username: Optional[str] = None,
    action: Optional[str] = None,
) -> tuple[List[AdminActivityLog], int]:
    """Return paginated, optionally filtered activity logs."""
    session = get_admin_session()
    try:
        stmt = select(AdminActivityLog).order_by(AdminActivityLog.timestamp.desc())
        count_stmt = select(AdminActivityLog)

        if username:
            stmt = stmt.where(AdminActivityLog.username == username)
            count_stmt = count_stmt.where(AdminActivityLog.username == username)
        if action:
            stmt = stmt.where(AdminActivityLog.action == action)
            count_stmt = count_stmt.where(AdminActivityLog.action == action)

        total = len(session.exec(count_stmt).all())
        offset = (page - 1) * page_size
        logs = list(session.exec(stmt.offset(offset).limit(page_size)).all())
        return logs, total
    finally:
        session.close()
