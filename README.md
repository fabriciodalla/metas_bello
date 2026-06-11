# METAS_BELLO

Sistema interno para criacao, distribuicao e aprovacao hierarquica de metas comerciais em kg.

## Visao Geral

O projeto sera um app web interno em Django para apoiar o ciclo mensal de metas da Bello. O sistema deve permitir que o gerente crie metas globais por grupo, distribua essas metas para coordenadores regionais e acompanhe a quebra das metas pela hierarquia ate supervisores e vendedores.

O MVP prioriza controle, rastreabilidade e fechamento exato da distribuicao. Uma distribuicao so pode seguir para o proximo nivel quando a soma dos valores distribuidos fechar 100% da meta recebida.

## Objetivo Do MVP

- Criar metas mensais em kg por grupo.
- Distribuir metas seguindo a hierarquia comercial.
- Gerar sugestao automatica de distribuicao com base em historico de vendas lido diretamente do banco/ERP em modo somente leitura.
- Permitir ajuste manual antes do envio.
- Bloquear envio quando a distribuicao nao fechar 100%.
- Registrar status, responsavel, historico e aprovacoes/liberacoes do fluxo.
- Alimentar hierarquia e cadastros por importacao Excel com ajustes manuais no sistema.

## Stack Decidida

- Backend e frontend inicial: Django.
- Banco do sistema: PostgreSQL.
- Integracao ERP: leitura direta em banco somente leitura.
- Login do MVP: usuarios e senhas proprios no Django.
- Execucao e desenvolvimento: Docker Compose com servicos `web` e `db`.
- Evolucao prevista: login Microsoft/empresa.

## Documentacao

- [Projeto](docs/PROJECT.md)
- [Arquitetura](docs/ARCHITECTURE.md)
- [Modelo de Dados](docs/DATA_MODEL.md)
- [Log de Decisoes](docs/DECISION_LOG.md)
- [Contexto para IA](docs/AI_CONTEXT.md)
- [Workflows Codex](docs/CODEX_WORKFLOWS.md)
- [Estrategia de Testes](docs/TESTING.md)
- [Manutencao da Documentacao](docs/DOCS_MAINTENANCE.md)

## Como Rodar

O projeto Django inicial ja foi criado e deve ser executado em container. O caminho principal de desenvolvimento e Docker Compose.

Comandos principais:

```powershell
docker compose build
docker compose up -d db
docker compose run --rm web python manage.py migrate
docker compose up web
```

O app fica disponivel em:

```text
http://localhost:8000/health/
```

Para rodar a suite de testes dentro do container:

```powershell
docker compose run --rm web python -m unittest discover -s tests -v
```

O arquivo `.env.example` documenta as variaveis esperadas. Nao versionar `.env` com segredos reais.

## Decisoes Importantes

- O sistema comeca como app web interno.
- O MVP usa metas com aprovacao/liberacao hierarquica.
- As metas sao mensais e medidas em kg.
- A distribuicao sera hibrida: sugestao automatica + ajuste manual.
- A sugestao usa historico do ERP/banco.
- O sistema bloqueia envio quando a soma distribuida nao fecha 100%.
- O PostgreSQL do sistema fica separado do banco/ERP.
- O desenvolvimento e a execucao do projeto devem acontecer via Docker Compose.

## Pendencias

- Confirmar tabelas/views e regras de leitura do ERP.
- Definir exatamente o papel do coordenador local no fluxo de aprovacao e distribuicao.
- Definir telas principais do MVP.
- Definir politica de arredondamento para distribuicao em kg.
- Definir perfis de acesso e permissoes detalhadas.
