from dataclasses import dataclass

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.models import AuditLogEntry
from apps.catalog.models import ProductGroup, ProductSubgroup
from apps.cycles.models import Cycle
from apps.hierarchy.models import HierarchyNode
from apps.sales_history.provider import SalesHistoryProvider

from .models import GoalAllocation
from .strategies import (
    GroupSuggestion,
    LargestRemainderRoundingPolicy,
    MonthlyQuantity,
    SeasonalTrendDistributionStrategy,
    SeasonalTrendSuggestionStrategy,
    StrategyNotConfiguredError,
    default_distribution_registry,
)


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
    def detect_and_reassign_if_needed(
        previous: HierarchyNode | None, node: HierarchyNode, changed_by
    ) -> list[GoalAllocation]:
        """Compara o estado anterior (buscado do banco antes de salvar) com o novo e dispara a
        reatribuição só na transição real (ativo True->False, ou parent_id mudou) — criação de nó
        novo ou edição de outros campos não dispara nada. Chamado tanto pelo Django Admin
        (`HierarchyNodeAdmin.save_model`) quanto pela API de CRUD da SPA — dois pontos de entrada
        que editam hierarquia agora (Decisão 4 revista), então a checagem fica centralizada aqui
        em vez de duplicada em cada um."""
        if previous is None:
            return []

        was_deactivated = previous.ativo and not node.ativo
        was_reparented = previous.parent_id != node.parent_id
        if not (was_deactivated or was_reparented):
            return []

        return HierarchyChangeReassignmentService.reassign_open_cycle_allocations(node, changed_by=changed_by)

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


@dataclass(frozen=True)
class VendedorAllocationRow:
    regional_nome: str
    local_nome: str
    supervisor_nome: str
    vendedor_nome: str
    grupo_nome: str
    subgrupo_nome: str
    quantity_kg: int
    status: str  # "META" ou "META AJUSTADA"


class VendedorAllocationReportService:
    """Achata a árvore de alocações do ciclo até a folha (Vendedor, sempre SUBGROUP — O1) numa
    linha por alocação, com o caminho completo até Coordenador Regional. Fonte única tanto da
    tela de Metas quanto do CSV de exportação.

    Status "META" vs "META AJUSTADA": não é um campo novo no modelo — é derivado de H4
    (reabertura). Se a alocação em si ou qualquer ancestral na cadeia (`parent_allocation`) já
    foi reaberta neste ciclo (`AuditLogEntry.Action.REABERTURA`), a versão atual é fruto de um
    redo (ex.: Supervisor corrigindo por quebra de estoque no fim do mês) — "META AJUSTADA".
    Sem redo registrado, é a distribuição original — "META". Reaproveita o mecanismo já aprovado
    de reabrir/redistribuir em vez de inventar um novo campo/fluxo de ajuste.
    """

    @staticmethod
    def rows_for_cycle(cycle) -> list[VendedorAllocationRow]:
        allocations = list(
            GoalAllocation.objects.filter(cycle=cycle).select_related(
                "owner_node__parent__parent__parent", "subgroup__group"
            )
        )
        by_id = {allocation.id: allocation for allocation in allocations}

        reopened_ids = set(
            AuditLogEntry.objects.filter(
                content_type=ContentType.objects.get_for_model(GoalAllocation),
                object_id__in=by_id.keys(),
                action=AuditLogEntry.Action.REABERTURA,
            ).values_list("object_id", flat=True)
        )

        rows = []
        for allocation in allocations:
            if allocation.owner_node.level != HierarchyNode.Level.VENDEDOR:
                continue

            adjusted = False
            current = allocation
            while current is not None:
                if current.id in reopened_ids:
                    adjusted = True
                    break
                current = by_id.get(current.parent_allocation_id)

            supervisor = allocation.owner_node.parent
            local = supervisor.parent if supervisor else None
            regional = local.parent if local else None

            rows.append(
                VendedorAllocationRow(
                    regional_nome=regional.nome if regional else "",
                    local_nome=local.nome if local else "",
                    supervisor_nome=supervisor.nome if supervisor else "",
                    vendedor_nome=allocation.owner_node.nome,
                    grupo_nome=allocation.subgroup.group.nome if allocation.subgroup_id else "",
                    subgrupo_nome=allocation.subgroup.nome if allocation.subgroup_id else "",
                    quantity_kg=allocation.quantity_kg,
                    status="META AJUSTADA" if adjusted else "META",
                )
            )
        return rows


