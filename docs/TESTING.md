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
- coordenador local conforme responsabilidade definida;
- supervisor distribuindo somente para seus vendedores;
- vendedor consultando apenas sua meta final;
- administrador mantendo cadastros sem quebrar rastreabilidade.

### Importacao Excel

Quando o layout for definido, os testes devem cobrir:

- arquivo valido;
- colunas obrigatorias ausentes;
- duplicidades;
- referencias de hierarquia inexistentes;
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
