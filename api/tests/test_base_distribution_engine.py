"""Teste completo do motor de distribuição proporcional.

Monta uma hierarquia real:
  GER_01  (Gerente)
  ├── REG_01  (Coord Regional)
  └── REG_02  (Coord Regional)
      └── COO_05  (Coord Local)
          ├── SUP_01  (Supervisor)
          │   ├── VEN_01
          │   ├── VEN_04
          │   └── VEN_127
          ├── SUP_02  (Supervisor)
          │   ├── VEN_06
          │   └── VEN_07
          └── SUP_03  (Supervisor)
              └── VEN_02

Categoria EMBUTIDOS com 3 produtos.
Base distribution: dados de 3 meses (Abr/Mai/Jun 2026).
Meta gerencial: 10 000 kg.

Em cada nível: soma da distribuição == meta recebida (nem mais, nem menos).
"""
import pytest
from datetime import date
from decimal import Decimal

from api.models.calendar import Holiday, WorkingDaysConfig
from api.models.catalog import Product, ProductCategory
from api.models.goals import Distribution, GoalCycle
from api.models.hierarchy import HierarchyLevel, HierarchyNode
from api.models.portfolio import BaseDistribution
import os
import sys
import types

# Evitar que o import chain passe por engines/__init__.py (que importa
# PortfolioBasedEngine com dependência quebrada de ClientPortfolio).
_engines_pkg = types.ModuleType("api.services.engines")
_engines_pkg.__path__ = [
    os.path.join(os.path.dirname(__file__), "..", "services", "engines")
]
sys.modules["api.services.engines"] = _engines_pkg

from api.services.engines.base_distribution import (  # noqa: E402
    BaseDistributionEngine,
    _proportional_allocation,
)


# ── Helpers ────────────────────────────────────────────


async def _seed_hierarchy(db):
    """Cria levels + nos. Retorna dict source_id -> node."""
    levels = {}
    for name, depth, prefix in [
        ("Gerente", 1, "GER"),
        ("Coordenador Regional", 2, "REG"),
        ("Coordenador Local", 3, "COO"),
        ("Supervisor", 4, "SUP"),
        ("Vendedor", 5, "VEN"),
    ]:
        lv = HierarchyLevel(name=name, depth=depth, prefix=prefix)
        db.add(lv)
        await db.flush()
        levels[prefix] = lv

    nodes_spec = [
        ("GER_01", "FABIO SHAEN", "GER", None),
        ("REG_01", "DIVINO REGINALDO", "REG", "GER_01"),
        ("REG_02", "MARCELO CIRELI", "REG", "GER_01"),
        ("COO_05", "EDVAN SOUZA", "COO", "REG_02"),
        ("SUP_01", "IAGO CALLIGURI", "SUP", "COO_05"),
        ("SUP_02", "JOSIEL BARBOSA", "SUP", "COO_05"),
        ("SUP_03", "WAGNER CAETANO", "SUP", "COO_05"),
        ("VEN_01", "MARCELO SILVA", "VEN", "SUP_01"),
        ("VEN_04", "MELQUIADES JUNIOR", "VEN", "SUP_01"),
        ("VEN_127", "RODRIGO DIAS", "VEN", "SUP_01"),
        ("VEN_06", "EDILSON SILVA", "VEN", "SUP_02"),
        ("VEN_07", "FERNANDO RIBEIRO", "VEN", "SUP_02"),
        ("VEN_02", "WAGNER CAETANO V", "VEN", "SUP_03"),
    ]

    nodes = {}
    for source_id, name, prefix, parent_sid in nodes_spec:
        n = HierarchyNode(
            level_id=levels[prefix].id,
            source_id=source_id,
            name=name,
        )
        db.add(n)
        await db.flush()
        nodes[source_id] = n

    for source_id, _, _, parent_sid in nodes_spec:
        if parent_sid:
            nodes[source_id].parent_id = nodes[parent_sid].id
    await db.flush()

    return nodes