def previous_month(ano: int, mes: int) -> tuple[int, int]:
    """Mês imediatamente anterior a (ano, mes) — usado como `last_month` da janela de 12 meses
    de histórico do P1, de forma que a projeção (que olha um mês além do fim da janela) caia
    exatamente no mês do ciclo sendo planejado."""
    return (ano, mes - 1) if mes > 1 else (ano - 1, 12)


class GoalSuggestionService:
    """P1: sugestão automática por grupo pro Gerente, com breakdown auditável (tendência, índice
    sazonal, comparação com o mesmo mês do ano passado, aviso de lacuna no histórico) — ver
    Decisão 6 em docs/decisions.md. Só orquestra: a fórmula em si vive em `strategies.py`, os
    dados em `SalesHistoryProvider`."""

    PERIOD_MONTHS = 12

    @staticmethod
    def suggest_for_cycle(cycle: Cycle) -> dict[int, GroupSuggestion]:
        last_month = previous_month(cycle.ano, cycle.mes)
        group_ids = list(ProductGroup.objects.filter(ativo=True).values_list("id", flat=True))

        history_by_group = {
            group_id: SalesHistoryProvider.group_history(
                group_id, GoalSuggestionService.PERIOD_MONTHS, last_month
            )
            for group_id in group_ids
        }
        strategy = SeasonalTrendSuggestionStrategy(history_by_group)
        return strategy.suggest_detailed(group_ids, GoalSuggestionService.PERIOD_MONTHS)


@dataclass(frozen=True)
class ChildDistributionContext:
    """Contexto histórico de um alvo direto de uma alocação a distribuir — histórico de 12 meses,
    comparativos (mesmo mês ano passado, média últimos 3 meses) e participação, pra apoiar a
    decisão de quem está distribuindo manualmente (Gerente→Regional, Regional→Local, e agora
    também a Etapa 2 — Subgrupo→Supervisor — da quebra do Coordenador Local).

    `suggested_kg` só vem preenchido quando o nível de quem distribui tem fórmula AUTO ligada
    (GERENTE/REGIONAL/LOCAL/SUPERVISOR — ver `default_distribution_registry`); sem AUTO ligada
    fica None e a UI não mostra número pré-calculado nenhum, só o histórico/comparativos.
    """

    owner_node_id: int
    history: list[MonthlyQuantity]
    same_month_last_year_kg: float | None
    last_3_months_avg_kg: float | None
    historical_share_pct: float | None
    has_gap: bool
    suggested_kg: int | None


PERIOD_MONTHS = 12


