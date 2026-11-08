"""
Regenera os dados do repositório a partir das fontes oficiais.

Fontes:
- NCM: Portal Único Siscomex (JSON público da nomenclatura).
- TIPI: Receita Federal (tipi.xlsx).
- TEC: Camex/MDIC (Anexos I a X da Resolução Gecex nº 272/2021).
- PIS/COFINS por NCM: tabelas externas do SPED EFD-Contribuições (4.3.10 a 4.3.17).

Uso (a partir da raiz do repositório ou de qualquer lugar):

    pip install -r tools/requirements.txt
    python tools/atualizar_dados.py                 # baixa tudo e regenera
    python tools/atualizar_dados.py --cache pasta   # reaproveita/guarda downloads em "pasta"

O script nunca inventa valores: tudo o que é escrito vem das planilhas oficiais.
"""

import argparse
import csv
import datetime as dt
import html
import json
import os
import re
import sys
import tempfile
import urllib.request
from pathlib import Path

try:
    import openpyxl
except ImportError:  # pragma: no cover
    sys.exit("Dependência ausente: rode 'pip install -r tools/requirements.txt'")

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest.json"
UA = {"User-Agent": "Mozilla/5.0 (imposto-produtos-brasil; atualizador de dados)"}

URL_NCM = "https://portalunico.siscomex.gov.br/classif/api/publico/nomenclatura/download/json?perfil=PUBLICO"
URL_TIPI = "https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/legislacao/documentos-e-arquivos/tipi.xlsx"
URL_TEC_PAGINA = "https://www.gov.br/mdic/pt-br/assuntos/camex/se-camex/strat/tarifas/vigentes"
URL_SPED_VERSOES = ("http://www.sped.fazenda.gov.br/spedtabelas/WsConsulta/WsConsulta.asmx/"
                    "consultarVersoesTabelasExternas?codigoSistema=SpedPisCofins")
URL_SPED_TABELA = "http://www.sped.fazenda.gov.br/spedtabelas/wsconsulta/obterTabela.ashx?idTabela={id}&versao={versao}"

# Tabelas SPED de PIS/COFINS que relacionam produtos (NCM) a regimes diferenciados.
SPED_TABELAS = {
    "4.3.10": ("monofasica_aliquota_diferenciada", "02;04"),
    "4.3.11": ("monofasica_aliquota_por_unidade", "03;04"),
    "4.3.12": ("substituicao_tributaria", "05"),
    "4.3.13": ("aliquota_zero", "06"),
    "4.3.14": ("isencao", "07"),
    "4.3.15": ("nao_incidencia", "08"),
    "4.3.16": ("suspensao", "09"),
    "4.3.17": ("aliquota_diferenciada", "02"),
}

CABECALHO_NCM = ["codigo_ncm", "descricao", "data_inicio", "data_fim", "numero", "ano"]
RE_FOLHA = re.compile(r"^\d{4}\.\d{2}\.\d{2}$")


# --------------------------------------------------------------------------- utilidades

def baixar(url: str, destino: Path) -> Path:
    if destino.exists() and destino.stat().st_size > 0:
        return destino
    print(f"  baixando {url}")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as r:
        destino.write_bytes(r.read())
    return destino


