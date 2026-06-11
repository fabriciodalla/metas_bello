# Contexto Para IA

## Resumo

METAS_BELLO e um projeto para construir um app web interno em Django que controla a criacao, distribuicao e liberacao hierarquica de metas comerciais mensais em kg.

O sistema deve evitar divergencias entre meta recebida e meta distribuida. A regra central e: uma distribuicao so pode seguir para o proximo nivel quando a soma dos destinos fechar 100% da meta recebida.

## Mapa Do Repositorio

Estado atual:

- `README.md`: entrada do projeto.
- `AGENTS.md`: regras para Codex.
- `Dockerfile` e `docker-compose.yml`: ambiente containerizado com Django e PostgreSQL.
- `manage.py` e `config/`: base Django inicial.
- Apps Django iniciais: `accounts`, `hierarchy`, `catalog`, `goals`, `allocations`, `approvals`, `imports`, `erp_readonly` e `audit`.
- `tests/`: suite inicial em `unittest` com guardrails e contratos.
- `docs/PROJECT.md`: produto, escopo e regras.
- `docs/ARCHITECTURE.md`: arquitetura proposta.
- `docs/DATA_MODEL.md`: entidades conceituais.
- `docs/DECISION_LOG.md`: decisoes registradas.
- `docs/CODEX_WORKFLOWS.md`: fluxos de trabalho sugeridos.
- `docs/TESTING.md`: estrategia e comando de testes.
- `docs/DOCS_MAINTENANCE.md`: regra de manutencao dos docs.

O primeiro servico de dominio implementado e `allocations.services.validation.evaluate_distribution_closure`.

## Fontes Da Verdade

- Regras de negocio: `docs/PROJECT.md`.
- Arquitetura: `docs/ARCHITECTURE.md`.
- Dados: `docs/DATA_MODEL.md`.
- Decisoes: `docs/DECISION_LOG.md`.
- Testes: `docs/TESTING.md` e `tests/`.
- Regras para agentes: `AGENTS.md`.

## Invariantes

- App web interno.
- Django como tecnologia principal.
- PostgreSQL como banco do sistema.
- ERP/banco somente leitura para historico.
- Metas mensais.
- Metas em kg.
- Distribuicao hibrida: sugestao automatica + ajuste manual.
- Bloqueio quando a soma distribuida nao fecha 100%.
- Login proprio no MVP.
- Login Microsoft/empresa como evolucao futura.
- Desenvolvimento e execucao via Docker Compose.

## Decisoes Atuais

As decisoes aprovadas estao em `docs/DECISION_LOG.md`.

Ao alterar escopo, arquitetura, banco, integracao, autenticacao, regra de fechamento ou hierarquia, atualize o log de decisoes.

## Pendencias Conhecidas

- Confirmar fonte do historico no ERP/banco.
- Definir periodo de historico usado na sugestao.
- Definir regra de arredondamento.
- Definir papel detalhado do coordenador local.
- Definir telas prioritarias.
- Definir ambiente de deploy.
- Definir layout das importacoes Excel.

## Cuidados Para Futuras Implementacoes

- Nao gravar no ERP.
- Nao versionar credenciais.
- Nao criar regra que permita envio com sobra ou falta.
- Nao esconder ajustes manuais; eles precisam ser rastreaveis.
- Nao misturar dados importados de Excel com dados oficiais do ERP sem origem clara.
- Nao rodar comandos de app Django diretamente no host; usar `docker compose run --rm web ...`.
