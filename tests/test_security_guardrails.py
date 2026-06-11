import re
import unittest

from tests.helpers import ROOT, iter_project_text_files


SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"\b(?P<key>password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|connection[_-]?string)"
    r"\b\s*[:=]\s*[\"']?(?P<value>[^\s\"'#]+)",
    re.IGNORECASE,
)

SAFE_PLACEHOLDER_MARKERS = (
    "changeme",
    "dummy",
    "example",
    "fake",
    "placeholder",
    "sample",
    "todo",
    "your_",
)


class SecurityGuardrailsTests(unittest.TestCase):
    def test_no_obvious_secret_values_are_stored_in_project_files(self):
        violations = []

        for path in iter_project_text_files():
            relative_path = path.relative_to(ROOT)
            text = path.read_text(encoding="utf-8", errors="ignore")

            for line_number, line in enumerate(text.splitlines(), start=1):
                match = SENSITIVE_ASSIGNMENT_RE.search(line)
                if not match:
                    continue

                value = match.group("value").strip().lower()
                if len(value) < 12:
                    continue
                if any(marker in value for marker in SAFE_PLACEHOLDER_MARKERS):
                    continue

                violations.append(f"{relative_path}:{line_number}: {match.group('key')}")

        self.assertEqual(
            [],
            violations,
            "Possiveis credenciais ou tokens reais foram encontrados em arquivos do projeto.",
        )
