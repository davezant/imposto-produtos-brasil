# Impostos Estaduais

## `padrao.csv` - ICMS

Alíquota **interna padrão (modal)** de cada UF, com o adicional do Fundo de Combate à Pobreza (FCP), e as
alíquotas interestaduais. Tabela mantida manualmente.

| coluna | descrição |
|---|---|
| `id` | identificador |
| `tipo_operacao` | `interna` (dentro da UF) ou `interestadual` |
| `uf` | sigla da UF; obrigatória nas internas e vazia nas interestaduais |
| `aliquota` | fração |
| `fcp` | adicional do fundo de pobreza, em fração |
| `aliquota_efetiva` | `aliquota + fcp` (o validador confere a soma) |
| `descricao` | quando a alíquota se aplica, com a base legal |
| `revisar_ate` | data até a qual o valor deve ser reconferido na fonte oficial; o validador avisa quando a data passa |

**Limitação:** não cobre alíquotas específicas por produto, substituição tributária (ST/MVA),
reduções de base de cálculo nem benefícios fiscais estaduais.
