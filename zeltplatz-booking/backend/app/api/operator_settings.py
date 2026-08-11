from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import OperatorSettingsRead, OperatorSettingsUpdate
from app.services import operator_settings as op_svc

router = APIRouter(prefix="/operator-settings", tags=["operator-settings"])

_MAX_LOGO_BYTES = 2 * 1024 * 1024


def _to_read(row) -> OperatorSettingsRead:
    return OperatorSettingsRead(
        organization_name=row.organization_name or "",
        address=row.address or "",
        iban=row.iban or "",
        has_logo=bool(row.logo_filename and op_svc.logo_path(row).is_file()),
    )


@router.get("", response_model=OperatorSettingsRead)
def get_settings(db: Session = Depends(get_db)) -> OperatorSettingsRead:
    return _to_read(op_svc.get_or_create_operator_settings(db))


@router.patch("", response_model=OperatorSettingsRead)
def update_settings(
    payload: OperatorSettingsUpdate,
    db: Session = Depends(get_db),
) -> OperatorSettingsRead:
    row = op_svc.get_or_create_operator_settings(db)
    data = payload.model_dump(exclude_unset=True)
    if "organization_name" in data and data["organization_name"] is not None:
        row.organization_name = data["organization_name"].strip()
    if "address" in data and data["address"] is not None:
        row.address = data["address"].strip()
    if "iban" in data and data["iban"] is not None:
        row.iban = data["iban"].strip().replace(" ", "").upper()
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_read(row)


@router.get("/logo")
def get_logo(db: Session = Depends(get_db)) -> FileResponse:
    row = op_svc.get_or_create_operator_settings(db)
    path = op_svc.logo_path(row)
    if not row.logo_filename or not path.is_file():
        raise HTTPException(status_code=404, detail="Kein Logo hinterlegt")
    ext = Path(row.logo_filename).suffix.lower()
    media = op_svc.CONTENT_TYPES.get(ext, "application/octet-stream")
    return FileResponse(path, media_type=media, filename=row.logo_filename)


@router.post("/logo", response_model=OperatorSettingsRead)
async def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> OperatorSettingsRead:
    # #region agent log
    try:
        import json, time
        from pathlib import Path as _P
        _log = _P(__file__).resolve().parents[4] / ".cursor" / "debug-188c80.log"
        _log.parent.mkdir(parents=True, exist_ok=True)
        with _log.open("a", encoding="utf-8") as _f:
            _f.write(json.dumps({"sessionId":"188c80","runId":"pre-fix","hypothesisId":"C","location":"operator_settings.py:upload_logo","message":"upload_logo entered","data":{"filename":file.filename,"content_type":file.content_type},"timestamp":int(time.time()*1000)})+"\n")
    except Exception:
        pass
    # #endregion
    filename = file.filename or "logo.png"
    ext = Path(filename).suffix.lower()
    if ext not in op_svc.ALLOWED_LOGO_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Ungültiges Logo-Format. Erlaubt: {', '.join(sorted(op_svc.ALLOWED_LOGO_EXTENSIONS))}",
        )
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Leere Datei")
    if len(content) > _MAX_LOGO_BYTES:
        raise HTTPException(status_code=422, detail="Logo darf maximal 2 MB groß sein")

    row = op_svc.get_or_create_operator_settings(db)
    op_svc.clear_logo_file(row)
    stored_name = f"operator_logo{ext}"
    dest = op_svc.data_dir() / stored_name
    dest.write_bytes(content)
    row.logo_filename = stored_name
    db.add(row)
    db.commit()
    db.refresh(row)
    # #region agent log
    try:
        import json, time
        from pathlib import Path as _P
        _log = _P(__file__).resolve().parents[4] / ".cursor" / "debug-188c80.log"
        with _log.open("a", encoding="utf-8") as _f:
            _f.write(json.dumps({"sessionId":"188c80","runId":"pre-fix","hypothesisId":"C","location":"operator_settings.py:upload_logo:ok","message":"upload_logo saved","data":{"stored_name":stored_name,"bytes":len(content),"dest_exists":dest.is_file()},"timestamp":int(time.time()*1000)})+"\n")
    except Exception:
        pass
    # #endregion
    return _to_read(row)


@router.delete("/logo", response_model=OperatorSettingsRead)
def delete_logo(db: Session = Depends(get_db)) -> OperatorSettingsRead:
    row = op_svc.get_or_create_operator_settings(db)
    op_svc.clear_logo_file(row)
    row.logo_filename = None
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_read(row)
