import re
from datetime import datetime, date, timedelta
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator, computed_field, ConfigDict

def to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"


class TransactionType(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class PolicyStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ELAPSED = "ELAPSED"
    PENDING = "PENDING"


class Address(BaseModel):
    street: str
    city: str
    zip_code: str = Field(pattern=r"^\d{5}$")

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class User(BaseModel):
    id: str
    email: EmailStr
    age: int = Field(ge=18, le=120)
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None
    address: Address

    social_security_number: Optional[str] = Field(
        default=None,
        exclude=True
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v):
        acc_pattern = r"^ACC-\d{4}$"
        try:
            UUID(str(v))
            return v
        except Exception:
            pass
        if re.match(acc_pattern, v):
            return v
        raise ValueError(
            "User ID must be a UUID or match pattern ACC-XXXX"
        )
   

class Transaction(BaseModel):
    currency: Currency
    amount: Decimal = Field(gt=0)
    timestamp: datetime
    transaction_type: TransactionType

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

    @field_validator("currency")
    @classmethod
    def currency_error(cls, v):
        if v not in Currency:
            raise ValueError(
                "Please select a valid currency: USD, EUR, or GBP"
            )
        return v


class InsurancePolicy(BaseModel):
    policy_number: str
    start_date: date
    end_date: date
    status: PolicyStatus

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

    @field_validator("policy_number")
    @classmethod
    def policy_format(cls, v):
        if not re.match(r"^[A-Z]{10}$", v):
            raise ValueError(
                "Policy number must be uppercase and exactly 10 characters"
            )
        return v

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date + timedelta(days=30):
            raise ValueError(
                "Policy end_date must be at least 30 days after start_date"
            )
        return self


class Account(BaseModel):
    user: User
    transactions: List[Transaction] = []

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

    @property
    def total_portfolio_value(self) -> Decimal:
        total = Decimal("0")
        for t in self.transactions:
            total += t.amount
        return total

    @computed_field
    @property
    def risk_score(self) -> str:
        total = self.total_portfolio_value
        age = self.user.age
        if total > Decimal("10000") and age < 30:
            return "High"
        if total > Decimal("5000"):
            return "Medium"
        return "Low"