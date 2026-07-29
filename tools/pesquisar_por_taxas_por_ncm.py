import csv
import os
import re

from globals import get_manifest_dict, find_ncm_interval, format_relation_list_to_list, ROOT_DIR, find_ancestors, find_children, normalize, load_chapter_rows, to_percentage

HEADER_FATHER = ["NCM PAI", "Descrição"]
HEADER_SELF = ["NCM", "Descrição", "Medida", "Data Início", "Data Fim"]
HEADER_CHILD = ["NCM Filho", "Descrição"]
LAYOUT = "%s: \t%s \n"

# Comando para pesquisar por taxas a partir de seu código NCM.

def search_for_taxes_by_ncm(ncm_code: str):
    manifest_dict = get_manifest_dict()
    ncm_code = ncm_code[0:10]
    digits = normalize(ncm_code)
    items = find_ncm_interval(ncm_code, manifest_dict)
    if items is not None:
        interval = items[0]
        prefix = items[1]

        ncm = manifest_dict.get("index-ncm", [])
        tec = manifest_dict.get("index-tec", [])
        tipi = manifest_dict.get("index-tipi", [])

        ncm_final_path = os.path.join(ROOT_DIR, ncm[interval][prefix])
        tec_final_path = os.path.join(ROOT_DIR, tec[interval])
        tipi_final_path = os.path.join(ROOT_DIR, tipi[interval])

        rows = load_chapter_rows(ncm_final_path)

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
        else:
            print("\nEste código não possui filhos (é um código folha).")

        print("\nALIQUOTAS \n")
        
        with open(tec_final_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            found = False
            next(reader, None)

            for row in reader:
                if (row[0] == ncm_code) or (row[0] == ncm_code[0:8] + "00"):
                    found = True
                    print("Aliquota TEC: \t" + to_percentage(row[1]))
            if not found:
                print("Alíquota TEC: \tN/T")

        with open(tipi_final_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            found = False
            next(reader, None)

            for row in reader:
                if (row[0] == ncm_code) or (row[0] == ncm_code[0:8] + "00"):
                    found = True
                    print("Aliquota TIPI: \t" + to_percentage(row[2]))
            if not found:
                print("Alíquota TIPI: \tN/T")


if __name__ == "__main__":
    ncm_code = input("> Coloque o seu código NCM: ")
    search_for_taxes_by_ncm(ncm_code)
