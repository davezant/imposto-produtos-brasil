# Instruções para agentes de IA

Este arquivo orienta LLMs e agentes (Claude Code, Codex, Cursor, Copilot etc.) que editam este repositório.
Pessoas também podem ler: é um resumo das regras do projeto.

## O projeto

Base aberta de impostos sobre produtos vendidos no Brasil, organizada por código NCM: Imposto de Importação (TEC),
IPI (TIPI), PIS/COFINS, ICMS e regimes especiais. Os dados ficam em CSV para que pessoas sem conhecimento técnico
consigam editar. A documentação e as mensagens são em português do Brasil: escreva assim também.

## Regras que nunca podem ser quebradas

1. **Nunca invente, estime ou "complete de memória" uma alíquota, NCM, data ou ato legal.** Todo valor tributário
   precisa vir de uma fonte oficial (Diário Oficial, Receita Federal, Camex/MDIC, Siscomex, SPED, legislação estadual).
   Se não tiver a fonte, não altere o dado: diga isso ao usuário.
2. **Os CSVs são a única fonte editável.** SQLite, JSON e API (`dist/`) são gerados; nunca edite nem commite `dist/`.
3. **Não edite à mão os arquivos gerados das fontes oficiais**, porque a próxima atualização os sobrescreve:
   - `ncm/**/capitulo-*.csv`
   - `aliquotas/federal/TEC/*.csv` (inclusive `excecoes.csv`)
   - `aliquotas/federal/TIPI/*.csv`
   - `aliquotas/federal/PIS_COFINS/excecoes.csv`

   Para mudar esses arquivos, altere `tools/atualizar_dados.py` e rode-o de novo.
   Os arquivos mantidos manualmente são `aliquotas/estadual/padrao.csv`, `aliquotas/especial/padrao.csv` e
   `aliquotas/federal/PIS_COFINS/padrao.csv`.
4. **Sempre valide antes de concluir:** `python tools/validar_dados.py`. A tarefa não está pronta com erros.
5. **Não renomeie nem reordene colunas sem atualizar o `schema.json`** e registrar a mudança no `CHANGELOG.txt`
   (seção "Estrutura"), porque isso quebra integrações. Os nomes de arquivo fazem parte do
   contrato público.

## Mapa do repositório

| caminho | conteúdo |
|---|---|
| `schema.json` | definição de todas as tabelas: colunas, tipos, obrigatoriedade, chaves. **Leia antes de mexer em dados** |
| `manifest.json` | índice de arquivos por intervalo de capítulos, fontes oficiais e versão |
| `ncm/<intervalo>/capitulo-XX.csv` | nomenclatura NCM (todos os níveis) |
| `aliquotas/federal/TEC/` | Imposto de Importação por NCM + `excecoes.csv` |
| `aliquotas/federal/TIPI/` | IPI por NCM e Ex |
| `aliquotas/federal/PIS_COFINS/` | `padrao.csv` (padrão) + `excecoes.csv` (regimes por NCM) |
| `aliquotas/estadual/padrao.csv` | ICMS padrão por UF e interestadual |
| `aliquotas/especial/padrao.csv` | regimes especiais (remessas internacionais) |
| `tools/` | scripts Python (ver abaixo) |
| `docs/` | documentação para pessoas; cada pasta de dados também tem um `README.md` com as colunas |

Os intervalos de capítulos (`01-05`, `06-14`, ...) estão em `manifest.json` → `intervalos`. Um NCM vai no arquivo do
intervalo que contém os dois primeiros dígitos dele.

## Comandos

```bash
python tools/validar_dados.py              # validar (sem dependências)
python tools/validar_dados.py --corrigir   # corrige formato: ';', vírgula decimal, BOM, encoding, espaços
python tools/gerar_distribuicao.py         # gera dist/ (SQLite, JSON, API); testa que tudo continua gerável
python tools/pesquisar_por_taxas_por_ncm.py 2203.00.00   # conferir o resultado de uma mudança
pip install -r tools/requirements.txt && python tools/atualizar_dados.py   # rebaixar as fontes oficiais
```

Os scripts usam só a biblioteca padrão do Python 3.10+, exceto `atualizar_dados.py` (precisa do `openpyxl`).
Não adicione dependências externas aos outros scripts.

## Formato dos dados (armadilhas comuns)

- **Alíquota em fração com ponto:** `0.18` = 18%. Nunca `18`, `18%` ou `0,18`.
- **`NT` ≠ `0`** na TIPI: `NT` = não tributado (fora do campo do IPI), `0.0000` = tributado com alíquota zero.
- **NCM com pontos:** `2203.00.00` (folha, 8 dígitos). Códigos mais curtos (`22`, `22.03`, `2203.1`) são agrupamentos
  e não têm alíquota.
- **Ex:** 2 dígitos na TIPI (`01`), 3 nas exceções da TEC (`001`). Vazio = regra geral do NCM.
- **Datas:** sempre `AAAA-MM-DD`. Data de fim vazia = sem fim.
- **Célula vazia** = "não se aplica"; na distribuição vira `null`.
- **CSV:** UTF-8 sem BOM, separador `,`, quebra de linha CRLF, aspas só quando o texto tem vírgula.
- **PIS/COFINS por NCM:** `ncm_prefixo` é um prefixo. Um NCM se enquadra se começar com ele. Linhas com
  `vigencia_fim` preenchida são históricas, não apague.
- **Avisos conhecidos:** a validação mostra hoje 5 avisos de NCMs da TIPI que não existem mais na NCM. Isso é um
  atraso da Receita, não um erro a corrigir.

## Receitas

**Corrigir ou adicionar um valor num arquivo manual** (ICMS, regimes especiais, PIS/COFINS padrão):
edite a linha, cite a fonte oficial no texto do commit/PR (e na coluna `observacao` ou `descricao`), atualize
`revisar_ate` para a próxima data em que o valor deve ser reconferido, rode o validador e registre a mudança no
`CHANGELOG.txt`. Um aviso de "revisão vencida" significa que alguém precisa conferir a fonte; não basta mudar a data.

**Atualizar os dados oficiais:** rode `tools/atualizar_dados.py`, depois o validador, e revise o `git diff`. Explique
ao usuário as mudanças de alíquota mais relevantes. Não "conserte" à mão diferenças que vieram da fonte.

**Adicionar uma coluna ou tabela:** altere o CSV, o `schema.json` (tipo, descrição, obrigatoriedade), o `README.md`
da pasta, o `manifest.json` se for um arquivo novo, e, se for gerado, `tools/atualizar_dados.py`. Confirme que
`tools/gerar_distribuicao.py` continua funcionando. Registre em "Estrutura" no `CHANGELOG.txt`.

**Mudar a API (`api/v1`):** só é permitido adicionar campos. Remover ou renomear exige uma nova versão (`api/v2`)
mantendo a `v1`.

## Ao responder perguntas sobre impostos com estes dados

- Diga de qual tabela e de qual versão (`manifest.json` → `info.versao`, `referencias`) o valor veio.
- Deixe claro o que os dados **não** cobrem: ICMS por produto, substituição tributária e benefícios estaduais, regimes
  aduaneiros especiais e a transição da reforma tributária (CBS/IBS/IS).
- Os dados servem para estimativa e estudo e não substituem um contador ou a legislação.

## Git

Mensagens de commit em português, no estilo do histórico ("Atualizando ...", "Adicionando ..."). Mudanças em dados
tributários precisam citar a fonte oficial na descrição do PR (o modelo do PR já pede isso).
