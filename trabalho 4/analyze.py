"""Consolida os CSV do Locust em resultados/resumo.csv e desenha os gráficos.

Requer matplotlib (pip install matplotlib).
"""

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
RAW = RESULTS / "raw"
CHARTS = RESULTS / "graficos"
COLORS = {"python": "#2a78d6", "ruby": "#eb6834"}
STYLES = {"on": "-", "off": "--"}
MARKERS = {"on": "o", "off": "s"}
LABEL_CACHE = {"on": "com cache", "off": "sem cache"}
LABEL_VERSION = {"python": "Python", "ruby": "Ruby"}
INK, MUTED, GRID = "#1f1f1e", "#6b6a63", "#e6e4dc"


def num(value: str) -> float:
    return float(value) if value not in ("", "N/A") else 0.0


def rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def summarize() -> list[dict]:
    runs = json.loads((RESULTS / "runs.json").read_text(encoding="utf-8"))["runs"]
    summary = []
    for run in runs:
        agg = next(r for r in rows(RAW / f"{run['run_id']}_stats.csv") if r["Name"] == "Aggregated")
        requests, failures = int(agg["Request Count"]), int(agg["Failure Count"])
        summary.append({
            "versao": run["versao"],
            "cache": run["cache"],
            "usuarios": run["usuarios"],
            "duracao": run["duracao"],
            "requisicoes": requests,
            "falhas": failures,
            "taxa_falhas_pct": round(100 * failures / requests, 3) if requests else 0.0,
            "tempo_medio_ms": round(num(agg["Average Response Time"]), 2),
            "mediana_ms": num(agg["50%"]),
            "p90_ms": num(agg["90%"]),
            "p95_ms": num(agg["95%"]),
            "p99_ms": num(agg["99%"]),
            "max_ms": round(num(agg["Max Response Time"]), 1),
            "requisicoes_por_segundo": round(num(agg["Requests/s"]), 2),
        })
    return summary


def per_page(run_id: str) -> list[float]:
    data = {r["Name"]: num(r["50%"]) for r in rows(RAW / f"{run_id}_stats.csv")}
    return [data[f"/api/pagina-{n:02d}"] for n in range(1, 11)]


def style_axes(ax, title, ylabel):
    ax.set_title(title, loc="left", fontsize=13, fontweight="bold", color=INK, pad=12)
    ax.set_ylabel(ylabel, color=MUTED, fontsize=10)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#b9b7ad")
    ax.tick_params(colors=MUTED, labelsize=9)


def save(fig, name: str) -> None:
    for ext in ("png", "svg"):
        fig.savefig(CHARTS / f"{name}.{ext}", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def line_chart(summary, metric, title, ylabel, name, log=False):
    users = sorted({r["usuarios"] for r in summary})
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for version in COLORS:
        for cache in STYLES:
            pts = sorted((r for r in summary if r["versao"] == version and r["cache"] == cache),
                         key=lambda r: r["usuarios"])
            if not pts:
                continue
            xs = [users.index(p["usuarios"]) for p in pts]
            ys = [p[metric] for p in pts]
            ax.plot(xs, ys, STYLES[cache], color=COLORS[version], linewidth=2,
                    marker=MARKERS[cache], markersize=7, markeredgecolor="white", markeredgewidth=1.5,
                    label=f"{LABEL_VERSION[version]} {LABEL_CACHE[cache]}")
    ax.set_xticks(range(len(users)), [str(u) for u in users])
    ax.set_xlabel("Usuários virtuais simultâneos", color=MUTED, fontsize=10)
    if log:
        ax.set_yscale("log")
    else:
        ax.set_ylim(bottom=0)
    style_axes(ax, title, ylabel)
    ax.legend(frameon=False, fontsize=9, ncol=2, loc="upper left", handlelength=3.5)
    save(fig, name)


def page_chart(summary, users):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    pages = list(range(1, 11))
    for version in COLORS:
        for cache in STYLES:
            run_id = f"{version}_cache-{cache}_u{users}"
            if not (RAW / f"{run_id}_stats.csv").is_file():
                continue
            ax.plot(pages, per_page(run_id), STYLES[cache], color=COLORS[version], linewidth=2,
                    marker=MARKERS[cache], markersize=6, markeredgecolor="white", markeredgewidth=1.2,
                    label=f"{LABEL_VERSION[version]} {LABEL_CACHE[cache]}")
    links = [p["links"] for p in json.loads((ROOT / "generated/sites/paginas.json").read_text("utf-8"))]
    ax.set_xticks(pages, [f"{n}\n({lk})" for n, lk in zip(pages, links)])
    ax.set_xlabel("Página (quantidade de links)", color=MUTED, fontsize=10)
    ax.set_yscale("log")
    style_axes(ax, f"Mediana por página com {users} usuários", "Mediana (ms, escala log)")
    ax.legend(frameon=False, fontsize=9, ncol=2, loc="upper left", handlelength=3.5)
    save(fig, f"mediana-por-pagina-u{users}")


def main() -> None:
    summary = summarize()
    CHARTS.mkdir(parents=True, exist_ok=True)
    with (RESULTS / "resumo.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)

    line_chart(summary, "mediana_ms", "Mediana do tempo de resposta", "ms (escala log)", "mediana", log=True)
    line_chart(summary, "p95_ms", "Percentil 95 do tempo de resposta", "ms (escala log)", "p95", log=True)
    line_chart(summary, "tempo_medio_ms", "Tempo médio de resposta", "ms (escala log)", "tempo-medio", log=True)
    line_chart(summary, "requisicoes_por_segundo", "Vazão", "requisições/s", "requisicoes-por-segundo")
    line_chart(summary, "taxa_falhas_pct", "Taxa de falhas", "% das requisições", "taxa-de-falhas")
    page_chart(summary, max(r["usuarios"] for r in summary))

    total = sum(r["requisicoes"] for r in summary)
    fails = sum(r["falhas"] for r in summary)
    print(f"{len(summary)} testes consolidados; {total} requisições, {fails} falhas.")


if __name__ == "__main__":
    main()