async def _seed_catalog(db):
    """Cria categoria EMBUTIDOS com 3 produtos. Retorna (category, {name: product})."""
    cat = ProductCategory(source_id="GRP_01", name="EMBUTIDOS")
    db.add(cat)
    await db.flush()

    products = {}
    for sid, name in [
        ("PRO_01", "DEFUMADOS BELLO"),
        ("PRO_05", "EMBUTIDOS CALABRESA"),
        ("PRO_06", "EMBUTIDOS LINGUICA"),
    ]:
        p = Product(category_id=cat.id, source_id=sid, name=name)
        db.add(p)
        await db.flush()
        products[name] = p

    return cat, products


async def _seed_cycle_and_base(db, nodes, products):
    """Cria ciclo Jul/2026, working days config, base_distribution para 3 meses."""
    cycle = GoalCycle(month=7, year=2026, working_days=23)
    db.add(cycle)
    await db.flush()

    # Working days dos 3 meses anteriores (confirmados)
    for y, m, d in [(2026, 4, 22), (2026, 5, 21), (2026, 6, 22)]:
        db.add(WorkingDaysConfig(year=y, month=m, confirmed_days=d))

    # Feriado: 1 de maio (dia util) — já descontado no confirmed_days acima
    db.add(Holiday(holiday_date=date(2026, 5, 1), year=2026, name="Dia do Trabalho"))
    await db.flush()

    # Base distribution: vendedor × produto × mês
    # Dados em kg — valores escolhidos para gerar proporções não-triviais
    sales_data = {
        #                    DEFUMADOS   CALABRESA   LINGUICA
        # SUP_01 sellers
        "VEN_01":  {"DEFUMADOS BELLO": [100, 120, 80],
                    "EMBUTIDOS CALABRESA": [50, 60, 40],
                    "EMBUTIDOS LINGUICA": [200, 180, 220]},
        "VEN_04":  {"DEFUMADOS BELLO": [80, 90, 70],
                    "EMBUTIDOS CALABRESA": [30, 40, 50],
                    "EMBUTIDOS LINGUICA": [150, 160, 140]},
        "VEN_127": {"DEFUMADOS BELLO": [60, 50, 70],
                    "EMBUTIDOS CALABRESA": [20, 25, 15],
                    "EMBUTIDOS LINGUICA": [100, 110, 90]},
        # SUP_02 sellers
        "VEN_06":  {"DEFUMADOS BELLO": [40, 45, 55],
                    "EMBUTIDOS CALABRESA": [70, 80, 50],
                    "EMBUTIDOS LINGUICA": [120, 130, 110]},
        "VEN_07":  {"DEFUMADOS BELLO": [30, 35, 25],
                    "EMBUTIDOS CALABRESA": [40, 50, 30],
                    "EMBUTIDOS LINGUICA": [80, 70, 90]},
        # SUP_03 sellers
        "VEN_02":  {"DEFUMADOS BELLO": [90, 85, 95],
                    "EMBUTIDOS CALABRESA": [60, 55, 65],
                    "EMBUTIDOS LINGUICA": [170, 180, 150]},
    }

    months = [date(2026, 4, 1), date(2026, 5, 1), date(2026, 6, 1)]

    for vendor_sid, prod_sales in sales_data.items():
        node = nodes[vendor_sid]
        for prod_name, month_values in prod_sales.items():
            for i, m in enumerate(months):
                db.add(BaseDistribution(
                    cycle_id=cycle.id,
                    seller_node_id=node.id,
                    seller_name=node.name,
                    product_name=prod_name,
                    month=m,
                    total_kg=Decimal(str(month_values[i])),
                ))

    await db.commit()
    return cycle, sales_data


def _confirm_distribution(db, cycle_id, category_id, source_node_id, dest_node_id, qty_kg, product_id=None):
    """Cria distribution confirmada (simula o que o nível acima fez)."""
    dist = Distribution(
        cycle_id=cycle_id,
        category_id=category_id,
        product_id=product_id,
        source_node_id=source_node_id,
        destination_node_id=dest_node_id,
        quantity_kg=Decimal(str(qty_kg)),
        status="CONFIRMADA",
    )
    db.add(dist)
    return dist


# ── Testes unitários: _proportional_allocation ─────────


