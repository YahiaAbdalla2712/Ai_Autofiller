from typing import Optional
from pydantic import BaseModel,Field

class StOutput(BaseModel):
    client_name: Optional[str] = Field(
        None, description="The name of the client/person/company associated with the transaction e.g. Moahmed Ahmed, Trends Egypt for systems, etc.. . REQUIRED."
    )
    amount: Optional[float] = Field(
        None, description="Transaction amount as a number. REQUIRED"
    )
    currency: Optional[str] = Field(
        None, description="ISO-style currency, e.g. EGP, USD. REQUIRED"
    )
    due_in_days: Optional[int] = Field(
        None, description="Number of days until the transaction is due. REQUIRED"
    )


REQUIRED_FIELDS = ["client_name", "amount", "currency", "due_in_days"]    