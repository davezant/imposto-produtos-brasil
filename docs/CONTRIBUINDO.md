# Contribuição

Qualquer pessoa pode contribuir com o projeto. Não é necessário ser especialista em tributação para colaborar.

##### Formas de contribuição

- **Revisão de dados**: Verificar a precisão das planilhas, corrigir erros de digitação e adicionar mudanças tributárias recentes.

- **Design e Documentação**: Melhorar a apresentação visual, criar diagramas explicativos, organizar a estrutura dos guias e tornar o material legível.

- **Divulgação**: Compartilhar o repositório com outras pessoas, indicar o projeto em comunidades e expandir o alcance da ferramenta.

- **Desenvolvimento**: Propor melhorias técnicas mantendo a estrutura original.

- **Reporte de problemas**: Abrir chamados para indicar inconsistências nos dados ou sugerir melhorias.

##### Como editar os dados

Os dados são CSVs comuns: abra no Excel, LibreOffice ou Google Sheets. Edite **só os CSVs**. SQLite, JSON e API são
gerados automaticamente depois do merge.

- Alíquotas em fração com ponto: `0.18` (não `18%` nem `0,18`).
- NCM com pontos: `2203.00.00`.
- Não renomeie nem reordene colunas. Se precisar de uma coluna nova, altere também o `schema.json`.
- NCM, TEC, TIPI e PIS/COFINS por NCM são gerados das fontes oficiais por `tools/atualizar_dados.py`, e um robô
  abre um PR toda semana quando algo muda. Para corrigir esses dados, prefira abrir uma issue com a fonte oficial,
  porque uma edição manual pode ser sobrescrita na próxima atualização.

Usa um assistente de IA (Claude Code, Codex, Cursor, Copilot...) para editar? Ele lê o
[`AGENTS.md`](../AGENTS.md), que traz as regras do projeto, como nunca inventar alíquotas sem fonte oficial.

Antes de enviar, valide:

```bash
python tools/validar_dados.py --corrigir
```

O `--corrigir` resolve sozinho os problemas comuns de quem salva pelo Excel (separador `;`, vírgula decimal,
arquivo fora de UTF-8, BOM, espaços sobrando). O que sobrar é erro de conteúdo, com arquivo e linha indicados.
Não tem Python? Envie o PR mesmo assim: a validação roda automaticamente e mostra os erros no próprio PR.

##### Como fazer Pull Request

1. Faça um fork do repositório.
2. Crie uma branch para a sua alteração.
3. Adicione ou edite os registros ou arquivos de documentação.
4. Abra um Pull Request detalhando as alterações (o modelo do PR pede as informações necessárias).
5. Se a alteração envolver dados tributários, inclua a fonte oficial dos dados (como Diário Oficial da União ou normativas da Receita Federal).

Nenhuma alteração tributária é aceita ***sem comprovação documental da fonte***. Essa exigência sustenta a confiabilidade do projeto.
