import re
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Credentials(StrictModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value):
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Enter a valid email address")
        return value.lower()


class Registration(Credentials):
    name: str = Field(min_length=2, max_length=80)
    workspace_name: str = Field(min_length=2, max_length=80)


class InvestigationRequest(StrictModel):
    question: str = Field(min_length=5, max_length=1000)
    use_ai: bool = True
    consent: bool = False


class CostCorrection(StrictModel):
    line_id: str = Field(min_length=1, max_length=100)
    product_cost: Decimal = Field(ge=0, le=10000000, decimal_places=2)
    shipping_cost: Decimal = Field(ge=0, le=10000000, decimal_places=2)
    reason: str = Field(min_length=5, max_length=300)
    expected_hash: str = Field(min_length=64, max_length=64)


class Scenario(StrictModel):
    discount_reduction: Decimal = Field(default=Decimal("10"), ge=0, le=1000, decimal_places=2)
    demand_drop: Decimal = Field(default=Decimal("8"), ge=0, le=50, decimal_places=2)
    max_demand_drop: Decimal = Field(default=Decimal("12"), ge=0, le=60, decimal_places=2)
    shipping_saving: Decimal = Field(default=Decimal("5"), ge=0, le=1000, decimal_places=2)
    extra_return_cost: Decimal = Field(default=Decimal("4"), ge=0, le=1000, decimal_places=2)
    implementation_cost: Decimal = Field(default=Decimal("0"), ge=0, le=10000000, decimal_places=2)


class Approval(StrictModel):
    expected_dataset_hash: str = Field(min_length=64, max_length=64)
    expected_scenario_hash: str = Field(min_length=64, max_length=64)
    acknowledged: bool


class WorkspaceUpdate(StrictModel):
    name: str = Field(min_length=2, max_length=80)
