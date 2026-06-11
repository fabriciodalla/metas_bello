# Changelog

Todas as mudancas relevantes do projeto METAS_BELLO devem ser registradas aqui.

O projeto usa versionamento semantico como referencia:

- `MAJOR`: mudancas incompativeis ou grandes viradas de produto.
- `MINOR`: novas funcionalidades compativeis.
- `PATCH`: correcoes pequenas, ajustes internos e documentacao.

## v0.1.0 - 2026-06-11

Base inicial do projeto.

- Criado projeto Django `config`.
- Criados apps modulares iniciais: `accounts`, `hierarchy`, `catalog`, `goals`, `allocations`, `approvals`, `imports`, `erp_readonly` e `audit`.
- Adicionado Docker Compose com servicos `web` e `db`.
- Configurado PostgreSQL como banco do sistema em container.
- Implementado contrato de fechamento 100% em `allocations.services.validation.evaluate_distribution_closure`.
- Atualizada documentacao para uso obrigatorio de Docker Compose.
- Suite inicial rodando em container com 9 testes passando.
