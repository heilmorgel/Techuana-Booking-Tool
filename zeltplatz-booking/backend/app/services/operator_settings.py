from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import OperatorSettings
from app.schemas import InvoiceOperator

ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
CONTENT_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def get_or_create_operator_settings(db: Session) -> OperatorSettings:
    row = db.get(OperatorSettings, 1)
    if row is None:
        row = OperatorSettings(
            id=1,
            organization_name="",
            address="",
            iban="",
            logo_filename=None,
            home_country="AT",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    if not (row.home_country or "").strip():
        row.home_country = "AT"
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def operator_to_invoice(row: OperatorSettings) -> InvoiceOperator:
    return InvoiceOperator(
        organization_name=row.organization_name or "",
        address=row.address or "",
        iban=row.iban or "",
        has_logo=bool(row.logo_filename and logo_path(row).is_file()),
    )


def data_dir() -> Path:
    path = Path(get_settings().data_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def logo_path(row: OperatorSettings) -> Path:
    if not row.logo_filename:
        return data_dir() / "__missing_logo__"
    return data_dir() / row.logo_filename


def clear_logo_file(row: OperatorSettings) -> None:
    if not row.logo_filename:
        return
    path = logo_path(row)
    if path.is_file():
        path.unlink()
