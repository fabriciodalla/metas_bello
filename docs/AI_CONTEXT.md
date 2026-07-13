# Contexto Para IA

Indice de referencia. Consulte cada doc apenas quando a tarefa tocar essa area.

| Area | Arquivo |
| --- | --- |
| Produto, escopo, usuarios, fluxo | `docs/PROJECT.md` |
| Arquitetura, componentes, apps, integracoes | `docs/ARCHITECTURE.md` |
| Modelos Django, entidades, invariantes | `docs/DATA_MODEL.md` |
| Decisoes aprovadas vs hipoteses | `docs/DECISION_LOG.md` |
| Layouts Excel de importacao | `docs/IMPORT_LAYOUTS.md` |
| Testes, contratos, comandos | `docs/TESTING.md` |
| Regras para o agente | `AGENTS.md` |

## Estado Atual Resumido

- Stack: FastAPI + Next.js + PostgreSQL proprio + ERP somente leitura.
- Backend: `api/` com routers (auth, hierarchy, goals, erp, calendar).
- Frontend: `frontend/` Next.js 15 com Tailwind.
- Invariante principal: distribuicao bloqueada se soma != 100% da meta recebida.
- Coordenador Local e etapa obrigatoria entre Regional e Supervisor.
- Matriz direta de distribuicao: Gerente -> Regional -> Local -> Supervisor -> Vendedor.
- Quantidades operacionais em kg usam 0 casas decimais.
- Carga inicial: 4 grupos, 152 subgrupos, 1 gerente, 2 regionais, 9 locais, 26 supervisores, 93 vendedores.

## Regra de Periodo do Calculo de Metas

**REGRA FIXA — nao alterar sem aprovacao:**

- O ciclo e sempre para o **mes seguinte** ao atual.
- O historico usa os **3 meses FECHADOS** antes do mes atual (pula o mes corrente).
- Formula: `ciclo = mes_atual + 1`, `historico = mes_atual - 1, - 2, - 3`.

Exemplo (estamos em junho/2026):
- Ciclo: **julho/2026**
- Historico: **maio, abril, marco** (junho ainda nao fechou, e pulado)
- Meta diaria = soma_3_meses / dias_uteis(mar+abr+mai)
- Meta individual = meta_diaria × dias_uteis(julho)

Implementacao: `previous_months(cycle.year, cycle.month, 3, skip=1)` em `api/services/working_days.py`.

## Regra de Dias Uteis

- Dias uteis = dias de semana (seg-sex) - feriados em dia util.
- Tabela `holidays` armazena feriados.
- Tabela `working_days_config` armazena overrides do admin.
- Prioridade: override confirmado > calculo automatico (weekdays - feriados).
- Admin pode ajustar dias uteis pela tela "Dias Uteis" ou pelo input no Painel Gerencial.

## Menu por Role

| Role | Comercial | Administracao |
| --- | --- | --- |
| GERENTE | Dashboard, Painel Gerencial, Ciclos, Distribuir Metas, Metas Vendedores | — |
| ADMINISTRADOR | Tudo acima | Hierarquia, Produtos, Usuarios, Feristas, Dias Uteis |
| COORDENADOR_REGIONAL | Dashboard, Ciclos, Distribuir Metas, Metas Vendedores | — |
| COORDENADOR_LOCAL | Dashboard, Ciclos, Distribuir Metas, Metas Vendedores | — |
| SUPERVISOR | Dashboard, Distribuir Metas, Metas Vendedores | — |
| VENDEDOR | Dashboard, Metas Vendedores | — |

## Fluxo de Sync ERP (3 passos)

1. `POST /erp/clients/sync/{cycle_id}` — carteira de clientes
2. `POST /erp/accumulated/sync/{cycle_id}?start_date=YYYY-MM-01` — historico de vendas
3. `POST /erp/base-distribution/build/{cycle_id}` — cruzamento carteira × vendas

O `start_date` deve cobrir os 3 meses historicos. Ex: ciclo julho → start_date = 2026-03-01.
