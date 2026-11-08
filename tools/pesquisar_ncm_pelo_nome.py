import os
import sys
import unicodedata

from globals import get_manifest_dict, load_chapter_rows, ROOT_DIR

# Comando para pesquisar códigos NCM pelo nome (busca sem acento e sem diferenciar maiúsculas).

MAX_RESULTS = 50

def _simplify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.replace("\xa0", " "))
    return "".join(c for c in text if not unicodedata.combining(c)).lower()

def find_ncm_section_by_name(name: str) -> list:
    manifest_dict = get_manifest_dict()
    terms = _simplify(name).split()
    results = []
    for chapters in manifest_dict.get("index-ncm", {}).values():
        for path in chapters.values():
            for r in load_chapter_rows(os.path.join(ROOT_DIR, path)):
                description = _simplify(r["row"][1])
                if all(t in description for t in terms):
                    results.append(r["row"])
    return results

if __name__ == "__main__":
    name = " ".join(sys.argv[1:]) or input("> Nome do produto: ")
    results = find_ncm_section_by_name(name)
    for row in results[:MAX_RESULTS]:
        folha = "" if len(row[0]) == 10 else "  (agrupamento)"
        print("%-11s %s%s" % (row[0], row[1], folha))
    if len(results) > MAX_RESULTS:
        print("... e mais %d resultado(s). Refine a busca." % (len(results) - MAX_RESULTS))
    if not results:
        print("Nenhum código encontrado.")
