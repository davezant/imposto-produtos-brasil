import os
import json
import re
import csv

ROOT_DIR = "../"
MANIFEST_PATH = os.path.join(ROOT_DIR, "manifest.json")

# Funções constantes que podem ser compartilhadas entre as ferramentas.

def format_relation_list_to_list(header: list, row: list, layout: str):
    for n in range(0, len(header)): 
        if header[n] == '':
            pass
        else:
            print(layout % (header[n], row[n]))

def get_manifest_dict() -> dict:
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def find_ncm_interval(ncm_code: str, manifest_dict: dict) -> list | None:
    prefix = ncm_code[:2]
    starting_numbers = int(prefix)
    
    for s in manifest_dict.get("intervalos", []):
        start_str, end_str = s.split("-")

        if int(start_str) <= starting_numbers <= int(end_str):
            return [s, prefix]

    return None

def normalize(ncm: str) -> str:
    return re.sub(r"\D", "", ncm)

def load_chapter_rows(ncm_final_path: str) -> list:
    rows = []
    with open(ncm_final_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            rows.append({"row": row, "digits": normalize(row[0])})
    return rows

def find_ancestors(rows, digits) -> list:
    ancestors = [r for r in rows if r["digits"] != digits and digits.startswith(r["digits"])]
    ancestors.sort(key=lambda r: len(r["digits"]))
    return ancestors

def find_children(rows, digits) -> list:
    candidates = [r for r in rows if len(r["digits"]) > len(digits) and r["digits"].startswith(digits)]
    if not candidates:
        return []
    min_len = min(len(r["digits"]) for r in candidates)
    return [r for r in candidates if len(r["digits"]) == min_len]

def to_percentage(float_in_str: str) -> str:
    converted_float = float(float_in_str) * 100
    return f"{converted_float:g}%"
