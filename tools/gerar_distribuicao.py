"""
Gera a distribuição para integrações a partir dos CSVs (que continuam sendo a única fonte editável).

Uso:
    python tools/gerar_distribuicao.py            # gera em dist/
    python tools/gerar_distribuicao.py --saida X  # gera em X/

Saída (nada disso é commitado; o CI publica no GitHub Pages e nas Releases):
    impostos.sqlite              banco com todas as tabelas, tipado e indexado
    csv/<tabela>.csv             cada tabela consolidada em um único CSV (formato original)
    json/<tabela>.json           cada tabela como lista JSON tipada
    api/v1/meta.json             versão, data de geração, fontes e lista de tabelas
    api/v1/ncm/index.json        todos os NCM folha com descrição completa (para busca)
    api/v1/ncm/<8 dígitos>.json  todos os impostos de um NCM, em um único arquivo
    api/v1/fixas.json            alíquotas que não dependem do NCM (PIS/COFINS padrão, ICMS, especiais)
    datapackage.json             descrição Frictionless Data dos CSVs
    schema.json                  cópia do schema
    llms.txt                     instruções para LLMs consultarem os dados (padrão llmstxt.org)

Na distribuição tipada (SQLite, JSON e API):
    - alíquotas são números (fração); 'NT' vira aliquota = null e nao_tributado = true;
    - datas estão em ISO (AAAA-MM-DD) e '31/12/9999' vira null;
    - colunas de NCM ganham uma versão só com dígitos (<coluna>_digitos).

Não depende de nenhuma biblioteca externa.
"""

import argparse
import csv
import glob
import json
import os
import re
import shutil
import sqlite3
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIPOS_NCM = {"ncm", "ncm_folha", "ncm_prefixo"}


def carregar_json(nome):
    with open(os.path.join(ROOT, nome), encoding="utf-8") as f:
        return json.load(f)


def ler_tabela(tabela):
    linhas = []
    for p in sorted(glob.glob(os.path.join(ROOT, tabela["arquivos"]))):
        with open(p, encoding="utf-8", newline="") as f:
            linhas.extend(csv.DictReader(f))
    return linhas


def digitos(ncm):
    return re.sub(r"\D", "", ncm or "")


def converter(tipo, valor):
    """Valor do CSV -> valor tipado. Retorna dict de colunas (uma coluna pode virar duas)."""
    if valor == "":
        return None
    if tipo in ("fracao", "numero"):
        return float(valor)
    if tipo == "inteiro":
        return int(valor)
    if tipo == "data_br":
        d, m, a = valor.split("/")
        return None if a == "9999" else f"{a}-{m}-{d}"
    return valor


def registro_tipado(tabela, linha):
    saida = {}
    for col in tabela["colunas"]:
        nome, tipo, valor = col["nome"], col["tipo"], linha[col["nome"]]
        if tipo == "fracao_ou_nt":
            saida[nome] = None if valor in ("", "NT") else float(valor)
            saida["nao_tributado"] = valor == "NT"
            continue
        saida[nome] = converter(tipo, valor)
        if tipo in TIPOS_NCM:
            saida[nome + "_digitos"] = digitos(valor) or None
    return saida


def colunas_tipadas(tabela):
    """Lista (nome, tipo SQL) na mesma ordem de registro_tipado."""
    cols = []
    for col in tabela["colunas"]:
        tipo = col["tipo"]
        if tipo == "fracao_ou_nt":
            cols += [(col["nome"], "REAL"), ("nao_tributado", "INTEGER")]
            continue
        sql = {"fracao": "REAL", "numero": "REAL", "inteiro": "INTEGER"}.get(tipo, "TEXT")
        cols.append((col["nome"], sql))
        if tipo in TIPOS_NCM:
            cols.append((col["nome"] + "_digitos", "TEXT"))
    return cols


def escrever_json(caminho, dados):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, separators=(",", ":"))


# --------------------------------------------------------------------------- saídas

def gerar_csv_e_json(schema, brutos, tipados, saida):
    for t in schema["tabelas"]:
        nomes = [c["nome"] for c in t["colunas"]]
        caminho = os.path.join(saida, "csv", t["nome"] + ".csv")
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=nomes, lineterminator="\r\n")
            w.writeheader()
            w.writerows(brutos[t["nome"]])
        escrever_json(os.path.join(saida, "json", t["nome"] + ".json"), tipados[t["nome"]])


