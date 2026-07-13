# Estrategia De Testes

## Objetivo

Garantir que o sistema de metas evolua com seguranca, rastreabilidade e desempenho aceitavel, preservando as decisoes ja aprovadas do MVP.

## Estado Atual

O projeto Django inicial ja existe, com apps modulares e Docker Compose. A suite inicial ainda usa `unittest` para proteger decisoes criticas, seguranca, ERP somente leitura e contratos de dominio.

Comando:

```powershell
docker compose run --rm web python -m unittest discover -s tests -v
```

## Camadas De Teste

- Guardrails documentais: confirmam que as decisoes criticas continuam registradas.
- Guardrails de seguranca: procuram credenciais ou tokens obvios em arquivos do projeto.
- Guardrails do ERP: impedem SQL de escrita dentro do futuro app `erp_readonly`.
- Contratos de dominio: definem o comportamento esperado antes da implementacao Django.
- Contratos de modelos: protegem FKs, tabelas de hierarquia/catalogo e regras de movimentacao.
- Contratos de metas: protegem ciclos mensais, metas globais por grupo e quantidades positivas em kg.
- Contratos de distribuicao: protegem lotes, linhas, eventos, origens, destinos e fechamento por soma das linhas.
- Contratos de escopo hierarquico: protegem origem ativa com vinculo vigente e destino ativo dentro da cadeia comercial da origem.
- Contratos de contas e escopo de usuario: protegem perfil operacional, escopo comercial correspondente e consulta de vinculos vigentes por usuario.
- Contratos de fluxo web: protegem login, criacao de ciclo/meta, criacao de distribuicao, linha e envio.
- Testes Django futuros: devem cobrir modelos, servicos, formularios, views, permissoes e consultas.

## Contratos Obrigatorios

### Fechamento 100%

O validador de distribuicao deve:

- receber a meta recebida em kg;
- receber a lista de valores distribuidos em kg;
- permitir envio somente quando a soma fechar exatamente a meta recebida;
- bloquear envio quando houver sobra;
- bloquear envio quando houver falta;
- usar `Decimal` ou equivalente seguro para evitar erro de ponto flutuante;
- retornar a diferenca para exibicao ao usuario e auditoria.

Contrato inicial esperado:

```python
allocations.services.validation.evaluate_distribution_closure(
    received_kg,
    allocated_kg_values,
)
```

Retorno esperado:

- `can_send`
- `difference_kg`

Status atual: implementado em `allocations.services.validation`.

### ERP Somente Leitura

Os testes devem:

- usar fake, mock ou fixture local;
- nunca depender do ERP real;
- falhar se SQL de escrita aparecer no app `erp_readonly`;
- cobrir timeout, indisponibilidade e respostas vazias quando o adaptador for implementado.

### Permissoes E Hierarquia

Quando o Django existir, os testes devem cobrir:

- gerente criando e distribuindo metas globais;
- coordenador regional vendo apenas seu escopo;
- coordenador local como etapa obrigatoria entre regional e supervisor;
- supervisor distribuindo somente para seus vendedores;
- vendedor consultando apenas sua meta final;
- administrador mantendo cadastros sem quebrar rastreabilidade.
- perfil de usuario ligado ao escopo comercial correto.
- movimentacoes criando historico de vigencia.
- inativacoes sem exclusao fisica de registros historicos.
- distribuicoes recusando destinos fora do escopo vigente da origem.
- distribuicoes excluindo pessoas inativas das opcoes operacionais.

### Ciclos E Metas Globais

Os modelos iniciais devem garantir:

- um unico ciclo por mes/ano;
- mes valido entre 1 e 12;
- uma unica meta global por ciclo e grupo;
- quantidade em kg maior que zero;
- quantidade em kg armazenada sem casas decimais.

### Distribuicoes

Os modelos iniciais devem garantir:

- lote vinculado a ciclo, meta global, grupo e origem;
- linha vinculada a lote e destino;
- quantidades recebidas e distribuidas maiores que zero;
- origem e destino coerentes com o nivel escolhido;
- origem ativa com vinculo vigente na hierarquia;
- destino ativo no proximo nivel direto permitido e dentro do escopo vigente da origem;
- fechamento do lote calculado pela soma das linhas;
- tentativa de envio marcada como enviada quando fecha 100%;
- tentativa de envio marcada como bloqueada quando ha sobra ou falta;
- evento de distribuicao registrando recebido, distribuido, diferenca e status.

### Fluxo Web Manual

As telas iniciais devem permitir:

- login proprio do Django;
- criacao de ciclo mensal;
- criacao de meta global por grupo;
- criacao de lote de distribuicao a partir da meta global;
- criacao de linha de distribuicao;
- tentativa de envio com status `ENVIADA` ou `BLOQUEADA`.

### Importacao Excel

Os layouts oficiais estao definidos em `docs/IMPORT_LAYOUTS.md`.

Os testes devem cobrir:

- arquivo valido;
- colunas obrigatorias ausentes;
- duplicidades;
- referencias de hierarquia inexistentes;
- conflito de codigo com nomes diferentes;
- linhas invalidas;
- registro da importacao e dos erros.

## Desempenho

Quando houver views e consultas Django, incluir testes de:

- limite de queries em telas principais;
- ausencia de consultas ao ERP em loops por destinatario;
- uso de fake/mock para historico de vendas;
- paginacao ou filtros em listagens grandes;
- tempo controlado para validacoes de importacao.

## Regras De Seguranca

- Nao versionar credenciais reais.
- Nao gravar no ERP.
- Nao usar o ERP real em teste automatizado.
- Nao permitir envio com sobra ou falta.
- Nao esconder ajustes manuais nem bloqueios; eles devem gerar rastreabilidade.
