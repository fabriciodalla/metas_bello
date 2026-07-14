"""Pontos de extensão plugáveis para as fórmulas de cálculo.

Todas as 5 pendências têm fórmula aprovada pelo usuário: P1-P4 (docs/decisions.md, Decisão 6) são
decomposição clássica tendência + sazonalidade sobre 12 meses de histórico; P5 (docs/decisions.md,
Decisão 7) é o método do maior resto / Hamilton. Nenhuma fórmula fica hardcoded no fluxo de
distribuição (DistributeGoalService só recebe quantidades já calculadas) — seguem plugáveis por
design, caso alguma precise ser revista.
"""

from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass


class DistributionStrategy(ABC):
    """Decide como um total_kg inteiro é dividido entre os alvos diretos de um nível.

    Cobre distribuição Regional→Local (P2), quebra Grupo→Subgrupo (P3) e distribuição
    Supervisor→Vendedor (P4). `context` é o ponto de extensão para dados auxiliares (ex.:
    histórico de vendas via SalesHistoryProvider, quando este existir).
    """

    @abstractmethod
    def distribute(self, total_kg: int, target_ids: list[int], context: dict | None = None) -> dict[int, int]:
        """Retorna {target_id: quantidade_kg}. A soma exata é checada pelo ClosureValidator, a jusante."""


class ManualDistributionStrategy(DistributionStrategy):
    """Modo manual: o usuário fornece os valores diretamente.

    Não é uma fórmula em disputa — é o modo explícito descrito no brief. Passa pelo mesmo
    ClosureValidator que qualquer estratégia automática.
    """

    def __init__(self, quantities_by_target: dict[int, int]):
        self._quantities_by_target = quantities_by_target

    def distribute(self, total_kg: int, target_ids: list[int], context: dict | None = None) -> dict[int, int]:
        missing = set(target_ids) - set(self._quantities_by_target)
        if missing:
            raise ValueError(f"Faltam quantidades manuais para os alvos: {sorted(missing)}")
        return {target_id: self._quantities_by_target[target_id] for target_id in target_ids}


class SuggestionStrategy(ABC):
    """Sugestão automática de metas por grupo para o Gerente, a partir do histórico (P1, H2)."""

    @abstractmethod
    def suggest(self, group_ids: list[int], period_months: int) -> dict[int, int]:
        """Retorna {group_id: quantidade_kg sugerida}. Nenhuma fórmula está aprovada ainda."""


@dataclass(frozen=True)
class MonthlyQuantity:
    """Um ponto de histórico: quanto foi vendido/distribuído num (ano, mês) específico.

    Precisa do (ano, mes) explícito, não só uma lista de valores em ordem — o índice sazonal
    depende de saber a qual mês do calendário cada ponto pertence.
    """

    ano: int
    mes: int
    quantity_kg: float


def _linear_trend(values: list[float]) -> tuple[float, float]:
    """Regressão linear simples (mínimos quadrados) sobre os índices 1..N. Retorna (intercepto, inclinação).

    Método fechado (sem iteração/otimização) — auditável, não é machine learning.
    """
    n = len(values)
    if n < 2:
        raise ValueError("São necessários ao menos 2 meses de histórico para calcular a tendência.")

    xs = list(range(1, n + 1))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values))
    denominator = sum((x - mean_x) ** 2 for x in xs)
    slope = numerator / denominator if denominator else 0.0
    intercept = mean_y - slope * mean_x
    return intercept, slope


def _seasonal_trend_forecast(history: list[MonthlyQuantity]) -> float:
    """Decomposição clássica multiplicativa: tendência linear × índice sazonal do mês, projetando
    um mês à frente do fim do histórico.

    Fórmula aprovada pelo usuário para P1-P4 (docs/decisions.md, Decisão 6 revisada). Requer
    histórico ordenado cronologicamente (mais antigo primeiro).

    Limitação conhecida e aceita: com só 12 meses (1 ano), cada índice sazonal por mês do
    calendário vem de uma única observação — não distingue padrão sazonal real de um evento
    pontual naquele mês específico. Ficaria mais robusto com 24-36 meses (múltiplas observações
    por mês), mas o usuário confirmou operar com a janela de 12 meses disponível.
    """
    if not history:
        raise ValueError("Não há histórico suficiente para calcular a projeção.")

    values = [entry.quantity_kg for entry in history]
    intercept, slope = _linear_trend(values)

    def trend_at(index: int) -> float:
        return intercept + slope * index

    seasonal_ratios: dict[int, list[float]] = defaultdict(list)
    for i, entry in enumerate(history, start=1):
        trend_value = trend_at(i)
        if trend_value > 0:
            seasonal_ratios[entry.mes].append(entry.quantity_kg / trend_value)

    seasonal_index_by_month = {mes: sum(ratios) / len(ratios) for mes, ratios in seasonal_ratios.items()}
    if seasonal_index_by_month:
        average_index = sum(seasonal_index_by_month.values()) / len(seasonal_index_by_month)
        if average_index > 0:
            seasonal_index_by_month = {
                mes: index / average_index for mes, index in seasonal_index_by_month.items()
            }

    last_entry = history[-1]
    next_month = last_entry.mes + 1 if last_entry.mes < 12 else 1

    trend_forecast = trend_at(len(history) + 1)
    seasonal_factor = seasonal_index_by_month.get(next_month, 1.0)
    return max(trend_forecast * seasonal_factor, 0.0)


