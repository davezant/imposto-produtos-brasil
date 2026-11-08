# PIS/PASEP e COFINS

## `padrao.csv` - regimes padrão (mantido manualmente)

Alíquotas gerais que valem quando o produto **não** tem regime diferenciado.

| coluna | descrição |
|---|---|
| `id` | identificador do regime |
| `tipo` | `Interno`, `Importacao` ou ambos |
| `aliquota_pis`, `aliquota_cofins` | fração (`0.0165` = 1,65%) |
| `revisar_ate` | data até a qual o valor deve ser reconferido; o validador avisa quando a data passa |

## `excecoes.csv` - regimes diferenciados por produto

Fonte: tabelas externas oficiais do SPED EFD-Contribuições (Receita Federal), versões registradas em
`manifest.json` → `referencias.aliquotas.federal.PIS/COFINS.tabelas_sped`. Gerado por `tools/atualizar_dados.py`.

Uma linha por regra **e** por prefixo de NCM. Para saber se um NCM se enquadra, verifique se o código começa com
`ncm_prefixo`. Regras com `ncm_prefixo` vazio são descritas só em texto (ex.: "adubos do Capítulo 31").
Linhas com `vigencia_fim` preenchida são históricas.

| coluna | descrição |
|---|---|
| `tabela_sped` | 4.3.10 a 4.3.17 |
| `tipo` | `monofasica_aliquota_diferenciada`, `monofasica_aliquota_por_unidade`, `substituicao_tributaria`, `aliquota_zero`, `isencao`, `nao_incidencia`, `suspensao`, `aliquota_diferenciada` |
| `cst` | Código de Situação Tributária correspondente |
| `codigo` | código da regra na tabela SPED |
| `descricao` | descrição oficial (contém as condições de aplicação) |
| `vigencia_inicio`, `vigencia_fim` | datas ISO |
| `ncm_prefixo` | prefixo de NCM (2 a 8 dígitos) |
| `ncm_ex`, `ex_ipi` | Ex associado, quando houver |
| `aliquota_pis`, `aliquota_cofins` | fração (tabelas 4.3.10 e 4.3.12) |
| `valor_pis_por_unidade`, `valor_cofins_por_unidade`, `unidade` | alíquota em R$ por unidade (tabela 4.3.11) |
| `aliquota_pis_p`, `aliquota_pis_r`, `aliquota_cofins_p`, `aliquota_cofins_r` | só na tabela 4.3.17: correspondem às colunas oficiais `ALIQ_PIS_P`, `ALIQ_PIS_R`, `ALIQ_COF_P` e `ALIQ_COF_R`. O leiaute da tabela não documenta o significado de "P" e "R"; consulte a `descricao` e a legislação citada nela |
