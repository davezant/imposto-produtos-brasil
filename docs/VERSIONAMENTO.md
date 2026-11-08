# Versionamento

O projeto usa versões no formato `MAJOR.MINOR.PATCH` (ex.: `1.2.0`), marcadas com tags `vX.Y.Z`. Cada tag gera uma
[Release](https://github.com/davezant/imposto-produtos-brasil/releases) com o SQLite e os zips de CSV/JSON, para
quem precisa fixar uma versão.

## O que muda cada número

| mudança | exemplos | versão |
|---|---|---|
| **Quebra quem integra** | renomear ou remover coluna, arquivo, tabela, campo da API ou valor permitido; mudar o formato de um valor (ex.: datas); mudar o significado de uma coluna | **MAJOR** |
| **Adiciona sem quebrar** | nova tabela, nova coluna no fim, novo campo na API, novo tributo, atualização periódica das fontes oficiais | **MINOR** |
| **Corrige** | dado errado corrigido com fonte oficial, documentação, correção de bug nas ferramentas | **PATCH** |

Atualizações de alíquotas pelas fontes oficiais são MINOR, mesmo quando mudam muitos valores: o formato continua o mesmo.

Antes da 1.0, mudanças que quebram integrações ainda podem acontecer em versões MINOR (`0.8` → `0.9`), sempre
listadas na seção "Estrutura" do `CHANGELOG.txt`.

## O que é o contrato público

- nomes e caminhos dos arquivos CSV, nomes e ordem das colunas, tipos e valores permitidos (`schema.json`);
- as chaves do `manifest.json`;
- os campos da API (`api/v1/schema-ncm.json`) e as tabelas/visões do SQLite.

## API

A API tem versão própria no caminho (`api/v1/`). Na `v1`, campos podem ser adicionados; nunca são removidos nem
renomeados. Uma mudança que quebre a API cria `api/v2/`, e a `v1` continua sendo publicada por pelo menos 6 meses.

## Onde ver a versão

- `manifest.json` → `info.versao` e `info.gerado_em`
- `api/v1/meta.json` e o campo `fontes` de cada resposta da API
- tabela `metadados` do SQLite
