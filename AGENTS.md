# AGENTS.md

## Projeto

App web interno com FastAPI (backend) e Next.js (frontend) para criar, distribuir e aprovar metas comerciais mensais em kg. Fluxo: Gerente → Regional → Local → Supervisor → Vendedor. Banco proprio PostgreSQL; ERP somente leitura para historico.

## Stack

- Backend: FastAPI + SQLAlchemy async (`api/`)
- Frontend: Next.js 15 + React 19 + TypeScript + Tailwind (`frontend/`)
- Banco: PostgreSQL 16
- Orquestracao: Docker Compose com servicos `db`, `api`, `frontend`

## Invariantes — nunca quebre sem confirmacao explicita

- Distribuicao bloqueada se soma dos destinos != 100% da meta recebida.
- Nunca gravar no ERP.
- Nunca versionar credenciais ou segredos.
- Remocao operacional = inativacao; sem exclusao fisica.
- Nodes inativos ficam no banco; distribuicoes usam so nodes ativos.
- Hierarquia representada por `HierarchyNode` com `parent_id` — nao criar tabelas separadas por nivel.
- Motores de calculo devem implementar o protocolo `CalculationEngine`.
- **Periodo historico**: ciclo = mes_atual + 1. Historico = 3 meses fechados antes do atual (pula o mes corrente). Implementado com `previous_months(..., skip=1)`. Nao alterar sem aprovacao.

## Areas sensiveis

- Integracao ERP, credenciais, migrations de banco.
- Regras de fechamento 100% (`api/services/validation.py`).
- Validacao de escopo hierarquico (`api/services/scope.py`).
- Motores de calculo (`api/services/engines/`).

## Comandos seguros

```bash
docker compose up --build
docker compose exec api python -m api.seed
docker compose logs api
docker compose logs frontend
```

## Consulte sob demanda

| Area | Arquivo |
|------|---------|
| Regras de negocio e escopo | `docs/PROJECT.md` |
| Arquitetura e componentes | `docs/ARCHITECTURE.md` |
| Modelos e invariantes de dados | `docs/DATA_MODEL.md` |
| Decisoes aprovadas | `docs/DECISION_LOG.md` |
| Layouts Excel de importacao | `docs/IMPORT_LAYOUTS.md` |

## Quando atualizar docs

- Regra de negocio criada/alterada → `docs/PROJECT.md`
- Model SQLAlchemy criado/alterado → `docs/DATA_MODEL.md` + `docs/ARCHITECTURE.md`
- Decisao tomada → `docs/DECISION_LOG.md`
- Comando novo → `README.md`
- Nova regra permanente → `AGENTS.md`
