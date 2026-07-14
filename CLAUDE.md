# CLAUDE.md

Guia para agentes de IA (Claude Code) trabalhando neste repositório. Para o produto e a
arquitetura, comece por [docs/PROJECT.md](docs/PROJECT.md) — este arquivo é só sobre como
trabalhar no código.

## O que é este projeto

App web interno da Bello Alimentos que distribui metas comerciais em KG (inteiro, sem casas
decimais) em cascata por 5 níveis hierárquicos fixos: **Gerente → Coordenador Regional →
Coordenador Local → Supervisor → Vendedor**. A regra mais crítica do sistema: em cada repasse, a
soma distribuída para baixo deve fechar **exatamente** com o recebido de cima — sem sobra, sem
falta. Detalhe em [docs/architecture.md](docs/architecture.md).

## Regra de ouro: não invente as fórmulas

Existem **5 pendências de cálculo conhecidas** (sugestão automática por grupo, distribuição
Regional→Local, quebra grupo→subgrupo, distribuição Supervisor→Vendedor, e o método de
arredondamento/rateio de resto) que o usuário ainda vai definir — ver
[docs/open-questions.md](docs/open-questions.md). **Nunca hardcode uma fórmula definitiva.**
Implemente essas peças como estratégias plugáveis (`DistributionStrategy`, `SuggestionStrategy`,
`RoundingPolicy`, conforme [docs/architecture.md](docs/architecture.md)); se precisar de um
placeholder para destravar desenvolvimento, marque-o explicitamente como **não-aprovado** no nome
da classe/docstring.

## Stack e estrutura

- **Backend:** Python 3.12, Django 5.2 LTS + Django REST Framework, dentro de `backend/`.
- **Apps de domínio** (`backend/apps/`): `hierarchy` (árvore de nós), `catalog` (grupos/subgrupos/
  produtos), `cycles` (ciclo mensal), `allocations` (`GoalAllocation`, o repasse de meta —
  entidade central), `accounts` (`User` customizado com login próprio e vínculo à hierarquia).
- **Frontend:** ainda não existe (React + Vite/TS planejado — ver
  [docs/roadmap.md](docs/roadmap.md), passo 8, só depois do núcleo do backend estar validado).
- **Banco:** PostgreSQL 16, só acessível via Docker Compose.
- Nomenclatura do projeto é **nova**, sem herança de versões anteriores — não existe código
  legado neste repo para seguir de referência.

## Ambiente: tudo roda em Docker

Não existe Python nem Node instalados fora de containers neste projeto — **todo comando roda via
`docker compose exec backend ...` (stack já no ar) ou `docker compose run --rm backend ...`
(stack ainda não subiu)**.

```bash
docker compose up -d                                    # sobe db + backend
docker compose exec backend python manage.py migrate    # aplicar migrações
docker compose exec backend python manage.py makemigrations   # após alterar models
docker compose exec backend pytest                       # testes
docker compose exec backend python manage.py check       # checagem de configuração/models
docker compose exec backend black .                      # formatar
docker compose exec backend ruff check --fix .           # lint + autofix
```

Depois de alterar `models.py`, sempre gere e aplique a migração antes de considerar a tarefa
concluída — models sem migração correspondente quebram `manage.py check` e `migrate`.

## Antes de considerar uma mudança de backend pronta

1. `docker compose exec backend python manage.py makemigrations` (se mexeu em models) e
   `migrate`.
2. `docker compose exec backend black . && docker compose exec backend ruff check --fix .`
3. `docker compose exec backend python manage.py check`
4. `docker compose exec backend pytest`

Todos os 4 devem passar limpos (sem erros, sem "would reformat") antes de reportar a tarefa como
concluída.

## Convenções

- Formatação: `black` (line-length 110). Lint: `ruff` (regras `E`, `F`, `I`; migrations excluídas
  do lint). Config em `backend/pyproject.toml`.
- Commits/branches: `tipo/descrição` (ex.: `feat/allocation-closure-validator`,
  `fix/hierarchy-scope-leak`), seguindo o padrão já usado na branch atual.
- Comentários no código: só quando explicam um porquê não-óbvio (ex.: uma decisão pendente como
  O5, uma invariante escondida). Não comente o óbvio.
- Regras de negócio (fechamento exato, isolamento de escopo) pertencem a **services de domínio**,
  não a views/serializers — mantém o monólito modular descrito em
  [docs/architecture.md](docs/architecture.md).

## Nunca

- Nunca commite `.env` (só `.env.example`) nem qualquer segredo real (senha de banco, chave do
  Django, credenciais do Postgres externo do histórico de vendas).
- Nunca escreva no Postgres externo do histórico de vendas — acesso é **somente leitura**, via
  `SalesHistoryProvider` (ver anticorruption layer em
  [docs/architecture.md](docs/architecture.md)). Use o Fake Provider para dev/testes enquanto a
  fonte real (pendência O3) não estiver definida.
- Nunca permita que uma alocação (`GoalAllocation`) seja persistida sem fechar 100% com a
  alocação-pai — é a invariante central do produto.