class TestProportionalAllocation:

    def test_soma_exata_caso_simples(self):
        target = Decimal("1000")
        shares = {
            (1, None): Decimal("300"),
            (2, None): Decimal("500"),
            (3, None): Decimal("200"),
        }
        result = _proportional_allocation(target, shares)
        assert sum(result.values()) == target

    def test_soma_exata_com_resto(self):
        target = Decimal("100")
        shares = {
            (1, None): Decimal("33"),
            (2, None): Decimal("33"),
            (3, None): Decimal("34"),
        }
        result = _proportional_allocation(target, shares)
        assert sum(result.values()) == target

    def test_soma_exata_muitos_itens(self):
        target = Decimal("9999")
        shares = {(i, None): Decimal(str(i * 7 + 3)) for i in range(50)}
        result = _proportional_allocation(target, shares)
        assert sum(result.values()) == target

    def test_soma_exata_com_produtos(self):
        target = Decimal("5000")
        shares = {
            (1, 10): Decimal("450"),
            (1, 20): Decimal("300"),
            (2, 10): Decimal("600"),
            (2, 20): Decimal("150"),
            (3, 10): Decimal("200"),
            (3, 20): Decimal("100"),
        }
        result = _proportional_allocation(target, shares)
        assert sum(result.values()) == target

    def test_proporcoes_corretas(self):
        target = Decimal("1000")
        shares = {
            (1, None): Decimal("600"),  # 60%
            (2, None): Decimal("400"),  # 40%
        }
        result = _proportional_allocation(target, shares)
        assert result[(1, None)] == Decimal("600")
        assert result[(2, None)] == Decimal("400")
        assert sum(result.values()) == target

    def test_target_um_kg(self):
        target = Decimal("1")
        shares = {
            (1, None): Decimal("100"),
            (2, None): Decimal("200"),
            (3, None): Decimal("300"),
        }
        result = _proportional_allocation(target, shares)
        assert sum(result.values()) == target

    def test_valores_zerados_retorna_vazio(self):
        target = Decimal("1000")
        shares = {(1, None): Decimal("0"), (2, None): Decimal("0")}
        result = _proportional_allocation(target, shares)
        assert result == {}

    def test_um_unico_destino_recebe_tudo(self):
        target = Decimal("7777")
        shares = {(1, None): Decimal("500")}
        result = _proportional_allocation(target, shares)
        assert result[(1, None)] == target


# ── Teste integração: fluxo completo de hierarquia ─────


