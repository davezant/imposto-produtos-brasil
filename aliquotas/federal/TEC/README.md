# TEC - Imposto de Importação (II)

Fonte: Camex/MDIC, Anexos I a X da Resolução Gecex nº 272/2021
(<https://www.gov.br/mdic/pt-br/assuntos/camex/se-camex/strat/tarifas/vigentes>).
Gerado por `tools/atualizar_dados.py`; a versão do ato está em `manifest.json` → `referencias`.

## `XX-YY.csv` (um por intervalo de capítulos)

Uma linha para **cada** código NCM folha (8 dígitos).

| coluna | descrição |
|---|---|
| `codigo_ncm` | NCM no formato `0000.00.00` |
| `aliquota` | alíquota do II **aplicada pelo Brasil**, em fração (`0.1260` = 12,6%). É a do Anexo II quando o Brasil aplica alíquota diferente da TEC; senão, a do Anexo I |
| `aliquota_tec_mercosul` | alíquota da Tarifa Externa Comum do Mercosul (Anexo I) |
| `bit_bk` | `BIT` (bens de informática e telecomunicações) ou `BK` (bens de capital), quando marcado na TEC |

## `excecoes.csv`

Alíquotas temporárias, por Ex-tarifário ou com quota. Elas **substituem** a alíquota acima apenas
dentro da vigência, da quota e da descrição do Ex.

| coluna | descrição |
|---|---|
| `anexo` | IV (desabastecimento), V (LETEC), VI (LEBITBK), VIII (concessões OMC), IX (DCC - elevações), X (automotivos ACE-14) |
| `codigo_ncm`, `ex` | NCM e número do Ex-tarifário (vazio = NCM inteiro) |
| `descricao` | descrição do produto/Ex |
| `aliquota` | fração |
| `quota`, `unidade_quota` | limite quantitativo, quando houver |
| `vigencia_inicio`, `vigencia_fim` | datas ISO (`AAAA-MM-DD`); fim vazio = indeterminado |
| `ato`, `observacao` | ato legal de inclusão e observações da Camex |

O Anexo III (regra do setor aeronáutico) e o Anexo VII não são listados aqui.
