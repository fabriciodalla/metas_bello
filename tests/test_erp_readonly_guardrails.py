import re
import unittest

from tests.helpers import ROOT


# SQL de escrita no inicio de uma string literal (raw SQL passado para cursor.execute)
RAW_SQL_WRITE_RE = re.compile(
    r"""['"]{1,3}\s*(ALTER|CREATE|DELETE|DROP|INSERT|MERGE|TRUNCATE|UPDATE)\b""",
    re.IGNORECASE,
)

# Metodos ORM do Django que gravam no banco
ORM_WRITE_RE = re.compile(
    r"""\.(save|delete|create|update|bulk_create|bulk_update|get_or_create|update_or_create)\s*\(""",
    re.IGNORECASE,
)


class ErpReadonlyGuardrailsTests(unittest.TestCase):
    def test_erp_readonly_code_does_not_contain_write_operations(self):
        erp_dir = ROOT / "erp_readonly"
        if not erp_dir.exists():
            raise unittest.SkipTest("O app erp_readonly ainda nao existe.")

        violations = []
        for path in erp_dir.rglob("*.py"):
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8", errors="ignore").splitlines(),
                start=1,
            ):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if RAW_SQL_WRITE_RE.search(stripped) or ORM_WRITE_RE.search(stripped):
                    relative_path = path.relative_to(ROOT)
                    violations.append(f"{relative_path}:{line_number}: {stripped}")

        self.assertEqual(
            [],
            violations,
            "O adaptador ERP deve permanecer somente leitura; operacao de escrita foi encontrada.",
        )
