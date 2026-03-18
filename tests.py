from unittest import TestCase, main
from decimal import Decimal
from pydantic import ValidationError
from datetime import datetime, date, timedelta
from modules.modules import User, Transaction, Currency, TransactionType, PolicyStatus, InsurancePolicy, Account, to_camel
from main import parse_errors, validate_model, GlobalConfig

class ClassWithDataForTesting(TestCase):
    def _valid_user_payload(self, **overrides) -> dict:
        base = {
            "id": "ACC-0001",
            "email": "john.doe@example.com",
            "age": 30,
            "user_first_name": "John",
            "user_last_name": "Doe",
            "address": {
                "street": "123 Main St",
                "city": "Springfield",
                "zip_code": "12345",
            },
            "social_security_number": None,
        }
        return {**base, **overrides}
    
    def _valid_transaction_payload(self, **overrides) -> dict:
        base = {
            "currency": Currency.USD,
            "amount": Decimal("100.00"),
            "timestamp": datetime(2024, 1, 15, 12, 0, 0),
            "transaction_type": TransactionType.CREDIT,
        }
        return {**base, **overrides}
    
    def _valid_insurance_policy_payload(self, **overrides) -> dict:
        base = {
            "policy_number": "ABCDEFGHIJ",
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 3, 1),
            "status": PolicyStatus.ACTIVE,
        }
        return {**base, **overrides}

    def _valid_account_payload(self, **overrides) -> dict:
        base = {
            "user": User(**self._valid_user_payload()),
            "transactions": [],
        }
        return {**base, **overrides}

class TestToCamel(ClassWithDataForTesting):
    def test_single_word_unchanged(self):
        self.assertEqual(to_camel("username"), "username")

    def test_multiple_words(self):
        self.assertEqual(to_camel("user_first_name"), "userFirstName")


class UserIdTests(ClassWithDataForTesting):
    def test_user_id_invalid(self):
        with self.assertRaises(ValueError) as cm:
            User(**self._valid_user_payload(id="bad_id"))
        self.assertIn("must be a UUID or match pattern", str(cm.exception))

    def test_user_id_valid(self):
        User(**self._valid_user_payload())


class TransactionCurrencyTests(ClassWithDataForTesting):
    def test_currency_error_occured(self):
        with self.assertRaises(ValidationError) as ctx:
            Transaction(**self._valid_transaction_payload(currency="JPY"))
        self.assertIn("Input should be 'USD', 'EUR' or 'GBP'", str(ctx.exception))

    def test_currency_error_not_occured(self):
        for valid_currency in Currency:
            with self.subTest(currency=valid_currency):
                transaction = Transaction(**self._valid_transaction_payload(currency=valid_currency))
                self.assertEqual(transaction.currency, valid_currency)


class InsuranceTests(ClassWithDataForTesting):
    
    def test_policy_format_valid(self):
        policy = InsurancePolicy(**self._valid_insurance_policy_payload())
        self.assertEqual(policy.policy_number, "ABCDEFGHIJ")

    def test_policy_format_invalid_length(self):
        for invalid in ["ABCDE", "ABCDEFGHIJK"]:
            with self.subTest(policy_number=invalid):
                with self.assertRaises(ValidationError) as ctx:
                    InsurancePolicy(**self._valid_insurance_policy_payload(policy_number=invalid))
                self.assertIn("10 characters", str(ctx.exception))

    def test_policy_format_invalid_characters(self):
        for invalid in ["abcdefghij", "ABCDE12345", "ABCDE!@#$%"]:
            with self.subTest(policy_number=invalid):
                with self.assertRaises(ValidationError) as ctx:
                    InsurancePolicy(**self._valid_insurance_policy_payload(policy_number=invalid))
                self.assertIn("uppercase", str(ctx.exception))

    def test_validate_dates_valid(self):
        policy = InsurancePolicy(**self._valid_insurance_policy_payload(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 1)
        ))
        self.assertEqual(policy.end_date, date(2024, 3, 1))

    def test_validate_dates_29_days_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            InsurancePolicy(**self._valid_insurance_policy_payload(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 30)
            ))
        self.assertIn("30 days", str(ctx.exception))


class AccountTests(ClassWithDataForTesting):    
    def test_total_portfolio_value_no_transactions(self):
        account = Account(**self._valid_account_payload())
        self.assertEqual(account.total_portfolio_value, Decimal("0"))

    def test_total_portfolio_value_single_transaction(self):
        transaction = Transaction(**self._valid_transaction_payload(amount=Decimal("200.00")))
        account = Account(**self._valid_account_payload(transactions=[transaction]))
        self.assertEqual(account.total_portfolio_value, Decimal("200.00"))

    def test_total_portfolio_value_multiple_transactions(self):
        transactions = [
            Transaction(**self._valid_transaction_payload(amount=Decimal("100.00"))),
            Transaction(**self._valid_transaction_payload(amount=Decimal("250.50"))),
            Transaction(**self._valid_transaction_payload(amount=Decimal("49.50"))),
        ]
        account = Account(**self._valid_account_payload(transactions=transactions))
        self.assertEqual(account.total_portfolio_value, Decimal("400.00"))

    def test_risk_score_high(self):
        transactions = [Transaction(**self._valid_transaction_payload(amount=Decimal("10001.00")))]
        user = User(**self._valid_user_payload(age=29))
        account = Account(**self._valid_account_payload(user=user, transactions=transactions))
        self.assertEqual(account.risk_score, "High")

    def test_risk_score_medium(self):
        for user_age, amount in [
            (30, Decimal("10001.00")),
            (29, Decimal("5001.00")),
        ]:
            with self.subTest(age=user_age, amount=amount):
                transactions = [Transaction(**self._valid_transaction_payload(amount=amount))]
                user = User(**self._valid_user_payload(age=user_age))
                account = Account(**self._valid_account_payload(user=user, transactions=transactions))
                self.assertEqual(account.risk_score, "Medium")

    def test_risk_score_low(self):
        transactions = [Transaction(**self._valid_transaction_payload(amount=Decimal("1000.00")))]
        account = Account(**self._valid_account_payload(transactions=transactions))
        self.assertEqual(account.risk_score, "Low")


class TestValidateModel(ClassWithDataForTesting):

    config = GlobalConfig()

    def test_valid_data_returns_model_instance(self):
        result = validate_model(User, self._valid_user_payload())
        self.assertIsInstance(result, User)

    def test_invalid_data_returns_parsed_errors(self):
        result = validate_model(User, self._valid_user_payload(age=10))
        self.assertIsInstance(result, list)
        self.assertIn("msg", result[0])
        self.assertIn("loc", result[0])

    def test_strict_mode_valid_data_returns_model_instance(self):
        self.config.strict_mode = True
        result = validate_model(User, self._valid_user_payload())
        self.assertIsInstance(result, User)
        self.config.strict_mode = False


class TestParseErrors(ClassWithDataForTesting):
    def test_parse_errors_returns_loc_and_msg(self):
        with self.assertRaises(ValidationError) as ctx:
            User(**self._valid_user_payload(age=10))
        result = parse_errors(ctx.exception)
        self.assertTrue(all("loc" in e and "msg" in e for e in result))

    def test_parse_errors_multiple_errors(self):
        with self.assertRaises(ValidationError) as ctx:
            User(**self._valid_user_payload(age=10, email="not-an-email"))
        result = parse_errors(ctx.exception)
        self.assertGreaterEqual(len(result), 2)

if __name__ == '__main__':
    main()