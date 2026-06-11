import unittest
from decimal import Decimal

from tests.helpers import import_contract_module


MODULE_PATH = "allocations.services.validation"
FUNCTION_NAME = "evaluate_distribution_closure"


class AllocationClosureContractTests(unittest.TestCase):
    """Contract for the future 100% distribution closing validator.

    Expected API:
    - allocations.services.validation.evaluate_distribution_closure(
        received_kg: Decimal,
        allocated_kg_values: Iterable[Decimal],
      )
    - returns an object or dict with:
        can_send: bool
        difference_kg: Decimal
    """

    def _validator(self):
        module = import_contract_module(
            MODULE_PATH,
            "O modulo de validacao de distribuicoes ainda nao existe.",
        )
        try:
            return getattr(module, FUNCTION_NAME)
        except AttributeError:
            self.fail(f"{MODULE_PATH} deve expor {FUNCTION_NAME}().")

    def _evaluate(self, received_kg: str, allocated_kg_values: list[str]):
        validator = self._validator()
        return validator(
            Decimal(received_kg),
            [Decimal(value) for value in allocated_kg_values],
        )

    def _field(self, result, name: str):
        if isinstance(result, dict):
            if name in result:
                return result[name]
            self.fail(f"Resultado deve conter a chave {name!r}.")

        if hasattr(result, name):
            return getattr(result, name)

        self.fail(f"Resultado deve expor o campo {name!r}.")

    def _difference(self, result) -> Decimal:
        return Decimal(str(self._field(result, "difference_kg")))

    def test_exact_distribution_can_be_sent(self):
        result = self._evaluate("1000.000", ["250.000", "350.000", "400.000"])

        self.assertTrue(bool(self._field(result, "can_send")))
        self.assertEqual(self._difference(result), Decimal("0"))

    def test_shortage_blocks_send(self):
        result = self._evaluate("1000.000", ["250.000", "350.000", "390.000"])

        self.assertFalse(bool(self._field(result, "can_send")))
        self.assertEqual(abs(self._difference(result)), Decimal("10.000"))

    def test_surplus_blocks_send(self):
        result = self._evaluate("1000.000", ["250.000", "350.000", "410.000"])

        self.assertFalse(bool(self._field(result, "can_send")))
        self.assertEqual(abs(self._difference(result)), Decimal("10.000"))

    def test_decimal_distribution_does_not_depend_on_float_rounding(self):
        result = self._evaluate("0.30", ["0.10", "0.20"])

        self.assertTrue(bool(self._field(result, "can_send")))
        self.assertEqual(self._difference(result), Decimal("0"))
