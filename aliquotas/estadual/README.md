# Impostos Estaduais

## `standart.csv` - ICMS

Alíquota **interna padrão (modal)** de cada UF, o adicional do Fundo de Combate à Pobreza (FCP)
e as alíquotas interestaduais (Resolução do Senado 22/1989 e 13/2012).

| coluna | descrição |
|---|---|
| `id` | identificador |
| `tipo` | UF ou `Interestadual` |
| `aliquota_interna` | fração |
| `fcp` | adicional do fundo de pobreza, em fração |
| `aliquota_efetiva` | `aliquota_interna + fcp` |

**Limitação:** não cobre alíquotas específicas por produto, substituição tributária (ST/MVA),
reduções de base de cálculo nem benefícios fiscais estaduais.
