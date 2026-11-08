import os
import sys

from globals import (get_manifest_dict, find_ncm_interval, format_relation_list_to_list, ROOT_DIR,
                     find_ancestors, find_children, normalize, load_chapter_rows, to_percentage,
                     read_csv_dicts)

HEADER_FATHER = ["NCM PAI", "Descrição"]
HEADER_SELF = ["NCM", "Descrição", "Medida", "Data Início", "Data Fim"]
HEADER_CHILD = ["NCM Filho", "Descrição"]
LAYOUT = "%s: \t%s \n"

# Comando para pesquisar por taxas a partir de seu código NCM.

def _matches_prefix(ncm_digits: str, prefix: str) -> bool:
    p = normalize(prefix)
    return bool(p) and ncm_digits.startswith(p)

def search_for_taxes_by_ncm(ncm_code: str):
    manifest_dict = get_manifest_dict()
    ncm_code = ncm_code.strip()[0:10]
    digits = normalize(ncm_code)
    items = find_ncm_interval(ncm_code, manifest_dict)
    if items is None:
        print("Código NCM inválido ou fora dos intervalos conhecidos.")
        return

    interval, prefix = items
    ncm = manifest_dict.get("index-ncm", {})
    tec = manifest_dict.get("index-tec", {})
    tipi = manifest_dict.get("index-tipi", {})

    if prefix not in ncm.get(interval, {}):
        print("Capítulo %s não existe na NCM." % prefix)
        return

    rows = load_chapter_rows(os.path.join(ROOT_DIR, ncm[interval][prefix]))
    ancestors = find_ancestors(rows, digits)
    self_row = next((r for r in rows if r["digits"] == digits), None)
    children = find_children(rows, digits)

    print("\nHIERARQUIA \n")
    for a in ancestors:
        format_relation_list_to_list(HEADER_FATHER, a["row"], LAYOUT)

    if self_row is not None:
        format_relation_list_to_list(HEADER_SELF, self_row["row"], LAYOUT)
    else:
        print("Código não encontrado na tabela NCM.")

    if children:
        print("\nEste código é pai de %d código(s):" % len(children))
        for c in children:
            format_relation_list_to_list(HEADER_CHILD, c["row"], LAYOUT)
        print("As alíquotas são definidas nos códigos folha (8 dígitos).")
        return
    print("\nEste código não possui filhos (é um código folha).")

    print("\nALÍQUOTAS \n")

    tec_row = next((r for r in read_csv_dicts(tec[interval]) if normalize(r["codigo_ncm"]) == digits), None)
    if tec_row:
        print("II (aplicada): \t" + to_percentage(tec_row["aliquota"]))
        print("TEC Mercosul: \t" + to_percentage(tec_row["aliquota_tec_mercosul"])
              + ("  [%s]" % tec_row["bit_bk"] if tec_row["bit_bk"] else ""))
    else:
        print("II (TEC): \tnão encontrado")

    tipi_rows = [r for r in read_csv_dicts(tipi[interval]) if normalize(r["codigo_ncm"]) == digits]
    if tipi_rows:
        for r in tipi_rows:
            if r["ex"]:
                print("IPI Ex %s: \t%s  (%s)" % (r["ex"], to_percentage(r["aliquota"]), r["descricao_ex"]))
            else:
                print("IPI (TIPI): \t" + to_percentage(r["aliquota"]))
    else:
        print("IPI (TIPI): \tnão encontrado")

    tec_exc = manifest_dict.get("relacao-tec_excecoes", {}).get("padrao")
    if tec_exc:
        exc = [r for r in read_csv_dicts(tec_exc) if normalize(r["codigo_ncm"]) == digits]
        if exc:
            print("\nEXCEÇÕES DO IMPOSTO DE IMPORTAÇÃO \n")
            for r in exc:
                vig = "%s a %s" % (r["vigencia_inicio"] or "?", r["vigencia_fim"] or "indeterminado")
                ex = (" Ex %s" % r["ex"]) if r["ex"] else ""
                quota = (" | quota %s %s" % (r["quota"], r["unidade_quota"])) if r["quota"] else ""
                print("%s%s: %s | %s%s | %s" % (r["anexo"], ex, to_percentage(r["aliquota"]), vig, quota, r["ato"]))

    pis_exc = manifest_dict.get("relacao-pis_cofins", {}).get("excecoes")
    if pis_exc:
        regras = [r for r in read_csv_dicts(pis_exc)
                  if _matches_prefix(digits, r["ncm_prefixo"]) and not r["vigencia_fim"]]
        print("\nPIS/COFINS \n")
        if not regras:
            print("Nenhum regime diferenciado vigente vinculado a este NCM nas tabelas SPED.")
            print("Aplicam-se as alíquotas padrão (ver aliquotas/federal/PIS_COFINS/standart.csv).")
        for r in regras:
            if r["aliquota_pis"]:
                valores = "PIS %s / COFINS %s" % (to_percentage(r["aliquota_pis"]), to_percentage(r["aliquota_cofins"]))
            elif r["valor_pis_por_unidade"]:
                valores = "PIS R$ %s / COFINS R$ %s por %s" % (r["valor_pis_por_unidade"],
                                                             r["valor_cofins_por_unidade"], r["unidade"])
            elif r["tipo"] == "aliquota_zero":
                valores = "PIS 0% / COFINS 0%"
            else:
                valores = r["observacao"] or "ver condições na descrição"
            print("[%s | CST %s] %s: %s" % (r["tabela_sped"], r["cst"], r["tipo"], valores))
            print("    %s" % r["descricao"][:160])


if __name__ == "__main__":
    ncm_code = sys.argv[1] if len(sys.argv) > 1 else input("> Coloque o seu código NCM: ")
    search_for_taxes_by_ncm(ncm_code)
