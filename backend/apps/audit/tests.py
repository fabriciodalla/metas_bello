from django.test import TestCase

from apps.hierarchy.models import HierarchyNode

from .models import AuditLogEntry


class AuditLogEntryTests(TestCase):
    def test_entry_links_to_any_tracked_model_via_generic_relation(self):
        node = HierarchyNode.objects.create(level=HierarchyNode.Level.GERENTE, nome="Gerente")

        entry = AuditLogEntry.objects.create(
            content_object=node,
            action=AuditLogEntry.Action.CRIACAO,
            changes={"nome": {"de": None, "para": "Gerente"}},
        )

        self.assertEqual(entry.content_object, node)
        self.assertIsNone(entry.changed_by)
