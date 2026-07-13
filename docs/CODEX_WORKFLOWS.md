# Workflows Codex

> Consulte os docs abaixo **sob demanda**, apenas quando a tarefa tocar essa área. Não leia todos antes de começar.

## Criar Projeto Django

1. Usar `Dockerfile` e `docker-compose.yml` como ambiente principal.
2. Instalar dependências em `requirements.txt`.
3. Configurar PostgreSQL via variáveis de ambiente.
4. Criar ou ajustar apps modulares conforme `docs/ARCHITECTURE.md`.
5. Implementar modelos conforme `docs/DATA_MODEL.md`.
6. Adicionar testes para fechamento 100%, permissões e auditoria.
7. Atualizar README com comandos reais.

```powershell
docker compose build
docker compose up -d db
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py check
```

## Implementar Regra De Fechamento 100%

- Meta recebida é a referência de total.
- Soma das distribuições filhas calculada com precisão decimal.
- Envio bloqueado se houver diferença; diferença apresentada ao usuário.
- Bloqueio registrado em auditoria/evento.
- Testes: fechamento correto, sobra e falta.

## Implementar Integração ERP Read-only

- Credencial somente leitura, fora do repositório.
- Camada/adaptador isolado; SQL do ERP não espalhado por views ou templates.
- Timeout e tratamento de indisponibilidade.
- Testes com mock/fake, sem depender do ERP real.
- Documentar tabelas/views autorizadas quando conhecidas.

## Implementar Importação Excel

Layouts oficiais em `docs/IMPORT_LAYOUTS.md`.

- Validar colunas obrigatórias, duplicidades e referências de hierarquia.
- Registrar importação, usuário, data e erros.
- Não sobrescrever dados existentes sem regra clara.

```powershell
docker compose run --rm -v "C:\Users\FABRICIO.DALLA\Downloads:/input:ro" web python manage.py import_reference_data --subgroups /input/SUBGRUPOS_BELLO.xlsx --hierarchy /input/hierarquia_bello.xlsx --effective-on 2026-06-11 --skip-name-conflicts
```

## Atualizar Documentação Após Mudanças

- Novo comando → `README.md`
- Nova estrutura/integração → `docs/ARCHITECTURE.md`
- Modelos alterados → `docs/DATA_MODEL.md`
- Decisão tomada → `docs/DECISION_LOG.md`
- Nova regra permanente → `AGENTS.md`