def gerar_sqlite(schema, tipados, manifest, saida):
    caminho = os.path.join(saida, "impostos.sqlite")
    if os.path.exists(caminho):
        os.remove(caminho)
    con = sqlite3.connect(caminho)
    for t in schema["tabelas"]:
        cols = colunas_tipadas(t)
        con.execute(f'CREATE TABLE {t["nome"]} ({", ".join(f"{n} {s}" for n, s in cols)})')
        con.executemany(f'INSERT INTO {t["nome"]} VALUES ({", ".join("?" * len(cols))})',
                        [tuple(r[n] for n, _ in cols) for r in tipados[t["nome"]]])
        for n, _ in cols:
            if n.endswith("_digitos") or n == "codigo_ncm":
                con.execute(f"CREATE INDEX idx_{t['nome']}_{n} ON {t['nome']} ({n})")

    con.executescript("""
        CREATE VIEW v_impostos_ncm AS
        SELECT n.codigo_ncm, n.codigo_ncm_digitos, n.descricao,
               tec.aliquota AS ii, tec.aliquota_tec_mercosul AS ii_tec_mercosul, tec.bit_bk,
               tipi.aliquota AS ipi, tipi.nao_tributado AS ipi_nao_tributado
        FROM ncm n
        LEFT JOIN tec ON tec.codigo_ncm = n.codigo_ncm
        LEFT JOIN tipi ON tipi.codigo_ncm = n.codigo_ncm AND tipi.ex IS NULL
        WHERE length(n.codigo_ncm_digitos) = 8;

        CREATE VIEW v_pis_cofins_vigente AS
        SELECT * FROM pis_cofins_excecoes WHERE vigencia_fim IS NULL OR vigencia_fim >= date('now');

        CREATE TABLE metadados (chave TEXT PRIMARY KEY, valor TEXT);
    """)
    info = manifest.get("info", {})
    con.executemany("INSERT INTO metadados VALUES (?, ?)", [
        ("versao", info.get("versao")), ("gerado_em", info.get("gerado_em")),
        ("referencias", json.dumps(manifest.get("referencias", {}), ensure_ascii=False)),
    ])
    con.commit()
    con.execute("VACUUM")
    con.close()


def vigente(reg, hoje):
    fim = reg.get("vigencia_fim")
    ini = reg.get("vigencia_inicio")
    return (not fim or fim >= hoje) and (not ini or ini <= hoje)


def gerar_api(schema, tipados, manifest, saida, base):
    api = os.path.join(saida, "api", "v1")
    hoje = date.today().isoformat()
    info = manifest.get("info", {})
    fontes = {"versao": info.get("versao"), "gerado_em": info.get("gerado_em")}

    ncm = tipados["ncm"]
    por_digitos = {r["codigo_ncm_digitos"]: r for r in ncm}
    tec = {r["codigo_ncm"]: r for r in tipados["tec"]}
    tipi, tec_exc = {}, {}
    for r in tipados["tipi"]:
        tipi.setdefault(r["codigo_ncm"], []).append(r)
    for r in tipados["tec_excecoes"]:
        tec_exc.setdefault(r["codigo_ncm"], []).append(r)
    pis_por_prefixo = {}
    for r in tipados["pis_cofins_excecoes"]:
        if r["ncm_prefixo_digitos"]:
            pis_por_prefixo.setdefault(r["ncm_prefixo_digitos"], []).append(r)

    def sem(reg, *chaves):
        return {k: v for k, v in reg.items() if k not in chaves and not k.endswith("_digitos")}

    indice = []
    for d, r in sorted(por_digitos.items()):
        if len(d) != 8:
            continue
        codigo = r["codigo_ncm"]
        hierarquia = [{"codigo": por_digitos[d[:n]]["codigo_ncm"], "descricao": por_digitos[d[:n]]["descricao"]}
                      for n in range(2, 8) if d[:n] in por_digitos]
        partes = [h["descricao"] for h in hierarquia] + [r["descricao"]]
        descricao_completa = " > ".join(re.sub(r"^[-\s]+", "", p) for p in partes)
        indice.append({"codigo": codigo, "descricao": descricao_completa})

        t = tec.get(codigo)
        linhas_tipi = tipi.get(codigo, [])
        geral = next((x for x in linhas_tipi if not x["ex"]), None)
        regras = [x for n in range(2, 9) for x in pis_por_prefixo.get(d[:n], [])]

        escrever_json(os.path.join(api, "ncm", d + ".json"), {
            "codigo": codigo,
            "codigo_digitos": d,
            "descricao": r["descricao"],
            "descricao_completa": descricao_completa,
            "hierarquia": hierarquia,
            "vigencia": {"inicio": r["data_inicio"], "fim": r["data_fim"]},
            "imposto_importacao": None if not t else {
                "aliquota": t["aliquota"],
                "aliquota_tec_mercosul": t["aliquota_tec_mercosul"],
                "bit_bk": t["bit_bk"],
                "excecoes": [dict(sem(x, "codigo_ncm"), vigente=vigente(x, hoje)) for x in tec_exc.get(codigo, [])],
            },
            "ipi": None if not linhas_tipi else {
                "aliquota": geral["aliquota"] if geral else None,
                "nao_tributado": geral["nao_tributado"] if geral else None,
                "ex": [{"ex": x["ex"], "aliquota": x["aliquota"], "nao_tributado": x["nao_tributado"],
                        "descricao": x["descricao_ex"]} for x in linhas_tipi if x["ex"]],
            },
            "pis_cofins": {
                "regimes_diferenciados": [dict(sem(x), vigente=vigente(x, hoje)) for x in regras],
                "padrao": f"{base}api/v1/fixas.json",
            },
            "fontes": fontes,
        })

    escrever_json(os.path.join(api, "ncm", "index.json"), indice)
    escrever_json(os.path.join(api, "fixas.json"), {
        "pis_cofins_padrao": tipados["pis_cofins_padrao"],
        "icms": tipados["icms"],
        "regras_especiais": tipados["regras_especiais"],
        "pis_cofins_sem_ncm": [sem(x) for x in tipados["pis_cofins_excecoes"] if not x["ncm_prefixo"]],
        "fontes": fontes,
    })
    escrever_json(os.path.join(api, "meta.json"), {
        "versao": info.get("versao"),
        "gerado_em": info.get("gerado_em"),
        "referencias": manifest.get("referencias", {}),
        "endpoints": {
            "ncm": f"{base}api/v1/ncm/{{8 dígitos}}.json",
            "indice_ncm": f"{base}api/v1/ncm/index.json",
            "fixas": f"{base}api/v1/fixas.json",
            "sqlite": f"{base}impostos.sqlite",
            "schema": f"{base}schema.json",
        },
        "tabelas": {t["nome"]: {"titulo": t["titulo"], "csv": f"{base}csv/{t['nome']}.csv",
                                "json": f"{base}json/{t['nome']}.json"} for t in schema["tabelas"]},
    })
    return len(indice)


