"""
Valida todos os dados do repositório contra o schema.json.

Uso:
    python tools/validar_dados.py              # só valida
    python tools/validar_dados.py --corrigir   # corrige o que for seguro e valida de novo
    python tools/validar_dados.py --estrito    # avisos também fazem a validação falhar

Correções automáticas (--corrigir), pensadas para quem edita no Excel/LibreOffice:
- remove BOM e converte o arquivo para UTF-8 (se estiver em Latin-1/Windows-1252);
- troca separador ';' por ',';
- padroniza quebras de linha (CRLF);
- remove espaços no início/fim das células;
- troca vírgula decimal por ponto nas colunas numéricas (0,0325 -> 0.0325).

Não depende de nenhuma biblioteca externa.
"""

import argparse
import csv
import glob
import io
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(ROOT, "schema.json")
MANIFEST_PATH = os.path.join(ROOT, "manifest.json")
HOJE = date.today().isoformat()
MAX_POR_REGRA = 10  # mensagens iguais por arquivo antes de resumir

RE = {
    "ncm": re.compile(r"^(\d{2}|\d{2}\.\d{2}|\d{4}\.\d|\d{4}\.\d{2}|\d{4}\.\d{2}\.\d|\d{4}\.\d{2}\.\d{2})$"),
    "ncm_folha": re.compile(r"^\d{4}\.\d{2}\.\d{2}$"),
    "ncm_prefixo": re.compile(r"^(\d{2}|\d{4}|\d{4}\.\d{1,2}|\d{4}\.\d{2}\.\d{1,2})$"),
    "ex": re.compile(r"^\d{2,3}$"),
    "inteiro": re.compile(r"^-?\d+$"),
    "numero": re.compile(r"^-?\d+(\.\d+)?$"),
    "fracao": re.compile(r"^\d+(\.\d+)?$"),
    "data_br": re.compile(r"^(\d{2})/(\d{2})/(\d{4})$"),
    "data_iso": re.compile(r"^(\d{4})-(\d{2})-(\d{2})$"),
}
TIPOS_NUMERICOS = {"inteiro", "numero", "fracao", "fracao_ou_nt"}
UFS = set("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split())


class Relatorio:
    def __init__(self):
        self.mensagens = []
        self._contagem = defaultdict(int)

    def add(self, nivel, arquivo, linha, msg, regra=None):
        chave = (arquivo, regra or msg)
        self._contagem[chave] += 1
        n = self._contagem[chave]
        if n <= MAX_POR_REGRA:
            self.mensagens.append((nivel, arquivo, linha, msg))
        elif n == MAX_POR_REGRA + 1:
            self.mensagens.append((nivel, arquivo, None, f"... mais ocorrências de: {regra or msg}"))

    def erro(self, arquivo, linha, msg, regra=None):
        self.add("erro", arquivo, linha, msg, regra)

    def aviso(self, arquivo, linha, msg, regra=None):
        self.add("aviso", arquivo, linha, msg, regra)

    @property
    def erros(self):
        return sum(1 for m in self.mensagens if m[0] == "erro")

    @property
    def avisos(self):
        return sum(1 for m in self.mensagens if m[0] == "aviso")

    def imprimir(self):
        github = os.environ.get("GITHUB_ACTIONS") == "true"
        for nivel, arquivo, linha, msg in self.mensagens:
            local = arquivo + (f":{linha}" if linha else "")
            print(f"[{nivel.upper()}] {local}: {msg}")
            if github:
                tipo = "error" if nivel == "erro" else "warning"
                pos = f",line={linha}" if linha else ""
                print(f"::{tipo} file={arquivo}{pos}::{msg}")


# --------------------------------------------------------------------------- leitura e correção

def ler_arquivo(caminho_rel, rel, corrigir):
    """Lê o CSV, aplicando (ou apontando) problemas de formato do arquivo. Retorna (cabecalho, linhas)."""
    caminho = os.path.join(ROOT, caminho_rel)
    bruto = open(caminho, "rb").read()
    alterado = False

    if bruto.startswith(b"\xef\xbb\xbf"):
        if corrigir:
            bruto, alterado = bruto[3:], True
        else:
            rel.erro(caminho_rel, None, "arquivo começa com BOM (marca do Excel). Rode com --corrigir", "bom")
            bruto = bruto[3:]
    try:
        texto = bruto.decode("utf-8")
    except UnicodeDecodeError:
        texto = bruto.decode("cp1252", errors="replace")
        if corrigir:
            alterado = True
        else:
            rel.erro(caminho_rel, None, "arquivo não está em UTF-8 (provavelmente salvo como Windows-1252/Latin-1). "
                                        "Rode com --corrigir ou salve como 'CSV UTF-8'", "encoding")

    primeira = texto.split("\n", 1)[0]
    delimitador = ","
    if primeira.count(";") > primeira.count(","):
        delimitador = ";"
        if corrigir:
            alterado = True
        else:
            rel.erro(caminho_rel, 1, "separador ';' em vez de ','. Rode com --corrigir", "delimitador")

    if "\r\n" in texto and re.search(r"(?<!\r)\n", texto):
        if corrigir:
            alterado = True
        else:
            rel.aviso(caminho_rel, None, "quebras de linha misturadas (CRLF e LF). Rode com --corrigir", "eol")

    linhas = list(csv.reader(io.StringIO(texto, newline=""), delimiter=delimitador))
    while linhas and not any(c.strip() for c in linhas[-1]):
        linhas.pop()
    if not linhas:
        rel.erro(caminho_rel, None, "arquivo vazio (precisa ao menos do cabeçalho)")
        return [], [], alterado
    return linhas[0], linhas[1:], alterado


def gravar_arquivo(caminho_rel, cabecalho, linhas):
    with open(os.path.join(ROOT, caminho_rel), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(cabecalho)
        w.writerows(linhas)


# --------------------------------------------------------------------------- validação de células

def validar_valor(tipo, valor):
    """Retorna None se válido, ou a mensagem de erro."""
    if tipo == "texto":
        return None
    if tipo == "fracao_ou_nt":
        if valor == "NT":
            return None
        tipo = "fracao"
    if tipo == "uf":
        return None if valor in UFS else "UF inválida"
    if tipo == "fracao":
        if "%" in valor:
            return "use fração, não percentual (3,25% -> 0.0325)"
        if not RE["fracao"].match(valor):
            return "alíquota deve ser um número com ponto decimal (ex.: 0.0325)"
        if float(valor) > 3:
            return "alíquota acima de 3 (300%): provavelmente foi digitada em percentual; use fração (ex.: 0.18)"
        return None
    if tipo in ("data_br", "data_iso"):
        m = RE[tipo].match(valor)
        if not m:
            return "data deve estar no formato " + ("DD/MM/AAAA" if tipo == "data_br" else "AAAA-MM-DD")
        d, mes = (int(m.group(1)), int(m.group(2))) if tipo == "data_br" else (int(m.group(3)), int(m.group(2)))
        if not (1 <= mes <= 12 and 1 <= d <= 31):
            return "data inexistente"
        return None
    padrao = RE.get(tipo)
    if padrao and not padrao.match(valor):
        dicas = {
            "ncm_folha": "NCM deve ter 8 dígitos no formato 0000.00.00",
            "ncm": "NCM deve estar no formato com pontos (ex.: 22, 22.03, 2203.00.00)",
            "ncm_prefixo": "prefixo de NCM inválido (ex.: 2710, 2710.12, 2710.12.59)",
            "ex": "Ex deve ter 2 ou 3 dígitos (ex.: 01)",
            "inteiro": "deve ser um número inteiro",
            "numero": "deve ser um número com ponto decimal",
        }
        return dicas.get(tipo, f"valor inválido para o tipo {tipo}")
    return None


def data_ordenavel(valor):
    m = RE["data_br"].match(valor)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return valor


# --------------------------------------------------------------------------- validação de tabelas

def validar_tabela(tabela, rel, corrigir):
    colunas = tabela["colunas"]
    nomes = [c["nome"] for c in colunas]
    arquivos = sorted(os.path.relpath(p, ROOT).replace(os.sep, "/")
                      for p in glob.glob(os.path.join(ROOT, tabela["arquivos"])))
    if not arquivos:
        rel.erro(tabela["arquivos"], None, f"nenhum arquivo encontrado para a tabela '{tabela['nome']}'")
    registros = []  # (arquivo, linha, dict)

    for arq in arquivos:
        cabecalho, linhas, alterado = ler_arquivo(arq, rel, corrigir)
        if not cabecalho:
            continue
        cab_limpo = [c.strip() for c in cabecalho]
        if cab_limpo != cabecalho:
            alterado = alterado or corrigir
            if not corrigir:
                rel.erro(arq, 1, "cabeçalho com espaços sobrando. Rode com --corrigir", "cabecalho-espaco")
        if cab_limpo != nomes:
            faltando = [n for n in nomes if n not in cab_limpo]
            sobrando = [n for n in cab_limpo if n not in nomes]
            detalhe = []
            if faltando:
                detalhe.append("faltando: " + ", ".join(faltando))
            if sobrando:
                detalhe.append("não previstas no schema.json: " + ", ".join(sobrando))
            if not detalhe:
                detalhe.append("ordem esperada: " + ", ".join(nomes))
            rel.erro(arq, 1, "colunas diferentes do schema.json (" + "; ".join(detalhe) + ")")
            continue

        novas = []
        for i, linha in enumerate(linhas, start=2):
            if not any(c.strip() for c in linha):
                rel.aviso(arq, i, "linha vazia", "linha-vazia")
                alterado = alterado or corrigir
                continue
            if len(linha) != len(nomes):
                rel.erro(arq, i, f"a linha tem {len(linha)} colunas, o esperado são {len(nomes)} "
                                 "(vírgula sem aspas dentro de um texto?)", "n-colunas")
                novas.append(linha)
                continue
            nova = []
            for col, valor in zip(colunas, linha):
                v = valor
                if v != v.strip(" \t\xa0"):
                    v = v.strip(" \t\xa0")
                    if not corrigir:
                        rel.aviso(arq, i, f"coluna '{col['nome']}': espaços no início/fim. Rode com --corrigir",
                                  "espacos")
                if col["tipo"] in TIPOS_NUMERICOS and re.match(r"^-?\d+,\d+$", v):
                    if corrigir:
                        v = v.replace(",", ".")
                    else:
                        rel.erro(arq, i, f"coluna '{col['nome']}': use ponto decimal ('{v}' -> "
                                         f"'{v.replace(',', '.')}'). Rode com --corrigir", "virgula-decimal")
                nova.append(v)
            if nova != linha:
                alterado = alterado or corrigir
            novas.append(nova)
            reg = dict(zip(nomes, nova))
            registros.append((arq, i, reg))

            for col in colunas:
                v = reg[col["nome"]]
                if v == "":
                    if col.get("obrigatorio"):
                        rel.erro(arq, i, f"coluna '{col['nome']}' é obrigatória", f"obrigatorio-{col['nome']}")
                    elif col.get("obrigatorio_se") and reg.get(col["obrigatorio_se"]):
                        rel.erro(arq, i, f"coluna '{col['nome']}' é obrigatória quando "
                                         f"'{col['obrigatorio_se']}' está preenchida")
                    elif col.get("obrigatorio_se_valor") and all(
                            reg.get(k) == v for k, v in col["obrigatorio_se_valor"].items()):
                        cond = ", ".join(f"{k} = {v}" for k, v in col["obrigatorio_se_valor"].items())
                        rel.erro(arq, i, f"coluna '{col['nome']}' é obrigatória quando {cond}")
                    continue
                if col["tipo"] in TIPOS_NUMERICOS and re.match(r"^-?\d+,\d+$", v):
                    continue  # já apontado como vírgula decimal
                problema = validar_valor(col["tipo"], v)
                if problema is None and "valores" in col and v not in col["valores"]:
                    problema = "valor não permitido; use um de: " + ", ".join(x or "(vazio)" for x in col["valores"])
                if problema is None and "padrao" in col and not re.match(col["padrao"], v):
                    problema = f"não segue o padrão {col['padrao']}"
                if problema:
                    rel.erro(arq, i, f"coluna '{col['nome']}' = '{v}': {problema}", f"tipo-{col['nome']}")
                if "soma_de" in col and problema is None:
                    try:
                        soma = sum(float(reg[c]) for c in col["soma_de"])
                        if abs(soma - float(v)) > 1e-9:
                            rel.erro(arq, i, f"coluna '{col['nome']}' deveria ser "
                                             f"{' + '.join(col['soma_de'])} = {round(soma, 6)}")
                    except ValueError:
                        pass

            if tabela.get("revisao") and reg.get(tabela["revisao"]) and RE["data_iso"].match(reg[tabela["revisao"]]):
                if reg[tabela["revisao"]] < HOJE:
                    rel.aviso(arq, i, f"revisão vencida em {reg[tabela['revisao']]}: confira o valor na fonte oficial "
                                      f"e atualize '{tabela['revisao']}'", "revisao")

            if "vigencia" in tabela:
                ini, fim = (reg[c] for c in tabela["vigencia"])
                if ini and fim and data_ordenavel(fim) < data_ordenavel(ini):
                    rel.erro(arq, i, "fim da vigência anterior ao início")

        if corrigir and alterado:
            gravar_arquivo(arq, cab_limpo, novas)
            print(f"corrigido: {arq}")

    if "chave" in tabela:
        vistos = {}
        for arq, i, reg in registros:
            k = tuple(reg[c] for c in tabela["chave"])
            if k in vistos:
                rel.erro(arq, i, f"registro duplicado ({', '.join(tabela['chave'])} = {', '.join(k)}); "
                                 f"primeira ocorrência em {vistos[k][0]}:{vistos[k][1]}", "duplicado")
            else:
                vistos[k] = (arq, i)
    return registros


# --------------------------------------------------------------------------- validações entre arquivos

def capitulo(ncm):
    return re.sub(r"\D", "", ncm)[:2]


def no_intervalo(cap, intervalo):
    ini, fim = (int(x) for x in intervalo.split("-"))
    return ini <= int(cap) <= fim


def validar_estrutura(schema, dados, rel):
    manifest = json.load(open(MANIFEST_PATH, encoding="utf-8"))
    intervalos = manifest.get("intervalos", [])

    # Referências do manifest apontam para arquivos existentes.
    def caminhos(no):
        if isinstance(no, dict):
            for v in no.values():
                yield from caminhos(v)
        elif isinstance(no, str) and no.endswith(".csv"):
            yield no
    referenciados = set()
    for chave, valor in manifest.items():
        if chave.startswith(("index-", "relacao-")):
            for p in caminhos(valor):
                referenciados.add(p)
                if not os.path.exists(os.path.join(ROOT, p)):
                    rel.erro("manifest.json", None, f"'{chave}' aponta para arquivo inexistente: {p}")

    # Todo CSV de dados está no schema e no manifest.
    cobertos = set()
    for t in schema["tabelas"]:
        for p in glob.glob(os.path.join(ROOT, t["arquivos"])):
            cobertos.add(os.path.relpath(p, ROOT).replace(os.sep, "/"))
    for pasta in ("ncm", "aliquotas"):
        for p in glob.glob(os.path.join(ROOT, pasta, "**", "*.csv"), recursive=True):
            r = os.path.relpath(p, ROOT).replace(os.sep, "/")
            if r not in cobertos:
                rel.erro(r, None, "CSV não descrito em nenhuma tabela do schema.json")
            if r not in referenciados:
                rel.aviso(r, None, "CSV não referenciado no manifest.json")

    # Arquivos de NCM: capítulo e intervalo corretos; índice do manifest coerente.
    for iv, caps in manifest.get("index-ncm", {}).items():
        for cap, p in caps.items():
            m = re.search(r"ncm/(\d{2}-\d{2})/capitulo-(\d{2})\.csv$", p)
            if not m or m.group(1) != iv or m.group(2) != cap:
                rel.erro("manifest.json", None, f"index-ncm[{iv}][{cap}] aponta para {p}")
    for arq, i, reg in dados.get("ncm", []):
        m = re.search(r"ncm/(\d{2}-\d{2})/capitulo-(\d{2})\.csv$", arq)
        if m and capitulo(reg["codigo_ncm"]) != m.group(2):
            rel.erro(arq, i, f"NCM {reg['codigo_ncm']} não pertence ao capítulo {m.group(2)}", "capitulo")
        if m and not no_intervalo(m.group(2), m.group(1)):
            rel.erro(arq, None, f"capítulo {m.group(2)} fora da pasta {m.group(1)}", "pasta")
        if m and m.group(1) not in intervalos:
            rel.erro(arq, None, f"pasta {m.group(1)} não está em 'intervalos' do manifest", "intervalo")

    # TEC/TIPI: cada arquivo só contém capítulos do seu intervalo.
    for nome in ("tec", "tipi"):
        for arq, i, reg in dados.get(nome, []):
            m = re.search(r"/(\d{2}-\d{2})\.csv$", arq)
            if m and not no_intervalo(capitulo(reg["codigo_ncm"]), m.group(1)):
                rel.erro(arq, i, f"NCM {reg['codigo_ncm']} fora do intervalo {m.group(1)}", "intervalo-arquivo")

    # Hierarquia da NCM: todo código tem o capítulo cadastrado e algum nível superior.
    codigos = {reg["codigo_ncm"] for _, _, reg in dados.get("ncm", [])}
    digitos = {re.sub(r"\D", "", c) for c in codigos}
    for arq, i, reg in dados.get("ncm", []):
        d = re.sub(r"\D", "", reg["codigo_ncm"])
        if len(d) > 2 and not any(d[:n] in digitos for n in range(2, len(d))):
            rel.aviso(arq, i, f"NCM {reg['codigo_ncm']} sem nenhum nível superior cadastrado", "hierarquia")

    # Referências entre tabelas.
    for t in schema["tabelas"]:
        for ref in t.get("referencias", []):
            destino = {reg[ref.get("coluna_destino", ref["coluna"])] for _, _, reg in dados.get(ref["tabela"], [])}
            for arq, i, reg in dados.get(t["nome"], []):
                v = reg[ref["coluna"]]
                if v and v not in destino:
                    msg = f"{ref['coluna']} {v} não existe na tabela '{ref['tabela']}'"
                    (rel.erro if ref.get("nivel") == "erro" else rel.aviso)(arq, i, msg, "referencia")

    # Toda folha da NCM tem alíquota de II.
    folhas = {c for c in codigos if RE["ncm_folha"].match(c)}
    com_tec = {reg["codigo_ncm"] for _, _, reg in dados.get("tec", [])}
    for c in sorted(folhas - com_tec):
        rel.aviso("aliquotas/federal/TEC", None, f"NCM {c} sem alíquota de Imposto de Importação", "sem-tec")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--corrigir", action="store_true", help="corrige automaticamente o que for seguro")
    p.add_argument("--estrito", action="store_true", help="avisos também fazem a validação falhar")
    args = p.parse_args()

    schema = json.load(open(SCHEMA_PATH, encoding="utf-8"))
    rel = Relatorio()
    dados = {t["nome"]: validar_tabela(t, rel, args.corrigir) for t in schema["tabelas"]}
    validar_estrutura(schema, dados, rel)
    rel.imprimir()

    total = sum(len(v) for v in dados.values())
    print(f"\n{total} registros em {len(schema['tabelas'])} tabelas: {rel.erros} erro(s), {rel.avisos} aviso(s).")
    if rel.erros or (args.estrito and rel.avisos):
        print("Validação FALHOU." + ("" if args.corrigir else " Tente: python tools/validar_dados.py --corrigir"))
        sys.exit(1)
    print("Validação OK.")


if __name__ == "__main__":
    main()
