from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PitchBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    available_from: date
    available_to: date
    daily_price: float = Field(ge=0, default=0)

    @model_validator(mode="after")
    def check_availability_range(self) -> PitchBase:
        if self.available_from >= self.available_to:
            raise ValueError("available_from must be before available_to")
        return self


class PitchCreate(PitchBase):
    pass


class PitchUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    available_from: date | None = None
    available_to: date | None = None
    daily_price: float | None = Field(default=None, ge=0)


class PitchRead(PitchBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class PersonBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    birth_date: date
    nationality: str = Field(min_length=2, max_length=2)
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("nationality")
    @classmethod
    def uppercase_nationality(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def check_person_dates(self) -> PersonBase:
        if self.start_date is not None and self.end_date is not None and self.start_date >= self.end_date:
            raise ValueError("Person start_date must be before end_date")
        return self


class PersonCreate(PersonBase):
    pass


class PersonRead(PersonBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    start_date: date
    end_date: date


class BookingServiceItem(BaseModel):
    service_id: int
    quantity: int = Field(ge=1)


class BookingServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    service_id: int
    quantity: int
    service_name: str = ""
    group_name: str = ""
    daily_price: float = 0
    start_date: date
    end_date: date


class BookingPitchSegmentRead(BaseModel):
    pitch_id: int
    pitch_name: str = ""
    start_date: date
    end_date: date


class BookingAmendmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    effective_date: date
    created_at: datetime
    summary: str
    diff_json: str = "{}"


class BookingAmendRequest(BaseModel):
    effective_date: date
    end_date: date
    pitch_ids: list[int] = Field(min_length=1)
    persons: list[PersonCreate] = Field(default_factory=list)
    services: list[BookingServiceItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_dates(self) -> BookingAmendRequest:
        if self.effective_date >= self.end_date:
            raise ValueError("effective_date must be before end_date")
        return self


class BookingCreate(BaseModel):
    group_name: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date
    pitch_ids: list[int] = Field(min_length=1)
    persons: list[PersonCreate] = Field(default_factory=list)
    services: list[BookingServiceItem] = Field(default_factory=list)
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def check_dates(self) -> BookingCreate:
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date (end is exclusive departure day)")
        return self


class BookingUpdate(BaseModel):
    group_name: str | None = Field(default=None, min_length=1, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    pitch_ids: list[int] | None = Field(default=None, min_length=1)
    persons: list[PersonCreate] | None = None
    services: list[BookingServiceItem] | None = None
    notes: str | None = Field(default=None, max_length=2000)


class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_name: str
    start_date: date
    end_date: date
    created_at: datetime
    notes: str = ""
    pitch_ids: list[int] = []
    pitch_segments: list[BookingPitchSegmentRead] = []
    persons: list[PersonRead] = []
    services: list[BookingServiceRead] = []
    amendments: list[BookingAmendmentRead] = []
    warnings: list[str] = []


class BookingGanttItem(BaseModel):
    id: int
    group_name: str
    start_date: date
    end_date: date
    pitch_id: int
    pitch_name: str


class ServiceGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ServiceGroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)


class ServiceGroupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    service_count: int = 0


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    group_id: int
    available_quantity: int = Field(ge=0)
    daily_price: float = Field(ge=0, default=0)


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    group_id: int | None = None
    available_quantity: int | None = Field(default=None, ge=0)
    daily_price: float | None = Field(default=None, ge=0)


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    group_id: int
    group_name: str = ""
    available_quantity: int
    daily_price: float = 0


class ServiceAvailabilityRead(BaseModel):
    service_id: int
    name: str
    group_id: int
    group_name: str
    available_quantity: int
    daily_price: float = 0
    used: int
    remaining: int


class PersonFeeBracketCreate(BaseModel):
    age_from: int = Field(ge=0)
    age_to_exclusive: int | None = Field(default=None, ge=0)
    daily_price: float = Field(ge=0)

    @model_validator(mode="after")
    def check_ages(self) -> PersonFeeBracketCreate:
        if self.age_to_exclusive is not None and self.age_to_exclusive <= self.age_from:
            raise ValueError("age_to_exclusive must be greater than age_from")
        return self


class PersonFeeBracketRead(PersonFeeBracketCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class PersonFeeElementCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: str = Field(pattern="^(fixed|age_based)$")
    daily_price: float = Field(ge=0, default=0)
    sort_order: int = 0
    brackets: list[PersonFeeBracketCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_kind(self) -> PersonFeeElementCreate:
        if self.kind == "fixed" and self.brackets:
            raise ValueError("fixed elements must not have brackets")
        if self.kind == "age_based" and not self.brackets:
            raise ValueError("age_based elements require at least one bracket")
        return self


class PersonFeeElementUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: str | None = Field(default=None, pattern="^(fixed|age_based)$")
    daily_price: float | None = Field(default=None, ge=0)
    sort_order: int | None = None
    brackets: list[PersonFeeBracketCreate] | None = None


class PersonFeeElementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kind: str
    daily_price: float = 0
    sort_order: int = 0
    brackets: list[PersonFeeBracketRead] = []


class InvoiceLine(BaseModel):
    category: str
    label: str
    quantity: float
    unit_price: float
    nights: int
    amount: float
    start_date: date | None = None
    end_date: date | None = None


class InvoiceOperator(BaseModel):
    organization_name: str = ""
    address: str = ""
    iban: str = ""
    has_logo: bool = False


class InvoiceRead(BaseModel):
    booking_id: int
    group_name: str
    start_date: date
    end_date: date
    nights: int
    lines: list[InvoiceLine]
    total: float
    operator: InvoiceOperator = InvoiceOperator()


class BillingListItem(BaseModel):
    booking_id: int
    group_name: str
    start_date: date
    end_date: date
    nights: int
    total: float


class OperatorSettingsUpdate(BaseModel):
    organization_name: str | None = Field(default=None, max_length=200)
    address: str | None = None
    iban: str | None = Field(default=None, max_length=64)


class OperatorSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_name: str = ""
    address: str = ""
    iban: str = ""
    has_logo: bool = False
