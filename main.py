import os
from typing import Any, Dict, List
from pydantic import ValidationError
from pydantic_settings import BaseSettings
from modules.modules import Account, User, Transaction, InsurancePolicy


class GlobalConfig(BaseSettings):

    strict_mode: bool = False

    class Config:
        env_prefix = "APP_"


config = GlobalConfig()

def validate_model(model, data: Dict[str, Any]):
    try:
        if config.strict_mode:
            return model.model_validate(data, strict=True)
        return model.model_validate(data)
    except ValidationError as e:
        return parse_errors(e)

def parse_errors(error: ValidationError) -> List[Dict]:
    parsed = []
    for err in error.errors():
        parsed.append(
            {
                "loc": err["loc"],
                "msg": err["msg"]
            }
        )
    return parsed

raw_account_data = {
    "user": {
        "id": "ACC-1234",
        "email": "user@email.com",
        "age": "29",
        "userFirstName": "Alice",
        "userLastName": "Smith",
        "socialSecurityNumber": "999-99-9999",

        "address": {
            "street": "Main St",
            "city": "New York",
            "zipCode": "10001"
        }
    },
    "transactions": [
        {
            "currency": "USD",
            "amount": "100.50",
            "timestamp": "2025-03-01T12:00:00",
            "transactionType": "DEBIT"
        },
        {
            "currency": "EUR",
            "amount": "5000",
            "timestamp": "2025-03-02T10:30:00",
            "transactionType": "CREDIT"
        }
    ]
}

def run():
    result = validate_model(Account, raw_account_data)

    if isinstance(result, list):
        print("Validation errors:")
        print(result)
        return

    account: Account = result

    print("\nClean Model Object\n")
    print(account)

    print("\nExported JSON (SSN removed)\n")
    print(account.model_dump())

    print("\nPortfolio Value\n")
    print(account.total_portfolio_value)

    print("\nRisk Score\n")
    print(account.risk_score)


if __name__ == "__main__":
    run()