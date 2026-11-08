# TIPI - Imposto sobre Produtos Industrializados (IPI)

Fonte: Receita Federal, `tipi.xlsx`
(<https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/legislacao/tipi-tabela-de-incidencia-do-imposto-sobre-produtos-industrializados>).
Gerado por `tools/atualizar_dados.py`; o último ato considerado está em `manifest.json` → `referencias`.

## `XX-YY.csv` (um por intervalo de capítulos)

Uma linha para **cada** código NCM folha da TIPI, mais uma linha por Ex-tarifário.

| coluna | descrição |
|---|---|
| `codigo_ncm` | NCM no formato `0000.00.00` |
| `ex` | número do Ex da TIPI (vazio = alíquota geral do código) |
| `aliquota` | fração (`0.0325` = 3,25%) **ou** `NT` (não tributado: o produto está fora do campo de incidência do IPI). `0.0000` significa tributado com alíquota zero |
| `descricao_ex` | descrição do Ex (vazio na linha geral) |

A ausência de um NCM aqui significa que ele não consta na TIPI vigente.
A TIPI pode conter poucos códigos que já foram alterados na NCM e ainda não foram atualizados pela Receita;
o script de atualização lista esses casos como aviso.
