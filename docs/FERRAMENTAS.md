# Ferramentas

Scripts em Python 3.10+ na pasta `tools/`. Podem ser executados de qualquer diretório.

| comando | o que faz |
|---|---|
| `python tools/pesquisar_por_taxas_por_ncm.py 2203.00.00` | mostra a hierarquia do NCM, II, IPI (incluindo Ex), exceções do II e regimes de PIS/COFINS vigentes |
| `python tools/pesquisar_ncm_pelo_nome.py cerveja` | busca códigos NCM pela descrição (ignora acentos e maiúsculas) |
| `python tools/mostrar_tabela_de_aliquotas_fixas.py` | lista as alíquotas que não dependem do NCM (PIS/COFINS padrão, ICMS por UF, regimes especiais) |
| `python tools/mostrar_referências.py` | mostra as fontes oficiais e as versões usadas |
| `python tools/validar_dados.py [--corrigir]` | valida todos os CSVs contra o `schema.json` e corrige problemas de formato |
| `python tools/gerar_distribuicao.py` | gera `dist/` com SQLite, JSON, CSV consolidado e a API estática (ver [Integração](INTEGRACAO.md)) |
| `python tools/atualizar_dados.py` | baixa as fontes oficiais e regenera NCM, TEC, TIPI e PIS/COFINS (requer `pip install -r tools/requirements.txt`) |

Exceto `atualizar_dados.py`, nenhum script tem dependências externas.

## Automação (GitHub Actions)

| workflow | quando | o que faz |
|---|---|---|
| `validar.yml` | todo PR e push | valida os dados e testa a geração da distribuição |
| `publicar.yml` | push na `main` e tags `v*` | publica a distribuição no GitHub Pages; em tags, cria uma Release |
| `atualizar.yml` | toda segunda-feira | baixa as fontes oficiais e abre um PR se algo mudou |
