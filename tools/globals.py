import os
import json
import re
import csv

# Raiz do repositório, independente do diretório de onde o script é executado.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

def repo_path(relative_path: str) -> str:
    return os.path.join(ROOT_DIR, relative_path)

def read_csv_dicts(relative_path: str) -> list:
    with open(repo_path(relative_path), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def find_ncm_interval(ncm_code: str, manifest_dict: dict) -> list | None:
    prefix = normalize(ncm_code)[:2]
    if len(prefix) < 2:
        return None
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
    """'0.0325' -> '3.25%'. Mantém 'NT' (não tributado) e vazio como estão."""
    if float_in_str is None or str(float_in_str).strip() in ("", "NT"):
        return str(float_in_str or "").strip() or "-"
    converted_float = float(float_in_str) * 100
    return f"{round(converted_float, 6):g}%"
