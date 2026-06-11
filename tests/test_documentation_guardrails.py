import re
import unittest

from tests.helpers import read_project_text


class DocumentationGuardrailsTests(unittest.TestCase):
    def test_project_docs_keep_core_business_invariants(self):
        project = read_project_text("docs/PROJECT.md").lower()

        for phrase in (
            "mensal",
            "kg",
            "100%",
            "bloqueado",
            "somente leitura",
            "registrar quem criou, alterou, distribuiu e liberou",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, project)

    def test_architecture_keeps_system_database_separate_from_erp(self):
        architecture = read_project_text("docs/ARCHITECTURE.md").lower()

        for phrase in (
            "postgresql proprio",
            "banco/erp",
            "somente leitura",
            "nunca gravar dados no erp",
            "conexao erp mockada ou isolada em testes",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, architecture)

    def test_decision_log_records_critical_approved_decisions(self):
        decision_log = read_project_text("docs/DECISION_LOG.md")

        critical_decisions = {
            "Regra de aprovacao": "bloqueio quando a soma distribuida nao fecha 100%",
            "Excecao principal": "envio fica bloqueado",
            "Integracao ERP": "Leitura direta em banco somente leitura",
            "Tecnologia web": "Django",
            "Banco do sistema": "PostgreSQL",
        }

        for topic, expected_text in critical_decisions.items():
            pattern = (
                r"\|\s*2026-06-10\s*\|\s*"
                + re.escape(topic)
                + r"\s*\|\s*approved\s*\|[^|]*"
                + re.escape(expected_text)
            )
            with self.subTest(topic=topic):
                self.assertRegex(decision_log, pattern)
