# AGENTS.md

## Objetivo Do Projeto

METAS_BELLO e um sistema interno Django para criacao, distribuicao e aprovacao hierarquica de metas comerciais mensais em kg.

O fluxo principal parte do gerente, passa por coordenadores regionais, coordenadores locais, supervisores e chega aos vendedores. O sistema deve preservar rastreabilidade, fechar distribuicoes em 100% e manter o banco do sistema separado do banco/ERP lido em modo somente leitura.

## Regras Para Codex

- Leia `README.md`, `docs/PROJECT.md`, `docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md` e `docs/DECISION_LOG.md` antes de alterar regras de negocio.
- Nao trate hipotese como decisao aprovada. Se algo estiver em aberto, marque como pendencia ou pergunte ao usuario.
- Nao implemente integracao de escrita no ERP. A decisao atual permite somente leitura.
- Nao altere a regra de fechamento 100% sem confirmacao explicita do usuario.
- Nao coloque credenciais, tokens, strings de conexao reais ou dados sensiveis em arquivos versionados.
- Preserve a separacao entre banco PostgreSQL do sistema e banco/ERP somente leitura.
- Ao criar codigo Django, prefira monolito modular com apps por dominio.
- Execute comandos do projeto Django via Docker Compose, nao diretamente no host.

## Arquivos Importantes

- `README.md`: visao geral e ponto de entrada.
- `docs/PROJECT.md`: escopo, usuarios, regras e pendencias de produto.
- `docs/ARCHITECTURE.md`: desenho tecnico, componentes e integracoes.
- `docs/DATA_MODEL.md`: entidades conceituais e invariantes de dados.
- `docs/DECISION_LOG.md`: decisoes aprovadas, propostas e hipoteses.
- `docs/AI_CONTEXT.md`: memoria operacional para IA.
- `docs/CODEX_WORKFLOWS.md`: passos sugeridos para evoluir o projeto.

## Comandos Seguros

Suite atual em container:

```powershell
docker compose run --rm web python -m unittest discover -s tests -v
```

Comandos Django em container:

```powershell
docker compose build
docker compose up -d db
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py check
docker compose up web
```

Antes de executar comandos que baixam dependencias, criam banco, alteram dados ou acessam rede, verifique as regras de permissao da sessao.

## Areas Sensiveis

- Integracao com ERP/banco corporativo.
- Credenciais e configuracoes de ambiente.
- Migracoes de banco.
- Regras de aprovacao e fechamento 100%.
- Importacao Excel de hierarquia e cadastros.
- Dados de vendedores, equipes, historico comercial e metas.

## Padroes De Edicao

- Atualize `docs/DECISION_LOG.md` quando uma decisao de produto, arquitetura, dados, seguranca ou operacao mudar.
- Atualize `docs/DATA_MODEL.md` quando criar ou alterar modelos Django relevantes.
- Atualize `docs/ARCHITECTURE.md` quando alterar componentes, integracoes ou fluxo tecnico.
- Atualize `README.md` quando houver comandos reais de setup, teste ou execucao.
- Mantenha documentacao em portugues simples e objetiva.

## Quando Atualizar Documentacao

Atualize os docs sempre que:

- uma regra de negocio for criada, alterada ou removida;
- um novo app Django for adicionado;
- houver mudanca no fluxo de distribuicao/aprovacao;
- surgir nova dependencia externa;
- uma pendencia for decidida;
- o modo de rodar, testar ou configurar o projeto mudar.
