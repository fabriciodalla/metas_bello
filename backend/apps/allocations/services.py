from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.models import AuditLogEntry
from apps.cycles.models import Cycle
from apps.hierarchy.models import HierarchyNode

from .models import GoalAllocation


class AllocationClosureError(ValidationError):
    """Falha na invariante de fechamento: soma das filhas não bate com o pai."""


class AllocationScopeError(ValidationError):
    """Falha de isolamento de escopo: só se distribui o que se possui, para filhos diretos."""


class AllocationReopenError(ValidationError):
    """Falha ao reabrir: alocação ainda não distribuída, ou ciclo já não está aberto."""


@dataclass(frozen=True)
class ChildAllocationSpec:
    owner_node_id: int
    quantity_kg: int
    granularity: str
    group_id: int | None = None
    subgroup_id: int | None = None
    product_id: int | None = None


class ClosureValidator:
    """Garante o fechamento exato, independente de qual estratégia gerou os valores."""

    @staticmethod
    def validate(parent_quantity_kg: int, children_quantities_kg: list[int]) -> None:
        for qty in children_quantities_kg:
            if not isinstance(qty, int) or isinstance(qty, bool):
                raise AllocationClosureError(f"Quantidade {qty!r} não é um inteiro.")
            if qty < 0:
                raise AllocationClosureError(f"Quantidade {qty} kg é negativa.")

        total = sum(children_quantities_kg)
        if total != parent_quantity_kg:
            raise AllocationClosureError(
                f"Soma das filhas ({total} kg) não fecha com o pai ({parent_quantity_kg} kg)."
            )


class DistributeGoalService:
    """Repassa uma GoalAllocation às filhas numa única transação, validada pelo ClosureValidator."""

    @staticmethod
    @transaction.atomic
    def distribute(
        parent: GoalAllocation, children: list[ChildAllocationSpec], criado_por
    ) -> list[GoalAllocation]:
        if parent.distributed:
            raise AllocationClosureError("Esta alocação já foi distribuída.")

        if not criado_por.hierarchy_nodes.filter(id=parent.owner_node_id).exists():
            raise AllocationScopeError("Você só pode distribuir uma alocação que possui.")

        parent_id_by_node_id = dict(
            HierarchyNode.objects.filter(id__in=[child.owner_node_id for child in children]).values_list(
                "id", "parent_id"
            )
        )
        for child in children:
            if parent_id_by_node_id.get(child.owner_node_id) != parent.owner_node_id:
                raise AllocationScopeError(
                    f"O nó {child.owner_node_id} não é filho direto de quem está distribuindo."
                )

        ClosureValidator.validate(parent.quantity_kg, [child.quantity_kg for child in children])

        created = [
            GoalAllocation(
                cycle=parent.cycle,
                owner_node_id=child.owner_node_id,
                parent_allocation=parent,
                granularity=child.granularity,
                group_id=child.group_id,
                subgroup_id=child.subgroup_id,
                product_id=child.product_id,
                quantity_kg=child.quantity_kg,
                criado_por=criado_por,
            )
            for child in children
        ]
        for allocation in created:
            allocation.full_clean()
            allocation.save()

        parent.distributed = True
        parent.save(update_fields=["distributed", "updated_at"])

        return created


def _collect_descendants(allocation: GoalAllocation) -> list[GoalAllocation]:
    """Sub-árvore inteira de GoalAllocation abaixo de `allocation` (não inclui ela mesma), em
    ordem de nível (a última posição da lista contém as folhas mais profundas)."""
    descendants: list[GoalAllocation] = []
    frontier = [allocation]
    while frontier:
        children = list(GoalAllocation.objects.filter(parent_allocation__in=frontier))
        descendants.extend(children)
        frontier = children
    return descendants


