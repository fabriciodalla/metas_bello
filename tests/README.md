# Testes

Esta pasta guarda a suite inicial de seguranca, invariantes e contratos do projeto METAS_BELLO.

## Como Rodar

```powershell
python -m unittest discover -s tests -v
```

## Camadas Atuais

- `test_documentation_guardrails.py`: protege decisoes criticas ja documentadas.
- `test_security_guardrails.py`: procura atribuicoes obvias de segredos em arquivos do projeto.
- `test_erp_readonly_guardrails.py`: impede SQL de escrita dentro do futuro app `erp_readonly`.
- `test_allocation_closure_contract.py`: define o contrato da validacao de fechamento 100%.

Os testes de contrato podem aparecer como `skipped` enquanto os apps Django ainda nao existem. Quando os modulos forem criados, eles passam a validar a implementacao real.

## Prioridades Para A Implementacao Django

- Fechamento exato em 100%, sobra e falta.
- Permissoes por perfil e escopo hierarquico.
- Auditoria de criacao, ajuste, bloqueio e liberacao.
- Sugestao por historico usando fake/mock do ERP.
- Importacao Excel com arquivo valido, invalido, duplicado e referencias ausentes.
- Testes de consulta com limites de queries para evitar degradacao em telas principais.
