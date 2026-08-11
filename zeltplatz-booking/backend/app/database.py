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
        if booking_cols and "invoice_number" not in booking_cols:
            conn.execute(
                text("ALTER TABLE bookings ADD COLUMN invoice_number VARCHAR(32)")
            )
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_bookings_invoice_number "
                    "ON bookings (invoice_number)"
                )
            )
        if booking_cols and "group_leader" not in booking_cols:
            conn.execute(
                text(
                    "ALTER TABLE bookings ADD COLUMN group_leader TEXT "
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
        # Re-read columns after possible start/end upgrades
        person_cols = _table_cols(conn, "persons")
        if person_cols and "travel_document" not in person_cols:
            conn.execute(
                text(
                    "ALTER TABLE persons ADD COLUMN travel_document VARCHAR(500) "
                    "NOT NULL DEFAULT ''"
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
            if "home_country" not in op_cols:
                conn.execute(
                    text(
                        "ALTER TABLE operator_settings ADD COLUMN home_country VARCHAR(2) "
                        "NOT NULL DEFAULT 'AT'"
                    )
                )
                op_cols = _table_cols(conn, "operator_settings")
            count = conn.execute(text("SELECT COUNT(*) FROM operator_settings")).scalar()
            if not count:
                conn.execute(
                    text(
                        """
                        INSERT INTO operator_settings
                            (id, organization_name, address, iban, logo_filename, home_country)
                        VALUES (1, '', '', '', NULL, 'AT')
                        """
                    )
                )

        # Price profiles + soft-upgrade for existing DBs
        profile_cols = _table_cols(conn, "price_profiles")
        if not profile_cols:
            conn.execute(
                text(
                    """
                    CREATE TABLE price_profiles (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(120) NOT NULL UNIQUE,
                        is_default BOOLEAN NOT NULL DEFAULT 0,
                        sort_order INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )
            )
            profile_cols = _table_cols(conn, "price_profiles")

        if profile_cols:
            count = conn.execute(text("SELECT COUNT(*) FROM price_profiles")).scalar()
            if not count:
                conn.execute(
                    text(
                        """
                        INSERT INTO price_profiles (name, is_default, sort_order)
                        VALUES ('Standard', 1, 0)
                        """
                    )
                )
            default_id = conn.execute(
                text("SELECT id FROM price_profiles WHERE is_default = 1 LIMIT 1")
            ).scalar()
            if default_id is None:
                default_id = conn.execute(
                    text("SELECT id FROM price_profiles ORDER BY sort_order, name LIMIT 1")
                ).scalar()
                if default_id is not None:
                    conn.execute(
                        text("UPDATE price_profiles SET is_default = 1 WHERE id = :id"),
                        {"id": default_id},
                    )

            fee_cols = _table_cols(conn, "person_fee_elements")
            if fee_cols and "price_profile_id" not in fee_cols and default_id is not None:
                conn.execute(
                    text(
                        "ALTER TABLE person_fee_elements ADD COLUMN price_profile_id "
                        "INTEGER REFERENCES price_profiles(id) ON DELETE CASCADE"
                    )
                )
                conn.execute(
                    text(
                        "UPDATE person_fee_elements SET price_profile_id = :id "
                        "WHERE price_profile_id IS NULL"
                    ),
                    {"id": default_id},
                )

            person_cols = _table_cols(conn, "persons")
            if person_cols and "price_profile_id" not in person_cols and default_id is not None:
                conn.execute(
                    text(
                        "ALTER TABLE persons ADD COLUMN price_profile_id "
                        "INTEGER REFERENCES price_profiles(id) ON DELETE RESTRICT"
                    )
                )
                conn.execute(
                    text(
                        "UPDATE persons SET price_profile_id = :id WHERE price_profile_id IS NULL"
                    ),
                    {"id": default_id},
                )