def ler_texto(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def fracao(percentual) -> str:
    """Converte percentual (ex.: 3.25) para fração em texto (ex.: '0.0325')."""
    if str(percentual).strip() == "":
        return ""
    valor = round(float(str(percentual).replace(",", ".")) / 100, 6)
    texto = f"{valor:.6f}".rstrip("0")
    inteiro, _, dec = texto.partition(".")
    return f"{inteiro}.{dec.ljust(4, '0')}"


def numero(texto) -> str:
    if str(texto).strip() == "":
        return ""
    valor = float(str(texto).replace(",", "."))
    return f"{valor:g}"


def data_iso(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, (dt.datetime, dt.date)):
        return valor.strftime("%Y-%m-%d")
    texto = str(valor).strip()
    if texto in ("", "-", "–"):
        return ""
    for formato in ("%d/%m/%Y", "%d%m%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(texto, formato).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return texto


def limpar(texto) -> str:
    if texto is None:
        return ""
    texto = html.unescape(re.sub(r"<[^>]+>", "", str(texto)))
    return re.sub(r"[ \t\r\n]+", " ", texto).strip(" \xa0")


def vazio(valor) -> str:
    texto = limpar(valor)
    return "" if texto in ("-", "–") else texto


def normalizar_ex(ex: str, digitos: int) -> str:
    """'Ex 1' / '1' -> '001' (ou '01'); textos não numéricos ficam como estão."""
    ex = re.sub(r"(?i)^ex\s*", "", (ex or "").strip())
    formula = re.match(r'^="(\d*)"&"?(\d+)"?$', ex)  # fórmula do Excel na fonte, ex.: ="0"&51
    if formula:
        ex = formula.group(1) + formula.group(2)
    return ex.zfill(digitos) if ex.isdigit() else ex


def ncm_pontuado(digitos: str) -> str:
    d = re.sub(r"\D", "", digitos)
    if len(d) <= 2:
        return d
    saida = d[:4]
    if len(d) > 4:
        saida += "." + d[4:6]
    if len(d) > 6:
        saida += "." + d[6:8]
    return saida


def escrever_csv(caminho: Path, cabecalho: list, linhas: list):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")  # CRLF: abre corretamente no Excel
        w.writerow(cabecalho)
        w.writerows(linhas)


def intervalo_do_capitulo(capitulo: str, intervalos: list) -> str:
    c = int(capitulo)
    for s in intervalos:
        ini, fim = (int(x) for x in s.split("-"))
        if ini <= c <= fim:
            return s
    raise ValueError(f"capítulo {capitulo} fora dos intervalos do manifest")


# --------------------------------------------------------------------------- NCM

def gerar_ncm(cache: Path, manifest: dict) -> dict:
    print("NCM")
    dados = json.loads(baixar(URL_NCM, cache / "ncm.json").read_text(encoding="utf-8-sig"))

    por_capitulo = {}
    for n in dados["Nomenclaturas"]:
        codigo = n["Codigo"].strip()
        cap = re.sub(r"\D", "", codigo)[:2]
        por_capitulo.setdefault(cap, []).append([
            codigo, limpar(n["Descricao"]), data_iso(n["Data_Inicio"]),
            "" if n["Data_Fim"].endswith("/9999") else data_iso(n["Data_Fim"]),
            n["Numero_Ato_Ini"], n["Ano_Ato_Ini"],
        ])

    intervalos = manifest["intervalos"]
    indice = {}
    for cap, linhas in sorted(por_capitulo.items()):
        iv = intervalo_do_capitulo(cap, intervalos)
        rel = f"ncm/{iv}/capitulo-{cap}.csv"
        escrever_csv(ROOT / rel, CABECALHO_NCM, linhas)
        indice.setdefault(iv, {})[cap] = rel

    # Capítulos sem códigos na NCM oficial (ex.: 98 e 99) mantêm o arquivo e a entrada existentes.
    for iv, caps in manifest.get("index-ncm", {}).items():
        for cap, rel in caps.items():
            if (ROOT / rel).exists() and cap not in por_capitulo:
                escrever_csv(ROOT / rel, CABECALHO_NCM, [])
                indice.setdefault(iv, {}).setdefault(cap, rel)
    manifest["index-ncm"] = {iv: dict(sorted(indice[iv].items())) for iv in intervalos if iv in indice}
    manifest["referencias"]["NCM"].update({
        "resolucao": dados.get("Ato", ""),
        "ultima_atualizacao": dt.date.today().isoformat(),
        "observacao": dados.get("Data_Ultima_Atualizacao_NCM", ""),
    })
    folhas = {l[0] for ls in por_capitulo.values() for l in ls if RE_FOLHA.match(l[0])}
    print(f"  {sum(len(v) for v in por_capitulo.values())} códigos, {len(folhas)} folhas")
    return {"folhas": folhas}


# --------------------------------------------------------------------------- TIPI

def gerar_tipi(cache: Path, manifest: dict, folhas_ncm: set):
    print("TIPI")
    wb = openpyxl.load_workbook(baixar(URL_TIPI, cache / "tipi.xlsx"), read_only=True)
    ws = wb.worksheets[0]

    atos = []
    linhas = {}
    ncm_atual = None
    for row in ws.iter_rows(values_only=True):
        celula = row[0]
        if isinstance(celula, str) and "Atualizações" in celula:
            atos = [l.strip() for l in celula.splitlines()[1:] if l.strip()]
            continue
        ncm, ex, desc, aliq = (list(row) + [None] * 4)[:4]
        if isinstance(ncm, str) and ncm.strip():
            ncm_atual = ncm.strip()
        ex = "" if ex in (None, "") else str(ex).strip()
        if ncm_atual is None or not RE_FOLHA.match(ncm_atual):
            continue
        if not (isinstance(ncm, str) and ncm.strip()) and not ex:
            continue  # linha de continuação sem dados
        if aliq is None or str(aliq).strip() == "":
            continue
        texto = str(aliq).strip().upper()
        aliquota = "NT" if texto == "NT" else fracao(aliq)
        ex = normalizar_ex(ex, 2)
        cap = ncm_atual[:2]
        linhas.setdefault(cap, []).append([ncm_atual, ex, aliquota, limpar(desc) if ex else ""])

    intervalos = manifest["intervalos"]
    por_iv = {iv: [] for iv in intervalos}
    for cap, ls in linhas.items():
        por_iv[intervalo_do_capitulo(cap, intervalos)].extend(ls)
    total = 0
    for iv in intervalos:
        ls = sorted(por_iv[iv], key=lambda l: (l[0], l[1]))
        escrever_csv(ROOT / f"aliquotas/federal/TIPI/{iv}.csv",
                     ["codigo_ncm", "ex", "aliquota", "descricao_ex"], ls)
        total += len(ls)

    fora = {l[0] for ls in linhas.values() for l in ls} - folhas_ncm
    if fora:
        print(f"  aviso: {len(fora)} NCM da TIPI não existem na NCM vigente: {sorted(fora)[:10]}")
    manifest["index-tipi"] = {iv: f"aliquotas/federal/TIPI/{iv}.csv" for iv in intervalos}
    ref = manifest["referencias"]["aliquotas"]["federal"]["TIPI"]
    ref["resolucao"] = "Decreto nº 11.158/2022" + (f", atualizado até {atos[-1]}" if atos else "")
    ref["ultima_atualizacao"] = dt.date.today().isoformat()
    print(f"  {total} linhas")


# --------------------------------------------------------------------------- TEC

def url_tec(cache: Path) -> str:
    pagina = baixar(URL_TEC_PAGINA, cache / "tec.html").read_text(encoding="utf-8", errors="replace")
    m = re.search(r'href="([^"]+anexos-i-a-x-resolucao-gecex-272-21\.xlsx)"', pagina, re.I)
    if not m:
        sys.exit("Não encontrei o link dos Anexos I a X na página da Camex.")
    return m.group(1)


def separar_tec(valor):
    """'12,6BK' -> ('12.6', 'BK'); 0 -> ('0', '')."""
    if isinstance(valor, (int, float)):
        return numero(valor), ""
    m = re.match(r"^\s*([\d.,]+)\s*(BIT|BK)?\s*$", str(valor or ""), re.I)
    if not m:
        return None, ""
    return numero(m.group(1)), (m.group(2) or "").upper()


def cabecalho_normalizado(row) -> list:
    return [limpar(c).lower() for c in row]


def coluna(cab: list, *nomes):
    for nome in nomes:
        for i, c in enumerate(cab):
            if c.startswith(nome):
                return i
    return None


def gerar_tec(cache: Path, manifest: dict, folhas_ncm: set):
    print("TEC")
    wb = openpyxl.load_workbook(baixar(url_tec(cache), cache / "tec.xlsx"), read_only=True)

    # Anexo I: TEC do Mercosul.
    ws = wb["Anexo I - TEC"]
    atualizacao_tec = ""
    tec = {}
    for row in ws.iter_rows(values_only=True):
        if isinstance(row[0], str) and "Atualizado até" in row[0]:
            atualizacao_tec = limpar(row[0]).lstrip("* ")
        if isinstance(row[0], str) and RE_FOLHA.match(row[0].strip()):
            aliq, marca = separar_tec(row[2])
            if aliq is not None:
                tec[row[0].strip()] = (aliq, marca)

    # Anexo II: alíquota efetivamente aplicada pelo Brasil quando difere da TEC.
    ws = wb["Anexo II - Diferentes da TEC"]
    aplicada = {}
    cab = None
    for row in ws.iter_rows(values_only=True):
        if cab is None:
            if row[0] and limpar(row[0]).upper() == "NCM":
                cab = cabecalho_normalizado(row)
                i_apl = coluna(cab, "alíquota aplicada")
                i_bk = coluna(cab, "bit/bk")
            continue
        if isinstance(row[0], str) and RE_FOLHA.match(row[0].strip()) and isinstance(row[i_apl], (int, float)):
            aplicada[row[0].strip()] = (numero(row[i_apl]), limpar(row[i_bk]).upper() if i_bk is not None else "")

    intervalos = manifest["intervalos"]
    por_iv = {iv: [] for iv in intervalos}
    for ncm in sorted(tec):
        aliq_tec, marca = tec[ncm]
        aliq_apl, marca2 = aplicada.get(ncm, (aliq_tec, ""))
        por_iv[intervalo_do_capitulo(ncm[:2], intervalos)].append(
            [ncm, fracao(aliq_apl), fracao(aliq_tec), marca or marca2])
    for iv in intervalos:
        escrever_csv(ROOT / f"aliquotas/federal/TEC/{iv}.csv",
                     ["codigo_ncm", "aliquota", "aliquota_tec_mercosul", "bit_bk"], por_iv[iv])

    # Anexos IV a X: exceções (por Ex, quota ou prazo).
    excecoes = []
    for ws in wb.worksheets:
        m = re.match(r"Anexo (IV|V|VI|VIII|IX|X)\b", ws.title)
        if not m:
            continue
        cab = None
        for row in ws.iter_rows(values_only=True):
            if cab is None:
                if row[0] and limpar(row[0]).upper() == "NCM":
                    cab = cabecalho_normalizado(row)
                    idx = {
                        "ex": coluna(cab, "nº ex"), "desc": coluna(cab, "descrição"),
                        "aliq": coluna(cab, "alíquota"), "quota": coluna(cab, "quota"),
                        "uq": coluna(cab, "unidade"), "ini": coluna(cab, "início"),
                        "fim": coluna(cab, "término"), "ato": coluna(cab, "ato de inclusão"),
                        "obs": coluna(cab, "observaç"),
                    }
                continue
            ncm = limpar(row[0])
            if not RE_FOLHA.match(ncm):
                continue
            g = lambda k: row[idx[k]] if idx[k] is not None and idx[k] < len(row) else None
            aliq, _ = separar_tec(g("aliq"))
            excecoes.append([
                f"Anexo {m.group(1)}", ncm, normalizar_ex(vazio(g("ex")), 3), limpar(g("desc")),
                fracao(aliq) if aliq is not None else "", vazio(g("quota")), vazio(g("uq")),
                data_iso(g("ini")), data_iso(g("fim")), vazio(g("ato")), vazio(g("obs")),
            ])
    escrever_csv(ROOT / "aliquotas/federal/TEC/excecoes.csv",
                 ["anexo", "codigo_ncm", "ex", "descricao", "aliquota", "quota", "unidade_quota",
                  "vigencia_inicio", "vigencia_fim", "ato", "observacao"], excecoes)

    fora = set(tec) - folhas_ncm
    if fora:
        print(f"  aviso: {len(fora)} NCM da TEC não existem na NCM vigente: {sorted(fora)[:10]}")
    manifest["index-tec"] = {iv: f"aliquotas/federal/TEC/{iv}.csv" for iv in intervalos}
    manifest["relacao-tec_excecoes"] = {"padrao": "aliquotas/federal/TEC/excecoes.csv"}
    ref = manifest["referencias"]["aliquotas"]["federal"]["TEC"]
    ref["resolucao"] = "Resolução Gecex nº 272/2021" + (f" ({atualizacao_tec})" if atualizacao_tec else "")
    ref["ultima_atualizacao"] = dt.date.today().isoformat()
    difere = sum(1 for n, (a, _) in aplicada.items() if n in tec and a != tec[n][0])
    print(f"  {len(tec)} NCM ({difere} com alíquota brasileira diferente da TEC), {len(excecoes)} exceções")


# --------------------------------------------------------------------------- PIS/COFINS

def gerar_pis_cofins(cache: Path, manifest: dict):
    print("PIS/COFINS")
    xml = ler_texto(URL_SPED_VERSOES)
    meta = html.unescape(re.search(r"<metadadosXml>(.*?)</metadadosXml>", xml, re.S).group(1))
    tabelas = {}
    for t in re.finditer(r"<tabela ([^>]*)/>", meta):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', t.group(1)))
        num = re.match(r"\s*(4\.3\.1[0-7])", attrs.get("desc", ""))
        if num and num.group(1) in SPED_TABELAS:
            tabelas[num.group(1)] = attrs

    linhas = []
    fontes = {}
    for num in sorted(SPED_TABELAS):
        attrs = tabelas[num]
        tipo, cst = SPED_TABELAS[num]
        arq = baixar(URL_SPED_TABELA.format(id=attrs["id"], versao=attrs["versao"]),
                     cache / f"sped_{num}_v{attrs['versao']}.txt")
        conteudo = arq.read_bytes().decode("cp1252", errors="replace").splitlines()
        cab = [c.strip().upper() for c in conteudo[0].split(" ", 1)[1].split(",")]
        fontes[num] = {"versao": attrs["versao"], "data": attrs.get("dtVersao", ""),
                       "descricao": limpar(attrs.get("desc"))}
        for bruta in conteudo[1:]:
            if not bruta.strip():
                continue
            campos = dict(zip(cab, bruta.split("|")))
            pis = cofins = vpis = vcofins = unid = ""
            pis_p = pis_r = cofins_p = cofins_r = ""
            if num in ("4.3.10", "4.3.12"):
                pis, cofins = fracao(campos["ALIQ_PIS"]), fracao(campos["ALIQ_COFIN"])
            elif num == "4.3.11":
                vpis, vcofins, unid = numero(campos["ALIQ_PIS"]), numero(campos["ALIQ_COFIN"]), campos["UNID"]
            elif num == "4.3.17":
                pis_p, pis_r = fracao(campos["ALIQ_PIS_P"]), fracao(campos["ALIQ_PIS_R"])
                cofins_p, cofins_r = fracao(campos["ALIQ_COF_P"]), fracao(campos["ALIQ_COF_R"])
            base = [num, tipo, cst, campos["CODIGO"], limpar(campos["DESC_PROD"]),
                    data_iso(campos["DT_INI"]), data_iso(campos["DT_FIM"])]
            resto = [campos.get("NCM_EX", ""), campos.get("EX_IPI", ""), pis, cofins, vpis, vcofins, unid,
                     pis_p, pis_r, cofins_p, cofins_r]
            ncms = [n for n in campos.get("NCM", "").split(";") if n.strip()]
            for ncm in ncms or [""]:
                linhas.append(base[:7] + [ncm_pontuado(ncm) if ncm else ""] + resto)

    escrever_csv(ROOT / "aliquotas/federal/PIS_COFINS/excecoes.csv",
                 ["tabela_sped", "tipo", "cst", "codigo", "descricao", "vigencia_inicio", "vigencia_fim",
                  "ncm_prefixo", "ncm_ex", "ex_ipi", "aliquota_pis", "aliquota_cofins",
                  "valor_pis_por_unidade", "valor_cofins_por_unidade", "unidade",
                  "aliquota_pis_p", "aliquota_pis_r", "aliquota_cofins_p", "aliquota_cofins_r"], linhas)
    manifest["relacao-pis_cofins"]["excecoes"] = "aliquotas/federal/PIS_COFINS/excecoes.csv"
    ref = manifest["referencias"]["aliquotas"]["federal"]["PIS/COFINS"]
    ref["tabelas_sped"] = {"link": "http://www.sped.fazenda.gov.br/spedtabelas/AppConsulta/publico/aspx/"
                                   "ConsultaTabelasExternas.aspx?CodSistema=SpedPisCofins",
                           "versoes": fontes}
    ref["ultima_atualizacao"] = dt.date.today().isoformat()
    print(f"  {len(linhas)} linhas")


# --------------------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cache", help="pasta para guardar/reaproveitar os arquivos baixados")
    p.add_argument("--versao", help="nova versão a gravar no manifest (ex.: 0.8)")
    args = p.parse_args()

    cache = Path(args.cache) if args.cache else Path(tempfile.mkdtemp(prefix="impostos-"))
    cache.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    ncm = gerar_ncm(cache, manifest)
    gerar_tipi(cache, manifest, ncm["folhas"])
    gerar_tec(cache, manifest, ncm["folhas"])
    gerar_pis_cofins(cache, manifest)

    if args.versao:
        manifest["info"]["versao"] = args.versao
    manifest["info"]["gerado_em"] = dt.date.today().isoformat()
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    print("manifest.json atualizado")


if __name__ == "__main__":
    main()