def _build_child_distribution_contexts(
    *, owner_node: HierarchyNode, cycle: Cycle, group_id: int | None, total_kg: int
) -> list[ChildDistributionContext]:
    """Núcleo compartilhado entre `DistributionContextService` (Gerente→Regional, Regional→Local,
    e a distribuição "tudo de uma vez" pro nível LOCAL) e `SupervisorSplitContextService` (Etapa 2
    do wizard de subgrupo do Coordenador Local): pesa os filhos diretos de `owner_node` pelo
    histórico do GRUPO INTEIRO de cada um (nunca por subgrupo — Decisão 6, refinamento
    2026-07-21) e reparte `total_kg` entre eles via a `DistributionStrategy` AUTO do nível, se
    houver. `total_kg` é parametrizado porque a Etapa 2 reparte o valor de um subgrupo específico
    (ainda não salvo), não a meta inteira do grupo."""
    children_nodes = list(HierarchyNode.objects.filter(parent_id=owner_node.id, ativo=True))
    if not children_nodes or group_id is None:
        return []

    last_month = previous_month(cycle.ano, cycle.mes)
    history_by_target = {
        node.id: SalesHistoryProvider.target_history(
            node.id,
            PERIOD_MONTHS,
            last_month,
            group_id=group_id,
        )
        for node in children_nodes
    }

    total_12m_by_target = {
        node_id: sum(point.quantity_kg for point in history) for node_id, history in history_by_target.items()
    }
    grand_total = sum(total_12m_by_target.values())

    try:
        strategy = default_distribution_registry.resolve(
            owner_node.level, "AUTO", history_by_target=history_by_target
        )
        suggested_by_target = strategy.distribute(total_kg, [node.id for node in children_nodes])
    except StrategyNotConfiguredError:
        suggested_by_target = {}
    except ValueError:
        # Nenhum alvo tem histórico (ex.: ExternalSalespersonMapping ainda sem curadoria, ver
        # O3 em docs/open-questions.md) — a proporção soma zero e a fórmula não tem base pra
        # sugerir nada. Degrada pra "sem sugestão", igual a nível sem AUTO configurada, em vez
        # de derrubar o endpoint.
        suggested_by_target = {}

    result = []
    for node in children_nodes:
        history = history_by_target[node.id]
        last_3_months = history[-3:] if len(history) >= 3 else history
        result.append(
            ChildDistributionContext(
                owner_node_id=node.id,
                history=history,
                same_month_last_year_kg=(history[0].quantity_kg if len(history) == PERIOD_MONTHS else None),
                last_3_months_avg_kg=(
                    sum(point.quantity_kg for point in last_3_months) / len(last_3_months)
                    if last_3_months
                    else None
                ),
                historical_share_pct=(
                    total_12m_by_target[node.id] / grand_total * 100 if grand_total > 0 else None
                ),
                has_gap=any(point.quantity_kg == 0 for point in history),
                suggested_kg=suggested_by_target.get(node.id),
            )
        )
    return result


class DistributionContextService:
    """Monta o `ChildDistributionContext` de cada filho direto do nó que está distribuindo,
    reaproveitando `SalesHistoryProvider.target_history` (mesma fonte de P2-P4) e, quando
    aplicável, a `DistributionStrategy` AUTO já aprovada para o nível — nunca inventa fórmula
    nova aqui, só orquestra o que já existe em `strategies.py`.

    Funciona tanto pra alocação GROUP (Gerente→Regional, Regional→Local) quanto SUBGROUP — a
    tela "Meta Supervisor" chama isso numa alocação SUBGROUP já persistida (dona = Coordenador
    Local, criada por `SplitGroupIntoSubgroupsService`), e o peso continua vindo do histórico do
    GRUPO inteiro do Supervisor (resolvido via `subgroup.group_id`), nunca do subgrupo específico
    — mesma regra da Decisão 6, só que a granularidade da alocação-pai agora pode ser mais fina.
    """

    PERIOD_MONTHS = PERIOD_MONTHS

    @staticmethod
    def build(allocation: GoalAllocation) -> list[ChildDistributionContext]:
        group_id = allocation.group_id
        if group_id is None and allocation.subgroup_id is not None:
            group_id = allocation.subgroup.group_id

        return _build_child_distribution_contexts(
            owner_node=allocation.owner_node,
            cycle=allocation.cycle,
            group_id=group_id,
            total_kg=allocation.quantity_kg,
        )


@dataclass(frozen=True)
class SubgroupDistributionContext:
    """Contexto histórico de um subgrupo de uma meta GROUP que o Coordenador Local está quebrando
    em subgrupos (Etapa 1 do wizard novo) — mesma forma de `ChildDistributionContext`, mas
    chaveado por subgrupo em vez de nó, porque aqui os "alvos" são categorias de produto, não
    posições da hierarquia."""

    subgroup_id: int
    subgroup_nome: str
    history: list[MonthlyQuantity]
    same_month_last_year_kg: float | None
    last_3_months_avg_kg: float | None
    historical_share_pct: float | None
    has_gap: bool
    suggested_kg: int | None


