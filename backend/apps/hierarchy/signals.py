from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import HierarchyNode
from .services import HierarchyClosureService


@receiver(post_save, sender=HierarchyNode)
def rebuild_closure_on_save(sender, **kwargs):
    HierarchyClosureService.rebuild()


@receiver(post_delete, sender=HierarchyNode)
def rebuild_closure_on_delete(sender, **kwargs):
    HierarchyClosureService.rebuild()
