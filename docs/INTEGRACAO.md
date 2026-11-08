# Integração

Os CSVs do repositório são a fonte que as pessoas editam. A partir deles, o CI gera automaticamente uma
**distribuição** pronta para sistemas, publicada no GitHub Pages a cada merge na `main`:

`https://davezant.github.io/imposto-produtos-brasil/`

Nada disso fica commitado na `main`, então quem edita os CSVs não vê arquivos gerados nem conflitos.

## Qual formato usar

| Você tem | Use |
|---|---|
| Um app/site que consulta um produto por vez | `api/v1/ncm/<8 dígitos>.json`: um GET, sem chave, sem servidor |
| Um sistema com banco ou consultas em lote | `impostos.sqlite` (todas as tabelas, indexadas) |
| Planilha, BI, pandas, R | `csv/<tabela>.csv` ou `json/<tabela>.json` |
| Validação/ETL com ferramentas de dados | `datapackage.json` (Frictionless Data) |
| Um assistente de IA ou agente | `llms.txt`: explica a API e as convenções em texto para LLMs |
| Precisa fixar uma versão | arquivos anexados às [Releases](https://github.com/davezant/imposto-produtos-brasil/releases) (`v0.8.0`, ...) |

`api/v1/meta.json` lista a versão, a data de geração, as fontes oficiais e os links de todas as tabelas.

## Convenções da distribuição

- Alíquotas em **fração** (`0.18` = 18%).
- `nao_tributado: true` = NT na TIPI (fora do campo do IPI), diferente de alíquota `0`.
- Datas em ISO `AAAA-MM-DD`; `null` = sem data de fim.
- Toda coluna de NCM tem uma versão só com dígitos: `codigo_ncm_digitos = "22030000"`.
- Regras com `vigente: false` são históricas.
- A API segue `v1`: campos podem ser **adicionados** sem aviso, mas remover ou renomear campos gera `v2`.

## Exemplos

### HTTP / curl

```bash
curl -s https://davezant.github.io/imposto-produtos-brasil/api/v1/ncm/22030000.json \
  | jq '{ii: .imposto_importacao.aliquota, ipi: .ipi.aliquota}'
```

### JavaScript

```js
const BASE = "https://davezant.github.io/imposto-produtos-brasil/";
const ncm = await (await fetch(`${BASE}api/v1/ncm/22030000.json`)).json();
console.log(ncm.imposto_importacao.aliquota, ncm.ipi.aliquota);
```

### Python

```python
import json, urllib.request
BASE = "https://davezant.github.io/imposto-produtos-brasil/"
ncm = json.load(urllib.request.urlopen(BASE + "api/v1/ncm/22030000.json"))
print(ncm["imposto_importacao"]["aliquota"], ncm["ipi"]["aliquota"])
```

### SQL (SQLite)

```sql
-- II e IPI de um NCM
SELECT * FROM v_impostos_ncm WHERE codigo_ncm_digitos = '22030000';

-- regimes de PIS/COFINS vigentes que se aplicam a um NCM (casamento por prefixo)
SELECT tipo, aliquota_pis, aliquota_cofins, valor_pis_por_unidade, unidade, descricao
FROM v_pis_cofins_vigente
WHERE '22030000' LIKE ncm_prefixo_digitos || '%';

-- exceções do Imposto de Importação
SELECT anexo, ex, aliquota, vigencia_fim, descricao FROM tec_excecoes WHERE codigo_ncm = '8703.40.00';
```

Tabelas do SQLite: `ncm`, `tec`, `tec_excecoes`, `tipi`, `pis_cofins_padrao`, `pis_cofins_excecoes`, `icms`,
`regras_especiais`, `metadados`; visões `v_impostos_ncm` e `v_pis_cofins_vigente`. As colunas estão descritas no
[`schema.json`](../schema.json).

### pandas

```python
import pandas as pd
tec = pd.read_csv("https://davezant.github.io/imposto-produtos-brasil/csv/tec.csv", dtype=str)
```

### Direto do repositório (sem distribuição)

Os CSVs originais também podem ser lidos direto do GitHub ou via jsDelivr, fixando uma tag:

```
https://cdn.jsdelivr.net/gh/davezant/imposto-produtos-brasil@v0.8.0/aliquotas/federal/TEC/84-85.csv
```

Nesse caso, use o `manifest.json` para achar o arquivo de cada capítulo e o `schema.json` para os tipos.

## Gerar localmente

```bash
python tools/gerar_distribuicao.py   # cria dist/ (sem dependências externas)
python -m http.server -d dist        # http://localhost:8000
```