class SubgroupDistributionContextService:
    """Etapa 1 do wizard de quebra do Coordenador Local: sugere quanto cada SUBGRUPO recebe da
    meta GROUP recebida pelo nó LOCAL, pesando pelo histórico de vendas de cada subgrupo dentro
    do próprio escopo (sub-árvore) daquele nó — análogo a P1 (sugestão por grupo pro Gerente), um
    nível mais fundo. Fórmula confirmada explicitamente pelo usuário (golden rule do CLAUDE.md):
    ao contrário do peso entre ALVOS/nós em P2-P4 (que nunca usa histórico de subgrupo, por ser
    esparso demais por nó), aqui a comparação é entre SUBGRUPOS dentro do mesmo nó, com volume
    agregado equivalente ao de P1 — não weight entre nós, então a mesma fragilidade não se aplica.
    """

    PERIOD_MONTHS = PERIOD_MONTHS

    @staticmethod
    def build(allocation: GoalAllocation) -> list[SubgroupDistributionContext]:
        if allocation.group_id is None:
            return []

        subgroups = list(ProductSubgroup.objects.filter(group_id=allocation.group_id, ativo=True))
        if not subgroups:
            return []

        last_month = previous_month(allocation.cycle.ano, allocation.cycle.mes)
        history_by_subgroup = {
            subgroup.id: SalesHistoryProvider.target_history(
                allocation.owner_node_id,
                SubgroupDistributionContextService.PERIOD_MONTHS,
                last_month,
                group_id=allocation.group_id,
                subgroup_id=subgroup.id,
            )
            for subgroup in subgroups
        }

        total_12m_by_subgroup = {
            subgroup_id: sum(point.quantity_kg for point in history)
            for subgroup_id, history in history_by_subgroup.items()
        }
        grand_total = sum(total_12m_by_subgroup.values())

        try:
            strategy = SeasonalTrendDistributionStrategy(
                history_by_subgroup, LargestRemainderRoundingPolicy()
            )
            suggested_by_subgroup = strategy.distribute(allocation.quantity_kg, [sg.id for sg in subgroups])
        except ValueError:
            suggested_by_subgroup = {}

        result = []
        for subgroup in subgroups:
            history = history_by_subgroup[subgroup.id]
            last_3_months = history[-3:] if len(history) >= 3 else history
            result.append(
                SubgroupDistributionContext(
                    subgroup_id=subgroup.id,
                    subgroup_nome=subgroup.nome,
                    history=history,
                    same_month_last_year_kg=(
                        history[0].quantity_kg
                        if len(history) == SubgroupDistributionContextService.PERIOD_MONTHS
                        else None
                    ),
                    last_3_months_avg_kg=(
                        sum(point.quantity_kg for point in last_3_months) / len(last_3_months)
                        if last_3_months
                        else None
                    ),
                    historical_share_pct=(
                        total_12m_by_subgroup[subgroup.id] / grand_total * 100 if grand_total > 0 else None
                    ),
                    has_gap=any(point.quantity_kg == 0 for point in history),
                    suggested_kg=suggested_by_subgroup.get(subgroup.id),
                )
            )
        return result


@dataclass(frozen=True)
class SubgroupSplitSpec:
    subgroup_id: int
    quantity_kg: int


