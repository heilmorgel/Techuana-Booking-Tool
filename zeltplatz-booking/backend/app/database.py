from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    settings = get_settings()
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


engine = _make_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _table_cols(conn, table: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows} if rows else set()


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Soft-upgrade for existing SQLite DBs (create_all does not add columns / reshape)
    with engine.begin() as conn:
        service_cols = _table_cols(conn, "services")
        if service_cols and "daily_price" not in service_cols:
            conn.execute(
                text(
                    "ALTER TABLE services ADD COLUMN daily_price NUMERIC(10, 2) "
                    "NOT NULL DEFAULT 0"
                )
            )

        booking_cols = _table_cols(conn, "bookings")
        if booking_cols and "notes" not in booking_cols:
            conn.execute(
                text(
                    "ALTER TABLE bookings ADD COLUMN notes VARCHAR(2000) "
                    "NOT NULL DEFAULT ''"
                )
            )

        pitch_cols = _table_cols(conn, "pitches")
        if pitch_cols and "daily_price" not in pitch_cols:
            conn.execute(
                text(
                    "ALTER TABLE pitches ADD COLUMN daily_price NUMERIC(10, 2) "
                    "NOT NULL DEFAULT 0"
                )
            )

        person_cols = _table_cols(conn, "persons")
        if person_cols and "start_date" not in person_cols:
            conn.execute(
                text(
                    "ALTER TABLE persons ADD COLUMN start_date DATE "
                    "NOT NULL DEFAULT '1970-01-01'"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE persons ADD COLUMN end_date DATE "
                    "NOT NULL DEFAULT '1970-01-02'"
                )
            )
            conn.execute(
                text(
                    """
                    UPDATE persons
                    SET start_date = (
                        SELECT bookings.start_date FROM bookings
                        WHERE bookings.id = persons.booking_id
                    ),
                    end_date = (
                        SELECT bookings.end_date FROM bookings
                        WHERE bookings.id = persons.booking_id
                    )
                    """
                )
            )

        bp_cols = _table_cols(conn, "booking_pitches")
        if bp_cols and "id" not in bp_cols:
            conn.execute(text("ALTER TABLE booking_pitches RENAME TO booking_pitches_old"))
            conn.execute(
                text(
                    """
                    CREATE TABLE booking_pitches (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        booking_id INTEGER NOT NULL,
                        pitch_id INTEGER NOT NULL,
                        start_date DATE NOT NULL,
                        end_date DATE NOT NULL,
                        FOREIGN KEY(booking_id) REFERENCES bookings (id) ON DELETE CASCADE,
                        FOREIGN KEY(pitch_id) REFERENCES pitches (id) ON DELETE RESTRICT
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    INSERT INTO booking_pitches (booking_id, pitch_id, start_date, end_date)
                    SELECT bp.booking_id, bp.pitch_id, b.start_date, b.end_date
                    FROM booking_pitches_old bp
                    JOIN bookings b ON b.id = bp.booking_id
                    """
                )
            )
            conn.execute(text("DROP TABLE booking_pitches_old"))

        bs_cols = _table_cols(conn, "booking_services")
        if bs_cols and "start_date" not in bs_cols:
            conn.execute(
                text(
                    "ALTER TABLE booking_services ADD COLUMN start_date DATE "
                    "NOT NULL DEFAULT '1970-01-01'"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE booking_services ADD COLUMN end_date DATE "
                    "NOT NULL DEFAULT '1970-01-02'"
                )
            )
            conn.execute(
                text(
                    """
                    UPDATE booking_services
                    SET start_date = (
                        SELECT bookings.start_date FROM bookings
                        WHERE bookings.id = booking_services.booking_id
                    ),
                    end_date = (
                        SELECT bookings.end_date FROM bookings
                        WHERE bookings.id = booking_services.booking_id
                    )
                    """
                )
            )

        # booking_amendments created by create_all when missing

        # Seed singleton operator settings when table exists but empty
        op_cols = _table_cols(conn, "operator_settings")
        if op_cols:
            count = conn.execute(text("SELECT COUNT(*) FROM operator_settings")).scalar()
            if not count:
                conn.execute(
                    text(
                        """
                        INSERT INTO operator_settings
                            (id, organization_name, address, iban, logo_filename)
                        VALUES (1, '', '', '', NULL)
                        """
                    )
                )