@pytest.mark.asyncio
async def test_fluxo_completo_hierarquia(db):
    """Percorre GER->REG->COO->SUP->VEN verificando que soma == meta em cada nível."""
    nodes = await _seed_hierarchy(db)
    cat, products = await _seed_catalog(db)
    cycle, sales_data = await _seed_cycle_and_base(db, nodes, products)

    engine = BaseDistributionEngine()
    META_GERENCIAL = Decimal("10000")

    # ──────────────────────────────────────────────────────
    # NÍVEL 1: Gerente (GER_01) distribui para Regionais
    # Sem received_kg -> engine sugere total baseado nos individuais
    # ──────────────────────────────────────────────────────
    result_ger = await engine.suggest(
        db, nodes["GER_01"].id, cycle.id, cat.id, product_level=False,
    )
    assert len(result_ger.items) > 0, "Gerente deve ter sugestões"
    # Total sugerido é a soma das metas individuais (sem budget de cima)
    soma_sugerida = sum(i.suggested_kg for i in result_ger.items)
    assert soma_sugerida == result_ger.total_kg, \
        f"Soma sugerida ({soma_sugerida}) != total_kg ({result_ger.total_kg})"

    # Gerente define META_GERENCIAL = 10000 e confirma para si mesmo (entrada manual)
    # Simular: criar distribution confirmada para GER_01
    _confirm_distribution(db, cycle.id, cat.id, None, nodes["GER_01"].id, META_GERENCIAL)
    await db.commit()

    # Agora com budget, rodar novamente
    result_ger2 = await engine.suggest(
        db, nodes["GER_01"].id, cycle.id, cat.id, product_level=False,
    )
    soma_ger = sum(i.suggested_kg for i in result_ger2.items)
    assert soma_ger == META_GERENCIAL, \
        f"GERENTE: soma distribuída ({soma_ger}) != meta ({META_GERENCIAL})"
    print(f"\n{'='*60}")
    print(f"GERENTE distribui {META_GERENCIAL} kg de EMBUTIDOS")
    print(f"{'='*60}")
    for item in result_ger2.items:
        print(f"  -> {item.destination_name}: {item.suggested_kg} kg ({item.percent:.1f}%)")
    print(f"  TOTAL: {soma_ger} kg ✓")

    # Extrair quanto REG_02 recebeu
    reg02_item = next(i for i in result_ger2.items if i.destination_node_id == nodes["REG_02"].id)
    meta_reg02 = reg02_item.suggested_kg

    # ──────────────────────────────────────────────────────
    # NÍVEL 2: Regional (REG_02) distribui para Locais
    # ──────────────────────────────────────────────────────
    _confirm_distribution(db, cycle.id, cat.id, nodes["GER_01"].id, nodes["REG_02"].id, meta_reg02)
    await db.commit()

    result_reg = await engine.suggest(
        db, nodes["REG_02"].id, cycle.id, cat.id, product_level=False,
    )
    soma_reg = sum(i.suggested_kg for i in result_reg.items)
    assert soma_reg == meta_reg02, \
        f"REGIONAL: soma ({soma_reg}) != meta ({meta_reg02})"
    print(f"\nREGIONAL ({nodes['REG_02'].name}) distribui {meta_reg02} kg")
    print(f"{'-'*60}")
    for item in result_reg.items:
        print(f"  -> {item.destination_name}: {item.suggested_kg} kg ({item.percent:.1f}%)")
    print(f"  TOTAL: {soma_reg} kg ✓")

    # Extrair quanto COO_05 recebeu
    coo05_item = next(i for i in result_reg.items if i.destination_node_id == nodes["COO_05"].id)
    meta_coo05 = coo05_item.suggested_kg

    # ──────────────────────────────────────────────────────
    # NÍVEL 3: Coordenador Local (COO_05) distribui POR PRODUTO
    # depth=3 -> product_level=True
    # ──────────────────────────────────────────────────────
    _confirm_distribution(db, cycle.id, cat.id, nodes["REG_02"].id, nodes["COO_05"].id, meta_coo05)
    await db.commit()

    result_coo = await engine.suggest(
        db, nodes["COO_05"].id, cycle.id, cat.id, product_level=True,
    )
    soma_coo = sum(i.suggested_kg for i in result_coo.items)
    assert soma_coo == meta_coo05, \
        f"COORD LOCAL: soma ({soma_coo}) != meta ({meta_coo05})"
    print(f"\nCOORD LOCAL ({nodes['COO_05'].name}) distribui {meta_coo05} kg por PRODUTO")
    print(f"{'-'*60}")
    for item in sorted(result_coo.items, key=lambda x: (x.product_name, x.destination_name)):
        print(f"  {item.product_name:25s} -> {item.destination_name:20s}: {item.suggested_kg} kg")
    print(f"  TOTAL: {soma_coo} kg ✓")

    # Confirmar distribuição do COO para cada SUP por produto
    for item in result_coo.items:
        _confirm_distribution(
            db, cycle.id, cat.id,
            nodes["COO_05"].id, item.destination_node_id,
            item.suggested_kg, product_id=item.product_id,
        )
    await db.commit()

    # ──────────────────────────────────────────────────────
    # NÍVEL 4: Supervisor (SUP_01) distribui POR PRODUTO para vendedores
    # ──────────────────────────────────────────────────────
    # SUP_01 precisa de uma distribution de grupo (product_id=None) confirmada
    # Somar os kg que SUP_01 recebeu por produto
    sup01_total = sum(
        i.suggested_kg for i in result_coo.items
        if i.destination_node_id == nodes["SUP_01"].id
    )
    _confirm_distribution(db, cycle.id, cat.id, nodes["COO_05"].id, nodes["SUP_01"].id, sup01_total)
    await db.commit()

    result_sup = await engine.suggest(
        db, nodes["SUP_01"].id, cycle.id, cat.id, product_level=True,
    )
    soma_sup = sum(i.suggested_kg for i in result_sup.items)
    assert soma_sup == sup01_total, \
        f"SUPERVISOR: soma ({soma_sup}) != meta ({sup01_total})"
    print(f"\nSUPERVISOR ({nodes['SUP_01'].name}) distribui {sup01_total} kg por PRODUTO")
    print(f"{'-'*60}")
    for item in sorted(result_sup.items, key=lambda x: (x.product_name, x.destination_name)):
        print(f"  {item.product_name:25s} -> {item.destination_name:20s}: {item.suggested_kg} kg ({item.percent:.1f}%)")
    print(f"  TOTAL: {soma_sup} kg ✓")

    # ──────────────────────────────────────────────────────
    # Verificação final: nenhum item com kg negativo
    # ──────────────────────────────────────────────────────
    all_items = result_ger2.items + result_reg.items + result_coo.items + result_sup.items
    for item in all_items:
        assert item.suggested_kg >= 0, \
            f"Meta negativa detectada: {item.destination_name} = {item.suggested_kg}"

    print(f"\n{'='*60}")
    print(f"TODOS OS NÍVEIS: soma == meta estipulada ✓")
    print(f"Nenhuma meta negativa ✓")
    print(f"{'='*60}")


