# Alíquotas Especiais

## `padrao.csv`

Regimes que não dependem do NCM, como o Imposto de Importação das remessas internacionais
(Programa Remessa Conforme, "taxa das blusinhas"). Tabela mantida manualmente.

| coluna | descrição |
|---|---|
| `id` | identificador |
| `descricao` | situação em que se aplica |
| `tipo_taxa` | tributo |
| `base_incidencia` | sobre o que a alíquota incide |
| `aliquota` | fração |
| `observacao` | base legal e condições |
| `revisar_ate` | data até a qual o valor deve ser reconferido na fonte oficial; o validador avisa quando a data passa |