class SplitGroupIntoSubgroupsService:
    """Tela "Distribuir Produtos": o Coordenador Local quebra a meta GROUP recebida em metas
    SUBGROUP, permanecendo dono do mesmo nó — não é um repasse pra outro nível da hierarquia (isso
    só acontece depois, na tela "Meta Supervisor", via `DistributeGoalService` normal), por isso
    não passa pela checagem de nó-filho direto de `DistributeGoalService.distribute()`. Reaproveita
    o mesmo `ClosureValidator` — a invariante de fechamento exato não muda, só quem é o dono das
    alocações filhas."""

    @staticmethod
    @transaction.atomic
    def split(parent: GoalAllocation, specs: list[SubgroupSplitSpec], criado_por) -> list[GoalAllocation]:
        if parent.distributed:
            raise AllocationClosureError("Esta alocação já foi distribuída.")

        if not criado_por.hierarchy_nodes.filter(id=parent.owner_node_id).exists():
            raise AllocationScopeError("Você só pode distribuir uma alocação que possui.")

        if (
            parent.owner_node.level != HierarchyNode.Level.LOCAL
            or parent.granularity != GoalAllocation.Granularity.GROUP
        ):
            raise AllocationScopeError(
                "Só é possível quebrar em subgrupos uma meta de grupo do Coordenador Local."
            )

        subgroup_ids = [spec.subgroup_id for spec in specs]
        subgroups_by_id = {sg.id: sg for sg in ProductSubgroup.objects.filter(id__in=subgroup_ids)}
        missing = set(subgroup_ids) - set(subgroups_by_id)
        if missing:
            raise AllocationScopeError(f"Subgrupo(s) inexistente(s): {sorted(missing)}.")
        wrong_group = [sg.id for sg in subgroups_by_id.values() if sg.group_id != parent.group_id]
        if wrong_group:
            raise AllocationScopeError("Todo subgrupo precisa pertencer ao grupo desta alocação.")

        ClosureValidator.validate(parent.quantity_kg, [spec.quantity_kg for spec in specs])

        created = [
            GoalAllocation(
                cycle=parent.cycle,
                owner_node=parent.owner_node,
                parent_allocation=parent,
                granularity=GoalAllocation.Granularity.SUBGROUP,
                subgroup_id=spec.subgroup_id,
                quantity_kg=spec.quantity_kg,
                criado_por=criado_por,
            )
            for spec in specs
        ]
        for allocation in created:
            allocation.full_clean()
            allocation.save()

        parent.distributed = True
        parent.save(update_fields=["distributed", "updated_at"])

        return created


class CreateRootAllocationError(ValidationError):
    """Falha ao criar a meta raiz (nível Gerente, sem alocação-pai)."""


class CreateRootAllocationService:
    """Cria a alocação raiz de um ciclo (nível Gerente, `parent_allocation=None`) — o ponto de
    partida da cascata, que hoje só existia via Django Admin/seed. A sugestão P1 pré-preenche o
    `quantity_kg` no frontend, mas o valor final sempre vem do usuário (revisável, nunca
    auto-persistido — ver [[project_goal-suggestion-workflow]])."""

    @staticmethod
    @transaction.atomic
    def create(
        *,
        cycle: Cycle,
        owner_node: HierarchyNode,
        granularity: str,
        quantity_kg: int,
        criado_por,
        group_id: int | None = None,
        subgroup_id: int | None = None,
        product_id: int | None = None,
    ) -> GoalAllocation:
        if not criado_por.hierarchy_nodes.filter(id=owner_node.id).exists():
            raise AllocationScopeError("Você só pode criar meta para um nó que possui.")
        if owner_node.level != HierarchyNode.Level.GERENTE or owner_node.parent_id is not None:
            raise AllocationScopeError(
                "A meta raiz só pode ser criada para um nó Gerente, no topo da hierarquia."
            )

        duplicate = GoalAllocation.objects.filter(
            cycle=cycle,
            owner_node=owner_node,
            parent_allocation__isnull=True,
            granularity=granularity,
            group_id=group_id,
            subgroup_id=subgroup_id,
            product_id=product_id,
        ).exists()
        if duplicate:
            raise CreateRootAllocationError(
                "Já existe uma meta raiz para esse grupo/subgrupo/produto neste ciclo."
            )

        allocation = GoalAllocation(
            cycle=cycle,
            owner_node=owner_node,
            parent_allocation=None,
            granularity=granularity,
            group_id=group_id,
            subgroup_id=subgroup_id,
            product_id=product_id,
            quantity_kg=quantity_kg,
            criado_por=criado_por,
        )
        allocation.full_clean()
        allocation.save()
        return allocation