class SeasonalTrendSuggestionStrategy(SuggestionStrategy):
    """P1 aprovada (Decisão 6 revisada): tendência linear + índice sazonal por mês do calendário,
    sobre uma janela de 12 meses, projetando o próximo mês.

    Consome uma série já resolvida por `ProductGroup.id` (mais antigo primeiro) — a extração a
    partir de `DistributionBaseline` (que só tem `subgroup_name` em texto) segue bloqueada até O3
    (mapeamento subgroup_name -> ProductGroup) ser resolvida; ver docs/open-questions.md.
    """

    def __init__(self, history_by_group: dict[int, list[MonthlyQuantity]]):
        self._history_by_group = history_by_group

    def suggest(self, group_ids: list[int], period_months: int) -> dict[int, int]:
        result = {}
        for group_id in group_ids:
            history = self._history_by_group.get(group_id, [])[-period_months:]
            result[group_id] = round(_seasonal_trend_forecast(history))
        return result


class RoundingPolicy(ABC):
    """Transforma proporções fracionárias em KG inteiro e aloca o resto para fechar exatamente (P5).

    É o núcleo do conflito "fração natural vs. inteiro exato".
    """

    @abstractmethod
    def round_to_close(self, total_kg: int, proportions_by_target: dict[int, float]) -> dict[int, int]:
        """Retorna {target_id: quantidade_kg inteira}, com soma == total_kg."""


class LargestRemainderRoundingPolicy(RoundingPolicy):
    """P5 aprovada (método do maior resto / Hamilton, ver docs/decisions.md, Decisão 7).

    Arredonda toda proporção para baixo, depois distribui o KG restante, um de cada vez, para
    quem tem a maior fração perdida no arredondamento. Método clássico de alocação (usado em
    apuração de cadeiras parlamentares), auditável linha a linha.
    """

    def round_to_close(self, total_kg: int, proportions_by_target: dict[int, float]) -> dict[int, int]:
        if not proportions_by_target:
            raise ValueError("proportions_by_target não pode ser vazio.")

        total_proportion = sum(proportions_by_target.values())
        if total_proportion <= 0:
            raise ValueError("A soma das proporções deve ser positiva.")

        exact_shares = {
            target_id: total_kg * proportion / total_proportion
            for target_id, proportion in proportions_by_target.items()
        }
        result = {target_id: int(share) for target_id, share in exact_shares.items()}
        remainder = total_kg - sum(result.values())

        by_largest_fraction = sorted(
            exact_shares.items(), key=lambda item: item[1] - result[item[0]], reverse=True
        )
        for target_id, _fraction in by_largest_fraction[:remainder]:
            result[target_id] += 1

        return result


class SeasonalTrendDistributionStrategy(DistributionStrategy):
    """P2-P4 aprovada (Decisão 6 revisada): reparte total_kg entre os alvos proporcionalmente à
    projeção de tendência + sazonalidade do histórico de cada um, fechando em KG inteiro via
    `RoundingPolicy` plugável (P5 continua não-aprovada — o placeholder é só o default, não fica
    hardcoded aqui).

    Consome uma série já resolvida por alvo (`HierarchyNode.id`) — a extração a partir de
    `DistributionBaseline` (que só tem `salesperson_name` em texto) segue bloqueada até O3/O5
    (mapeamento salesperson_name/nk_vendedor -> HierarchyNode) ser resolvida.
    """

    def __init__(self, history_by_target: dict[int, list[MonthlyQuantity]], rounding_policy: RoundingPolicy):
        self._history_by_target = history_by_target
        self._rounding_policy = rounding_policy

    def distribute(self, total_kg: int, target_ids: list[int], context: dict | None = None) -> dict[int, int]:
        proportions = {}
        for target_id in target_ids:
            history = self._history_by_target.get(target_id, [])
            proportions[target_id] = _seasonal_trend_forecast(history) if history else 0.0

        return self._rounding_policy.round_to_close(total_kg, proportions)


@dataclass(frozen=True)
class StrategyKey:
    level: str
    mode: str  # "AUTO" ou "MANUAL"


class StrategyNotConfiguredError(Exception):
    """A fórmula automática para este nível/modo ainda não foi definida pelo usuário (ver P1-P4)."""


class DistributionStrategyRegistry:
    """Seleciona a DistributionStrategy por nível hierárquico e modo (automático/manual).

    Só o modo manual vem registrado por padrão: nenhuma fórmula automática (P2-P4) está
    aprovada. Resolver "AUTO" para qualquer nível levanta StrategyNotConfiguredError.
    """

    def __init__(self):
        self._factories: dict[StrategyKey, object] = {}

    def register(self, level: str, mode: str, factory) -> None:
        self._factories[StrategyKey(level, mode)] = factory

    def resolve(self, level: str, mode: str, **kwargs) -> DistributionStrategy:
        factory = self._factories.get(StrategyKey(level, mode))
        if factory is None:
            raise StrategyNotConfiguredError(f"Nenhuma estratégia registrada para nível={level} modo={mode}.")
        return factory(**kwargs)


def _build_default_registry() -> DistributionStrategyRegistry:
    registry = DistributionStrategyRegistry()
    for level in ("GERENTE", "REGIONAL", "LOCAL", "SUPERVISOR"):
        registry.register(
            level,
            "MANUAL",
            lambda quantities_by_target: ManualDistributionStrategy(quantities_by_target),
        )
    # AUTO cobre só P2 (Regional->Local), P3 (quebra Local->Supervisor) e P4 (Supervisor->Vendedor)
    # — Gerente->Regional não é uma das pendências nomeadas em open-questions.md, então não tem AUTO.
    for level in ("REGIONAL", "LOCAL", "SUPERVISOR"):
        registry.register(
            level,
            "AUTO",
            lambda history_by_target, rounding_policy=None: SeasonalTrendDistributionStrategy(
                history_by_target, rounding_policy or LargestRemainderRoundingPolicy()
            ),
        )
    return registry


default_distribution_registry = _build_default_registry()