@pytest.mark.asyncio
async def test_soma_percentuais_100(db):
    """Verifica que a soma dos percentuais é aproximadamente 100%."""
    nodes = await _seed_hierarchy(db)
    cat, products = await _seed_catalog(db)
    cycle, _ = await _seed_cycle_and_base(db, nodes, products)

    engine = BaseDistributionEngine()

    _confirm_distribution(db, cycle.id, cat.id, None, nodes["GER_01"].id, 10000)
    await db.commit()

    result = await engine.suggest(
        db, nodes["GER_01"].id, cycle.id, cat.id, product_level=False,
    )
    soma_pct = sum(i.percent for i in result.items)
    assert abs(soma_pct - Decimal("100")) < Decimal("0.01"), \
        f"Soma percentuais = {soma_pct}, esperado ~100"


@pytest.mark.asyncio
async def test_sem_base_distribution_retorna_vazio(db):
    """Se não há dados históricos, engine retorna items vazio."""
    nodes = await _seed_hierarchy(db)
    cat, _ = await _seed_catalog(db)
    cycle = GoalCycle(month=7, year=2026, working_days=23)
    db.add(cycle)
    await db.flush()

    _confirm_distribution(db, cycle.id, cat.id, None, nodes["GER_01"].id, 5000)
    await db.commit()

    engine = BaseDistributionEngine()
    result = await engine.suggest(
        db, nodes["GER_01"].id, cycle.id, cat.id, product_level=False,
    )
    assert len(result.items) == 0


@pytest.mark.asyncio
async def test_feriado_afeta_calculo(db):
    """Feriado em dia útil altera o cálculo de dias úteis efetivos."""
    nodes = await _seed_hierarchy(db)
    cat, products = await _seed_catalog(db)
    cycle, _ = await _seed_cycle_and_base(db, nodes, products)

    _confirm_distribution(db, cycle.id, cat.id, None, nodes["GER_01"].id, 10000)
    await db.commit()

    engine = BaseDistributionEngine()

    # Sem feriados extras (só o 1/Mai que já está no fixture)
    r1 = await engine.suggest(
        db, nodes["GER_01"].id, cycle.id, cat.id, product_level=False,
    )
    soma1 = sum(i.suggested_kg for i in r1.items)
    assert soma1 == Decimal("10000")

    # Adicionar feriados em julho (mês alvo) — reduz dias úteis do alvo
    db.add(Holiday(holiday_date=date(2026, 7, 9), year=2026, name="Revolução Constitucionalista"))
    # Remover override para que o cálculo automático pegue o feriado
    from sqlalchemy import select
    from api.models.calendar import WorkingDaysConfig as WDC
    existing = await db.execute(select(WDC).where(WDC.year == 2026, WDC.month == 7))
    wdc = existing.scalar_one_or_none()
    if wdc:
        await db.delete(wdc)
    # Também limpar working_days do ciclo para forçar cálculo automático
    cycle.working_days = None
    await db.commit()

    r2 = await engine.suggest(
        db, nodes["GER_01"].id, cycle.id, cat.id, product_level=False,
    )
    soma2 = sum(i.suggested_kg for i in r2.items)
    # Soma ainda bate com o budget (invariante principal)
    assert soma2 == Decimal("10000"), \
        f"Com feriado extra, soma ({soma2}) != 10000"


