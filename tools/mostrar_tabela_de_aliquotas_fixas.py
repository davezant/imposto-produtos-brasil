from globals import get_manifest_dict, read_csv_dicts, to_percentage

# Comando para mostrar as alíquotas padrões (que não dependem do NCM).

def _print_table(title: str, rows: list, percent_columns: set):
    print("\n%s\n" % title)
    if not rows:
        print("(vazio)")
        return
    columns = list(rows[0].keys())
    values = [[to_percentage(r[c]) if c in percent_columns else r[c] for c in columns] for r in rows]
    widths = [min(max(len(c), *(len(v[i]) for v in values)), 60) for i, c in enumerate(columns)]
    print("  ".join(c.ljust(w) for c, w in zip(columns, widths)))
    for v in values:
        print("  ".join(x[:60].ljust(w) for x, w in zip(v, widths)))

if __name__ == "__main__":
    manifest_dict = get_manifest_dict()
    _print_table("PIS/COFINS - regimes padrão",
                 read_csv_dicts(manifest_dict["relacao-pis_cofins"]["padrao"]),
                 {"aliquota_pis", "aliquota_cofins"})
    _print_table("ICMS - alíquotas internas padrão por UF",
                 read_csv_dicts("aliquotas/estadual/standart.csv"),
                 {"aliquota_interna", "fcp", "aliquota_efetiva"})
    _print_table("Regras especiais (importação)",
                 [{k: v for k, v in r.items() if k != "observacao"}
                  for r in read_csv_dicts(manifest_dict["relacao-regras_especiais"]["padrao"])],
                 {"aliquota"})
