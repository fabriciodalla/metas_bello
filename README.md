# METAS_BELLO

Sistema interno para criacao, distribuicao e aprovacao hierarquica de metas comerciais em kg.

## Stack

- **Backend**: Python + FastAPI (`api/`)
- **Frontend**: Next.js + React + TypeScript (`frontend/`)
- **Banco**: PostgreSQL 16
- **Orquestracao**: Docker Compose (`db`, `api`, `frontend`)

## Como Rodar

```bash
# 1. Copiar variaveis de ambiente
cp .env.example .env

# 2. Subir todos os servicos
docker compose up --build

# 3. Criar tabelas, niveis de hierarquia e usuario admin
docker compose exec api python -m api.seed

# 4. Acessar
# Frontend:  http://localhost:3000
# API docs:  http://localhost:8000/docs
# Login:     admin / admin
```

### Portas alternativas

```powershell
$env:API_HOST_PORT='8001'
$env:FRONTEND_HOST_PORT='3001'
$env:POSTGRES_HOST_PORT='5433'
docker compose up --build
```

## Estrutura

```
METAS_BELLO/
├── api/                    # Backend FastAPI
│   ├── main.py             # App entry point
│   ├── models/             # SQLAlchemy models
│   ├── schemas/            # Pydantic request/response
│   ├── routers/            # Endpoints REST
│   ├── services/           # Regras de negocio
│   │   └── engines/        # Motores de calculo plugaveis
│   └── seed.py             # Carga inicial
├── frontend/               # Frontend Next.js
│   └── src/
│       ├── app/            # Pages (App Router)
│       ├── components/     # Componentes reutilizaveis
│       └── lib/api.ts      # Cliente da API
├── docs/                   # Documentacao do projeto
├── docker-compose.yml      # db + api + frontend
└── .env.example
```

## Endpoints Principais

| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | `/auth/login` | Login (retorna JWT) |
| GET | `/auth/me` | Usuario logado |
| GET | `/hierarchy/tree` | Arvore hierarquica |
| GET/POST | `/hierarchy/nodes` | CRUD nodes |
| GET/POST | `/goals/cycles` | Ciclos de meta |
| GET | `/goals/cycles/{id}/goals` | Metas do ciclo |
| GET/POST | `/allocations/batches` | Lotes de distribuicao |
| POST | `/allocations/batches/{id}/suggest` | Sugestao via motor |
| POST | `/allocations/batches/{id}/send` | Enviar distribuicao |
| PUT | `/allocations/batches/{id}/lines/bulk` | Atualizar linhas em lote |

## Motores de Calculo

O sistema suporta multiplos motores de calculo para sugestao de distribuicao:

- **historical**: Distribui proporcionalmente ao historico de vendas do ERP
- **equal**: Distribui igualmente entre todos os destinos
- **previous_cycle**: Distribui proporcionalmente ao ciclo anterior enviado

Novos motores podem ser adicionados implementando o protocolo `CalculationEngine` em `api/services/engines/`.

## Documentacao

- [Projeto](docs/PROJECT.md)
- [Arquitetura](docs/ARCHITECTURE.md)
- [Modelo de Dados](docs/DATA_MODEL.md)
- [Layouts de Importacao Excel](docs/IMPORT_LAYOUTS.md)
- [Log de Decisoes](docs/DECISION_LOG.md)

## Decisoes Importantes

- Hierarquia generica via `HierarchyNode` com arvore `parent_id` (substitui 5 tabelas separadas).
- Distribuicao bloqueada se soma dos destinos != 100% da meta recebida.
- Cascata rastreavel via `parent_batch_id` no lote.
- Nunca gravar no ERP — somente leitura.
- Remocao operacional = inativacao; sem exclusao fisica.
- Quantidades em kg sem casas decimais.