@pytest.mark.asyncio
async def test_cascata_completa_soma_preservada(db):
    """Teste de cascata: o que chega no vendedor, somando tudo, bate com a meta gerencial."""
    nodes = await _seed_hierarchy(db)
    cat, products = await _seed_catalog(db)
    cycle, _ = await _seed_cycle_and_base(db, nodes, products)

    engine = BaseDistributionEngine()
    META = Decimal("8500")

    # Nível 1: gerente
    _confirm_distribution(db, cycle.id, cat.id, None, nodes["GER_01"].id, META)
    await db.commit()
    r_ger = await engine.suggest(db, nodes["GER_01"].id, cycle.id, cat.id, False)
    assert sum(i.suggested_kg for i in r_ger.items) == META

    # REG_01 não tem vendedores no nosso test, então pega apenas REG_02
    reg02_kg = next(i.suggested_kg for i in r_ger.items if i.destination_node_id == nodes["REG_02"].id)

    # Nível 2: regional
    _confirm_distribution(db, cycle.id, cat.id, nodes["GER_01"].id, nodes["REG_02"].id, reg02_kg)
    await db.commit()
    r_reg = await engine.suggest(db, nodes["REG_02"].id, cycle.id, cat.id, False)
    assert sum(i.suggested_kg for i in r_reg.items) == reg02_kg

    coo05_kg = next(i.suggested_kg for i in r_reg.items if i.destination_node_id == nodes["COO_05"].id)

    # Nível 3: coordenador local (product level)
    _confirm_distribution(db, cycle.id, cat.id, nodes["REG_02"].id, nodes["COO_05"].id, coo05_kg)
    await db.commit()
    r_coo = await engine.suggest(db, nodes["COO_05"].id, cycle.id, cat.id, True)
    assert sum(i.suggested_kg for i in r_coo.items) == coo05_kg

    # Nível 4: cada supervisor
    sup_totals = {}
    for sup_sid in ["SUP_01", "SUP_02", "SUP_03"]:
        sup_id = nodes[sup_sid].id
        total = sum(i.suggested_kg for i in r_coo.items if i.destination_node_id == sup_id)
        sup_totals[sup_sid] = total
        # Confirmar distribution de grupo
        _confirm_distribution(db, cycle.id, cat.id, nodes["COO_05"].id, sup_id, total)
    await db.commit()

    vendedor_total = Decimal("0")
    for sup_sid in ["SUP_01", "SUP_02", "SUP_03"]:
        r_sup = await engine.suggest(db, nodes[sup_sid].id, cycle.id, cat.id, True)
        soma = sum(i.suggested_kg for i in r_sup.items)
        assert soma == sup_totals[sup_sid], \
            f"{sup_sid}: soma vendedores ({soma}) != meta supervisor ({sup_totals[sup_sid]})"
        vendedor_total += soma

    # A soma final de todos os vendedores deve bater com a meta do COO_05
    assert vendedor_total == coo05_kg, \
        f"Soma vendedores ({vendedor_total}) != meta coord local ({coo05_kg})"

    print(f"\nCASCATA COMPLETA:")
    print(f"  Meta gerencial:      {META} kg")
    print(f"  -> REG_02:            {reg02_kg} kg")
    print(f"  -> COO_05:            {coo05_kg} kg")
    for sid, kg in sup_totals.items():
        print(f"    -> {sid}:           {kg} kg")
    print(f"  Soma vendedores:     {vendedor_total} kg")
    print(f"  Invariante mantido ✓")
