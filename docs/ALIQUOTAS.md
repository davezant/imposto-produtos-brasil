# Alíquotas

| tributo | pasta | cobertura | fonte |
|---|---|---|---|
| Imposto de Importação (II) | `aliquotas/federal/TEC` | todos os NCM + exceções (LETEC, LEBITBK, desabastecimento, DCC, OMC, automotivos) | Camex - Res. Gecex 272/2021 |
| IPI | `aliquotas/federal/TIPI` | todos os NCM da TIPI + Ex-tarifários | Receita Federal - TIPI |
| PIS/COFINS | `aliquotas/federal/PIS_COFINS` | regimes padrão + regimes diferenciados por NCM (monofásico, alíquota zero, ST, isenção, suspensão...) | Tabelas SPED 4.3.10 a 4.3.17 |
| ICMS | `aliquotas/estadual` | alíquota interna padrão por UF, FCP e interestaduais | legislação estadual |
| Regimes especiais | `aliquotas/especial` | remessas internacionais (Remessa Conforme) | Lei 14.902/2024, MP 1.357/2026 |

## Convenções

- Alíquotas percentuais são guardadas em **fração**: `0.0325` = 3,25%.
- `NT` (só na TIPI) = não tributado, diferente de `0`.
- NCM sempre no formato com pontos (`0000.00.00`).
- Datas novas estão em ISO (`AAAA-MM-DD`). As tabelas de NCM mantêm o formato da fonte (`DD/MM/AAAA`, com `31/12/9999` = sem fim).
- Arquivos CSV em UTF-8 com quebra de linha CRLF (abrem diretamente no Excel/LibreOffice).
- Cada pasta tem um `README.md` descrevendo as colunas.

## Atualização

NCM, TEC, TIPI e PIS/COFINS por NCM são gerados a partir das fontes oficiais:

```bash
pip install -r tools/requirements.txt
python tools/atualizar_dados.py --versao X.Y
```

ICMS e regimes especiais são mantidos manualmente: qualquer alteração exige a fonte oficial no Pull Request.

## Limitações

Estes dados servem para estimativa e estudo. Eles **não** substituem a orientação de um contador nem a
legislação. Não estão cobertos, por exemplo: ICMS por produto e ST, benefícios regionais (ZFM, Sudene),
regimes aduaneiros especiais e a transição da reforma tributária (CBS/IBS/IS).