def gerar_datapackage(schema, manifest, saida):
    tipo_fd = {"inteiro": ("integer", None), "numero": ("number", None), "fracao": ("number", None),
               "data_br": ("date", "%d/%m/%Y"), "data_iso": ("date", None)}
    recursos = []
    for t in schema["tabelas"]:
        campos = []
        for c in t["colunas"]:
            tipo, fmt = tipo_fd.get(c["tipo"], ("string", None))
            campo = {"name": c["nome"], "type": tipo, "description": c.get("descricao", "")}
            if fmt:
                campo["format"] = fmt
            restr = {}
            if c.get("obrigatorio"):
                restr["required"] = True
            if "valores" in c:
                restr["enum"] = c["valores"]
            if restr:
                campo["constraints"] = restr
            campos.append(campo)
        sch = {"fields": campos, "missingValues": [""]}
        if "chave" in t:
            sch["primaryKey"] = t["chave"]
        recursos.append({"name": t["nome"], "title": t["titulo"], "path": f"csv/{t['nome']}.csv",
                         "format": "csv", "encoding": "utf-8", "schema": sch})
    pacote = {
        "name": "imposto-produtos-brasil",
        "title": "Impostos sobre produtos no Brasil",
        "version": manifest.get("info", {}).get("versao"),
        "licenses": [{"name": "Unlicense", "path": "https://unlicense.org"}],
        "resources": recursos,
    }
    with open(os.path.join(saida, "datapackage.json"), "w", encoding="utf-8") as f:
        json.dump(pacote, f, ensure_ascii=False, indent=2)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--saida", default=os.path.join(ROOT, "dist"))
    p.add_argument("--base-url", default="", help="URL pública onde a distribuição será servida (termina com /)")
    args = p.parse_args()

    schema = carregar_json("schema.json")
    manifest = carregar_json("manifest.json")
    saida = os.path.abspath(args.saida)
    for sub in ("api", "csv", "json"):
        shutil.rmtree(os.path.join(saida, sub), ignore_errors=True)
    os.makedirs(saida, exist_ok=True)

    brutos = {t["nome"]: ler_tabela(t) for t in schema["tabelas"]}
    tipados = {t["nome"]: [registro_tipado(t, r) for r in brutos[t["nome"]]] for t in schema["tabelas"]}

    gerar_csv_e_json(schema, brutos, tipados, saida)
    gerar_sqlite(schema, tipados, manifest, saida)
    n = gerar_api(schema, tipados, manifest, saida, args.base_url)
    gerar_datapackage(schema, manifest, saida)
    shutil.copy(os.path.join(ROOT, "schema.json"), os.path.join(saida, "schema.json"))
    pagina = os.path.join(ROOT, "tools", "pagina", "index.html")
    if os.path.exists(pagina):
        shutil.copy(pagina, os.path.join(saida, "index.html"))
    llms = os.path.join(ROOT, "tools", "pagina", "llms.txt")
    if os.path.exists(llms):
        info = manifest.get("info", {})
        texto = open(llms, encoding="utf-8").read()
        texto = (texto.replace("{BASE}", args.base_url)
                      .replace("{VERSAO}", str(info.get("versao", "?")))
                      .replace("{GERADO_EM}", str(info.get("gerado_em", "?"))))
        with open(os.path.join(saida, "llms.txt"), "w", encoding="utf-8") as f:
            f.write(texto)
    print(f"Distribuição gerada em {saida}: {sum(len(v) for v in brutos.values())} registros, {n} NCM na API.")


if __name__ == "__main__":
    main()
