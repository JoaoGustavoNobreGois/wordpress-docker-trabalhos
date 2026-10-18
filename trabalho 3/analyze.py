"""Consolida os CSV reais do Locust e desenha os gráficos do enunciado."""

import csv
import json
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
RAW = RESULTS / "raw"
CHARTS = RESULTS / "graficos"
SCENARIOS = ("imagem-1mb", "texto-400kb", "imagem-300kb")
USERS = (10, 50, 100)
INSTANCES = (1, 2, 3)
COLORS = {1: "#2563eb", 2: "#16a34a", 3: "#dc2626"}


def locust_row(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            if row.get("Name") == "Aggregated":
                return row
    raise ValueError(f"Linha Aggregated ausente: {path}")


def number(value: str) -> float:
    return float(value.replace(",", "."))


def summarize() -> list[dict]:
    runs = json.loads((RESULTS / "runs.json").read_text(encoding="utf-8"))["runs"]
    expected = {(s, i, u) for s in SCENARIOS for i in INSTANCES for u in USERS}
    actual = {(r["scenario"], r["instances"], r["users"]) for r in runs}
    if len(runs) != 27 or actual != expected:
        raise ValueError(f"Matriz incompleta: {len(runs)} testes; faltam {sorted(expected - actual)}")

    summary = []
    for run in runs:
        row = locust_row(RAW / f"{run['run_id']}_stats.csv")
        requests = int(row["Request Count"])
        failures = int(row["Failure Count"])
        summary.append({
            "cenario": run["scenario"],
            "instancias": run["instances"],
            "usuarios": run["users"],
            "duracao": run["duration"],
            "requisicoes": requests,
            "falhas": failures,
            "taxa_falhas_pct": round(100 * failures / requests, 3) if requests else 0,
            "tempo_medio_ms": round(number(row["Average Response Time"]), 3),
            "mediana_ms": round(number(row["Median Response Time"]), 3),
            "p95_ms": round(number(row["95%"]), 3),
            "requisicoes_por_segundo": round(number(row["Requests/s"]), 3),
            "bytes_medios_resposta": round(number(row["Average Content Size"]), 3),
            "locust_exit_code": run["locust_exit_code"],
        })
    return summary


def chart(scenario: str, records: list[dict], metric: str, label: str, unit: str, filename: str) -> None:
    width, height = 900, 510
    left, right, top, bottom = 105, 40, 75, 95
    plot_w, plot_h = width - left - right, height - top - bottom
    max_y = max(float(record[metric]) for record in records)
    ceiling = max(1.0, max_y * 1.15)

    def x(users: int) -> float:
        return left + (users - min(USERS)) * plot_w / (max(USERS) - min(USERS))

    def y(value: float) -> float:
        return top + plot_h - value * plot_h / ceiling

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2}" y="35" text-anchor="middle" font-family="sans-serif" font-size="22" font-weight="bold">{escape(scenario)} — {escape(label)}</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#334155"/>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#334155"/>',
    ]
    for tick in range(5):
        value = ceiling * tick / 4
        py = y(value)
        lines.append(f'<line x1="{left}" y1="{py:.1f}" x2="{left + plot_w}" y2="{py:.1f}" stroke="#e2e8f0"/>')
        lines.append(f'<text x="{left - 12}" y="{py + 5:.1f}" text-anchor="end" font-family="sans-serif" font-size="14" fill="#334155">{value:.1f}</text>')
    for users in USERS:
        px = x(users)
        lines.append(f'<text x="{px:.1f}" y="{top + plot_h + 28}" text-anchor="middle" font-family="sans-serif" font-size="14">{users}</text>')
    lines.append(f'<text x="{width / 2}" y="{height - 29}" text-anchor="middle" font-family="sans-serif" font-size="15">Usuários simultâneos</text>')
    lines.append(f'<text transform="translate(27 {height / 2}) rotate(-90)" text-anchor="middle" font-family="sans-serif" font-size="15">{escape(label)} ({escape(unit)})</text>')

    for instances in INSTANCES:
        points = sorted((r for r in records if r["instancias"] == instances), key=lambda r: r["usuarios"])
        coordinates = " ".join(f'{x(r["usuarios"]):.1f},{y(float(r[metric])):.1f}' for r in points)
        color = COLORS[instances]
        lines.append(f'<polyline points="{coordinates}" fill="none" stroke="{color}" stroke-width="3"/>')
        for record in points:
            lines.append(f'<circle cx="{x(record["usuarios"]):.1f}" cy="{y(float(record[metric])):.1f}" r="5" fill="{color}"/>')
        legend_x = left + instances * 170 - 120
        lines.append(f'<line x1="{legend_x}" y1="{height - 65}" x2="{legend_x + 30}" y2="{height - 65}" stroke="{color}" stroke-width="3"/>')
        lines.append(f'<text x="{legend_x + 38}" y="{height - 60}" font-family="sans-serif" font-size="14">{instances} instância(s)</text>')
    lines.append('</svg>')
    (CHARTS / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    summary = summarize()
    RESULTS.mkdir(exist_ok=True)
    CHARTS.mkdir(exist_ok=True)
    with (RESULTS / "resumo.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)

    metrics = (
        ("tempo_medio_ms", "Tempo médio de resposta", "ms", "tempo-medio"),
        ("requisicoes_por_segundo", "Vazão", "req/s", "requisicoes-por-segundo"),
        ("taxa_falhas_pct", "Taxa de falhas", "%", "taxa-de-falhas"),
    )
    for scenario in SCENARIOS:
        records = [row for row in summary if row["cenario"] == scenario]
        for metric, label, unit, name in metrics:
            chart(scenario, records, metric, label, unit, f"{scenario}-{name}.svg")

    failures = sum(row["falhas"] for row in summary)
    requests = sum(row["requisicoes"] for row in summary)
    print(f"27 combinações consolidadas; {requests} requisições, {failures} falhas.")
    print(f"Resumo: {RESULTS / 'resumo.csv'}")
    print(f"Gráficos: {CHARTS}")


if __name__ == "__main__":
    main()
