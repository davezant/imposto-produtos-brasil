import json

from globals import get_manifest_dict

# Comando para mostrar as referências (fontes oficiais) do 'manifest.json'.

def _print_tree(node, indent=0):
    pad = "  " * indent
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                print("%s%s:" % (pad, key))
                _print_tree(value, indent + 1)
            else:
                print("%s%s: %s" % (pad, key, value))
    elif isinstance(node, list):
        for item in node:
            if isinstance(item, (dict, list)):
                _print_tree(item, indent + 1)
            else:
                print("%s- %s" % (pad, item))

if __name__ == "__main__":
    manifest_dict = get_manifest_dict()
    info = manifest_dict.get("info", {})
    print("Versão dos dados: %s (gerado em %s)\n" % (info.get("versao", "?"), info.get("gerado_em", "?")))
    _print_tree(manifest_dict.get("referencias", {}))
