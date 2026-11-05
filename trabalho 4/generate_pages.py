"""Gera as 10 páginas HTML que o serviço de extração vai processar.

As páginas ficam num servidor Nginx local (serviço `sites`). Assim o teste
não sobrecarrega sites de terceiros e os resultados são reproduzíveis: cada
página tem sempre a mesma quantidade de links.
"""

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated" / "sites"
LINKS_PER_PAGE = (25, 50, 75, 100, 150, 200, 250, 300, 400, 500)
DOMAINS = ("unifor.br", "example.com", "docker.com", "python.org", "ruby-lang.org",
           "redis.io", "locust.io", "github.com", "wikipedia.org", "w3.org")


def page(index: int, links: int, rng: random.Random) -> str:
    items = []
    for n in range(links):
        if n % 3 == 0:
            href = f"/pagina-{rng.randint(1, 10):02d}.html#secao-{n}"
        else:
            href = f"https://{rng.choice(DOMAINS)}/artigo/{index}-{n}"
        items.append(f'      <li><a href="{href}">Link {n + 1} da página {index}</a></li>')
    paragraph = " ".join(rng.choice(("dados", "rede", "contêiner", "cache", "serviço",
                                     "latência", "carga", "usuário")) for _ in range(120))
    return "\n".join([
        "<!DOCTYPE html>",
        '<html lang="pt-BR">',
        f"  <head><meta charset=\"utf-8\"><title>Página de teste {index:02d}</title></head>",
        "  <body>",
        f"    <h1>Página de teste {index:02d}</h1>",
        f"    <p>{paragraph}</p>",
        "    <ul>",
        *items,
        "    </ul>",
        "  </body>",
        "</html>",
        "",
    ])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(2026)
    manifest = []
    for index, links in enumerate(LINKS_PER_PAGE, start=1):
        name = f"pagina-{index:02d}.html"
        content = page(index, links, rng)
        (OUT / name).write_text(content, encoding="utf-8")
        manifest.append({"pagina": name, "links": links, "bytes": len(content.encode("utf-8"))})
    (OUT / "paginas.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                      encoding="utf-8")
    print(f"{len(manifest)} páginas geradas em {OUT}")


if __name__ == "__main__":
    main()
