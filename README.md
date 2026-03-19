# Financial Account Validation System

A Python application for validating and modeling financial account data using **Pydantic v2**. It handles user profiles, transactions, insurance policies, and computes derived financial metrics like portfolio value and risk scores.

---

## Project Structure

```
project/
├── main.py        # Entry point — config, validation logic, and sample data
├── modules.py     # Pydantic models and business logic
└── README.md
```

---

## Requirements

- Python 3.10+
- pip

### Dependencies

| Package | Purpose |
|---|---|
| `pydantic[email]` | Core data validation and modeling |
| `pydantic-settings` | Environment-based configuration via `BaseSettings` |

---

## Setup

### 1. Create and activate a virtual environment

```bash
# Create the virtual environment
python -m venv venv

# Activate on macOS/Linux
source venv/bin/activate

# Activate on Windows
venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> The `[email]` extra installs `email-validator`, which is required for Pydantic's `EmailStr` type used in the `User` model.

### 3. Run the application

```bash
python main.py
```

---

## Configuration (`main.py`)

### `GlobalConfig`

Built on `pydantic-settings`' `BaseSettings`, this class reads configuration from environment variables prefixed with `APP_`.

| Setting | Type | Default | Description |
|---|---|---|---|
| `strict_mode` | `bool` | `False` | If `True`, Pydantic will not coerce types (e.g., `"29"` will not be cast to `int`) |

To enable strict mode before running:

```bash
export APP_STRICT_MODE=true
python main.py
```

### `validate_model(model, data)`

A wrapper around Pydantic's `model_validate` that respects the `strict_mode` config flag. Returns either a validated model instance or a list of parsed validation errors.

### `parse_errors(error)`

Takes a Pydantic `ValidationError` and returns a clean list of dictionaries, each containing the field location (`loc`) and human-readable message (`msg`).

---

## Models (`modules.py`)

All models use a shared **camelCase alias generator** (`to_camel`), meaning they can accept camelCase JSON input (e.g., `userFirstName`) and map it to snake_case Python attributes (e.g., `user_first_name`). This is configured via `populate_by_name=True`, so both formats are accepted.

---

### `Currency` (Enum)
Allowed currency codes for transactions.

| Value |
|---|
| `USD` |
| `EUR` |
| `GBP` |

---

### `TransactionType` (Enum)
Direction of a financial transaction.

| Value | Meaning |
|---|---|
| `DEBIT` | Money going out |
| `CREDIT` | Money coming in |

---

### `PolicyStatus` (Enum)
Current state of an insurance policy.

| Value |
|---|
| `ACTIVE` |
| `ELAPSED` |
| `PENDING` |

---

### `Address`

Represents a physical mailing address.

| Field | Type | Validation |
|---|---|---|
| `street` | `str` | Required |
| `city` | `str` | Required |
| `zip_code` | `str` | Must match `^\d{5}$` (5-digit US ZIP code) |

---

### `User`

Represents an account holder.

| Field | Type | Validation / Notes |
|---|---|---|
| `id` | `str` | Must be a valid UUID **or** match `ACC-XXXX` (e.g., `ACC-1234`) |
| `email` | `EmailStr` | Must be a valid email address |
| `age` | `int` | Must be between 18 and 120 (inclusive) |
| `user_first_name` | `Optional[str]` | Optional |
| `user_last_name` | `Optional[str]` | Optional |
| `address` | `Address` | Nested address object (see above) |
| `social_security_number` | `Optional[str]` | Optional — **excluded from all serialized output** |

> **Privacy note:** The `social_security_number` field is marked `exclude=True`, meaning it is stripped from any `model_dump()` or `model_dump_json()` output, even if it was provided during validation.

---

### `Transaction`

Represents a single financial transaction.

| Field | Type | Validation |
|---|---|---|
| `currency` | `Currency` | Must be `USD`, `EUR`, or `GBP` |
| `amount` | `Decimal` | Must be greater than `0` |
| `timestamp` | `datetime` | ISO 8601 datetime string |
| `transaction_type` | `TransactionType` | Must be `DEBIT` or `CREDIT` |

---

### `InsurancePolicy`

Represents an insurance policy attached to an account.

| Field | Type | Validation |
|---|---|---|
| `policy_number` | `str` | Must be exactly 10 uppercase letters (`^[A-Z]{10}$`) |
| `start_date` | `date` | ISO date string |
| `end_date` | `date` | Must be at least 30 days after `start_date` |
| `status` | `PolicyStatus` | Must be `ACTIVE`, `ELAPSED`, or `PENDING` |

The `validate_dates` model validator runs after field validation and raises an error if `end_date` is less than 30 days after `start_date`.

---

### `Account`

The top-level model, combining a user with their transaction history.

| Field | Type | Notes |
|---|---|---|
| `user` | `User` | Nested `User` object |
| `transactions` | `List[Transaction]` | Defaults to an empty list |

#### Computed Properties

**`total_portfolio_value`** *(property)*

Sums the `amount` of all transactions and returns a `Decimal`. This is a plain Python property and is not included in serialized output.

**`risk_score`** *(computed field)*

Automatically included in `model_dump()` output. Determined by the following logic:

| Condition | Score |
|---|---|
| Portfolio > $10,000 **and** user age < 30 | `"High"` |
| Portfolio > $5,000 | `"Medium"` |
| All other cases | `"Low"` |

---

## Example Output

Running `main.py` with the bundled sample data produces:

```
Clean Model Object

user=User(id='ACC-1234', email='user@email.com', age=29, ...) transactions=[...]

Exported JSON (SSN removed)

{'user': {'id': 'ACC-1234', 'email': 'user@email.com', ...}, 'transactions': [...], 'risk_score': 'Low'}

Portfolio Value

5100.50

Risk Score

Medium
```

> Note: The SSN (`999-99-9999`) provided in the raw data does **not** appear in the exported JSON output.