class ReopenAllocationService:
    """Reabre uma alocação já distribuída (H4): invalida em cascata toda a sub-árvore de filhas,
    apagando-as e registrando o evento no AuditLogEntry, e devolve esta alocação a
    distributed=False. Depois de reaberta, DistributeGoalService.distribute() (sem nenhuma
    mudança) pode ser chamado de novo para refazer o repasse.

    Escopo mínimo (H4): só o ramo desta alocação para baixo é invalidado — a alocação-pai e
    irmãos não tocados permanecem válidos.
    """

    @staticmethod
    @transaction.atomic
    def reopen(allocation: GoalAllocation, criado_por) -> GoalAllocation:
        """Reabertura voluntária: só quem possui a alocação pode reabri-la (H4)."""
        if not criado_por.hierarchy_nodes.filter(id=allocation.owner_node_id).exists():
            raise AllocationScopeError("Você só pode reabrir uma alocação que possui.")

        return ReopenAllocationService._reopen_unchecked(allocation, changed_by=criado_por, motivo=None)

    @staticmethod
    @transaction.atomic
    def reopen_for_hierarchy_change(
        allocation: GoalAllocation, changed_by, affected_node: HierarchyNode
    ) -> GoalAllocation:
        """Reabertura automática (O4): disparada quando um nó da hierarquia é desativado ou
        reparentado enquanto tem meta em ciclo aberto — não é o dono da alocação pedindo, por
        isso não passa pela checagem de posse de `reopen()`. `allocation` aqui é a alocação-PAI
        (quem distribuiu para o nó afetado), não a alocação do próprio nó afetado.
        """
        return ReopenAllocationService._reopen_unchecked(
            allocation,
            changed_by=changed_by,
            motivo={"motivo": "mudanca_hierarquia", "no_afetado_id": affected_node.id},
        )

    @staticmethod
    def _reopen_unchecked(allocation: GoalAllocation, changed_by, motivo: dict | None) -> GoalAllocation:
        if not allocation.distributed:
            raise AllocationReopenError("Esta alocação ainda não foi distribuída — nada para reabrir.")

        if allocation.cycle.status != Cycle.Status.ABERTO:
            raise AllocationReopenError("Só é possível reabrir alocações de um ciclo aberto.")

        descendants = _collect_descendants(allocation)

        changes = {
            "distributed": {"de": True, "para": False},
            "filhas_invalidadas": [
                {
                    "id": child.id,
                    "owner_node_id": child.owner_node_id,
                    "quantity_kg": child.quantity_kg,
                }
                for child in descendants
            ],
        }
        if motivo:
            changes.update(motivo)

        AuditLogEntry.objects.create(
            content_object=allocation,
            action=AuditLogEntry.Action.REABERTURA,
            changes=changes,
            changed_by=changed_by,
        )

        # Apaga da folha mais profunda para cima, senão on_delete=PROTECT em parent_allocation barra.
        for child in reversed(descendants):
            child.delete()

        allocation.distributed = False
        allocation.save(update_fields=["distributed", "updated_at"])

        return allocation


class HierarchyChangeReassignmentService:
    """O4: quando um nó da hierarquia é desativado (ativo=False) ou reparentado (parent mudou)
    enquanto tem meta em ciclo aberto, a alocação-PAI (quem tinha distribuído para esse nó) é
    reaberta em cascata — a meta "volta pro nó pai", que precisa redistribuir considerando a
    mudança (o nó afetado deixa de ser um alvo válido). Não decide para onde a meta vai depois
    disso — só garante que ela nunca fica presa/órfã num nó que saiu da estrutura ativa.

    Não cobre a alocação do PRÓPRIO nó afetado isoladamente — reabrir a alocação-pai já invalida
    em cascata toda a sub-árvore abaixo dela, incluindo a alocação do nó afetado e a de seus
    irmãos (o `distributed` do pai é tudo-ou-nada; não dá pra "devolver" só a fatia de um filho
    sem redistribuir o total de novo).
    """

    @staticmethod
    @transaction.atomic
    def reassign_open_cycle_allocations(node: HierarchyNode, changed_by) -> list[GoalAllocation]:
        affected_allocations = GoalAllocation.objects.filter(
            owner_node=node, cycle__status=Cycle.Status.ABERTO, parent_allocation__isnull=False
        ).select_related("parent_allocation")

        reopened = []
        seen_parent_ids = set()
        for allocation in affected_allocations:
            parent = allocation.parent_allocation
            if parent.id in seen_parent_ids or not parent.distributed:
                continue
            seen_parent_ids.add(parent.id)
            ReopenAllocationService.reopen_for_hierarchy_change(
                parent, changed_by=changed_by, affected_node=node
            )
            reopened.append(parent)

        return reopened


@dataclass(frozen=True)
class StuckAllocation:
    allocation_id: int
    owner_node_id: int
    owner_node_level: str
    quantity_kg: int


class CycleCompletenessChecker:
    """Verifica a invariante end-to-end: 100% da meta do ciclo chega ao nível VENDEDOR.

    Alocações VENDEDOR são folhas legítimas e nunca contam como presas, mesmo com
    distributed=False. Tratamento de nós inativos / ramos sem vendedor ativo fica em
    aberto (ver docs/open-questions.md O4/O5) e não é decidido aqui.
    """

    @staticmethod
    def stuck_allocations(cycle) -> list[StuckAllocation]:
        pending = (
            GoalAllocation.objects.filter(cycle=cycle, distributed=False)
            .exclude(owner_node__level=HierarchyNode.Level.VENDEDOR)
            .select_related("owner_node")
        )
        return [
            StuckAllocation(
                allocation_id=allocation.id,
                owner_node_id=allocation.owner_node_id,
                owner_node_level=allocation.owner_node.level,
                quantity_kg=allocation.quantity_kg,
            )
            for allocation in pending
        ]

    @classmethod
    def is_complete(cls, cycle) -> bool:
        return not cls.stuck_allocations(cycle)
