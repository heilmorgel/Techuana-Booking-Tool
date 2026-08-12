from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Pitch(Base):
    __tablename__ = "pitches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    available_from: Mapped[date] = mapped_column(Date, nullable=False)
    available_to: Mapped[date] = mapped_column(Date, nullable=False)
    daily_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    deposit: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    booking_pitches: Mapped[list[BookingPitch]] = relationship(
        "BookingPitch",
        back_populates="pitch",
    )


class ServiceGroup(Base):
    __tablename__ = "service_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)

    services: Mapped[list[Service]] = relationship(
        "Service",
        back_populates="group",
        cascade="all, delete-orphan",
        order_by="Service.name",
    )


class Service(Base):
    __tablename__ = "services"
    __table_args__ = (UniqueConstraint("group_id", "name", name="uq_service_group_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("service_groups.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    available_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    daily_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    deposit: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    group: Mapped[ServiceGroup] = relationship("ServiceGroup", back_populates="services")
    booking_services: Mapped[list[BookingService]] = relationship(
        "BookingService",
        back_populates="service",
    )


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_name: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    group_leader: Mapped[str] = mapped_column(Text, nullable=False, default="")
    invoice_number: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True)
    deposit_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    booking_pitches: Mapped[list[BookingPitch]] = relationship(
        "BookingPitch",
        back_populates="booking",
        cascade="all, delete-orphan",
        order_by="BookingPitch.id",
    )
    persons: Mapped[list[Person]] = relationship(
        "Person",
        back_populates="booking",
        cascade="all, delete-orphan",
        order_by="Person.id",
    )
    booking_services: Mapped[list[BookingService]] = relationship(
        "BookingService",
        back_populates="booking",
        cascade="all, delete-orphan",
        order_by="BookingService.id",
    )
    custom_invoice_lines: Mapped[list["InvoiceCustomLine"]] = relationship(
        "InvoiceCustomLine",
        back_populates="booking",
        cascade="all, delete-orphan",
        order_by="InvoiceCustomLine.sort_order, InvoiceCustomLine.id",
    )
    amendments: Mapped[list[BookingAmendment]] = relationship(
        "BookingAmendment",
        back_populates="booking",
        cascade="all, delete-orphan",
        order_by="BookingAmendment.created_at.desc()",
    )


class BookingPitch(Base):
    __tablename__ = "booking_pitches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    pitch_id: Mapped[int] = mapped_column(ForeignKey("pitches.id", ondelete="RESTRICT"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    booking: Mapped[Booking] = relationship("Booking", back_populates="booking_pitches")
    pitch: Mapped[Pitch] = relationship("Pitch", back_populates="booking_pitches")


class BookingService(Base):
    __tablename__ = "booking_services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    booking: Mapped[Booking] = relationship("Booking", back_populates="booking_services")
    service: Mapped[Service] = relationship("Service", back_populates="booking_services")


class PriceProfile(Base):
    __tablename__ = "price_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deposit: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    elements: Mapped[list[PersonFeeElement]] = relationship(
        "PersonFeeElement",
        back_populates="price_profile",
        cascade="all, delete-orphan",
        order_by="PersonFeeElement.sort_order, PersonFeeElement.name",
    )
    persons: Mapped[list[Person]] = relationship("Person", back_populates="price_profile")


class Person(Base):
    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    nationality: Mapped[str] = mapped_column(String(2), nullable=False)
    travel_document: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    price_profile_id: Mapped[int] = mapped_column(
        ForeignKey("price_profiles.id", ondelete="RESTRICT"), nullable=False
    )

    booking: Mapped[Booking] = relationship("Booking", back_populates="persons")
    price_profile: Mapped[PriceProfile] = relationship("PriceProfile", back_populates="persons")


class BookingAmendment(Base):
    __tablename__ = "booking_amendments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    summary: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    diff_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    booking: Mapped[Booking] = relationship("Booking", back_populates="amendments")


class PersonFeeElement(Base):
    __tablename__ = "person_fee_elements"
    __table_args__ = (
        UniqueConstraint("price_profile_id", "name", name="uq_person_fee_element_profile_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    price_profile_id: Mapped[int] = mapped_column(
        ForeignKey("price_profiles.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # fixed | age_based | year_based
    daily_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    price_profile: Mapped[PriceProfile] = relationship("PriceProfile", back_populates="elements")
    brackets: Mapped[list[PersonFeeBracket]] = relationship(
        "PersonFeeBracket",
        back_populates="element",
        cascade="all, delete-orphan",
        order_by="PersonFeeBracket.age_from",
    )


class PersonFeeBracket(Base):
    __tablename__ = "person_fee_brackets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    element_id: Mapped[int] = mapped_column(
        ForeignKey("person_fee_elements.id", ondelete="CASCADE"), nullable=False
    )
    age_from: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    age_to_exclusive: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    element: Mapped[PersonFeeElement] = relationship("PersonFeeElement", back_populates="brackets")


class InvoiceCustomLine(Base):
    """Manual invoice positions: surcharge, discount, or zero-amount note."""

    __tablename__ = "invoice_custom_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    booking: Mapped[Booking] = relationship("Booking", back_populates="custom_invoice_lines")


class OperatorSettings(Base):
    """Singleton row (id=1) for invoice header/footer branding."""

    __tablename__ = "operator_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    address: Mapped[str] = mapped_column(Text, nullable=False, default="")
    iban: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    logo_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    home_country: Mapped[str] = mapped_column(String(2), nullable=False, default="AT")
