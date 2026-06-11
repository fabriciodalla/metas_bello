# Workflows Codex

## Antes De Codar

1. Leia `README.md`.
2. Leia `docs/PROJECT.md`.
3. Leia `docs/ARCHITECTURE.md`.
4. Leia `docs/DATA_MODEL.md`.
5. Confira `docs/DECISION_LOG.md` para separar decisoes aprovadas de hipoteses.
6. Rode a suite de base quando mexer em regras, seguranca, ERP ou documentacao critica:

```powershell
docker compose run --rm web python -m unittest discover -s tests -v
```

## Criar Projeto Django

Fluxo recomendado, sempre em container:

1. Usar `Dockerfile` e `docker-compose.yml` como ambiente principal.
2. Instalar dependencias em `requirements.txt`.
3. Configurar PostgreSQL via variaveis de ambiente.
4. Criar ou ajustar apps modulares conforme `docs/ARCHITECTURE.md`.
5. Implementar modelos iniciais conforme `docs/DATA_MODEL.md`.
6. Adicionar testes para fechamento 100%, permissoes e auditoria.
7. Atualizar README com comandos reais.

Comandos base:

```powershell
docker compose build
docker compose up -d db
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py check
```

## Implementar Regra De Fechamento 100%

Checklist:

- A meta recebida deve ser a referencia de total.
- A soma das distribuicoes filhas deve ser calculada com precisao decimal.
- O envio deve ser bloqueado se houver diferenca.
- A diferenca deve ser apresentada ao usuario.
- O bloqueio deve ser registrado em auditoria ou evento.
- Testes devem cobrir fechamento correto, sobra e falta.

## Implementar Integracao ERP Read-only

Checklist:

- Usar credencial somente leitura.
- Guardar credenciais fora do repositorio.
- Criar camada/adaptador isolado.
- Nao espalhar SQL do ERP por views ou templates.
- Adicionar timeout e tratamento de indisponibilidade.
- Criar testes com mock/fake, sem depender do ERP real.
- Documentar tabelas/views autorizadas quando forem conhecidas.

## Implementar Importacao Excel

Checklist:

- Definir layout antes do codigo.
- Validar colunas obrigatorias.
- Validar duplicidades.
- Validar referencias de hierarquia.
- Registrar importacao, usuario, data e erros.
- Permitir ajustes manuais apos importacao.
- Nao sobrescrever dados existentes sem regra clara.

## Atualizar Documentacao Apos Mudancas

Sempre que concluir uma etapa:

- Atualize `README.md` se houver novo comando.
- Atualize `docs/ARCHITECTURE.md` se houver nova estrutura.
- Atualize `docs/DATA_MODEL.md` se os modelos mudarem.
- Atualize `docs/DECISION_LOG.md` se uma decisao for tomada.
- Atualize `AGENTS.md` se surgir uma regra permanente para Codex.
