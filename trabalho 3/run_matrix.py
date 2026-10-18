"""Prepara o blog e executa 3 cenários × 3 cargas × 3 números de instâncias."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
RAW = RESULTS / "raw"
SCENARIOS = ("imagem-1mb", "texto-400kb", "imagem-300kb")
USERS = (10, 50, 100)
INSTANCES = (1, 2, 3)
SITE_URL = "http://localhost:8090"
MANIFEST = ROOT / "html/wp-content/uploads/locust/scenarios.json"


def compose_command() -> list[str]:
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    if shutil.which("docker"):
        return ["docker", "compose"]
    raise RuntimeError("Docker Compose não foi encontrado no PATH.")


def call(command: list[str], env: dict[str, str], check: bool = True) -> int:
    print("+", " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=ROOT, env=env, check=False)
    if check and completed.returncode:
        raise RuntimeError(f"Comando terminou com código {completed.returncode}.")
    return completed.returncode


def env_for(instances: int) -> dict[str, str]:
    env = os.environ.copy()
    env["NGINX_CONF"] = f"./nginx/{instances}.conf"
    return env


def start_stack(compose: list[str], instances: int) -> dict[str, str]:
    env = env_for(instances)
    call(compose + ["down", "--remove-orphans"], env)
    wordpress_services = [f"wordpress{index}" for index in range(1, instances + 1)]
    call(
        compose
        + [
            "up", "-d", "--wait", "--wait-timeout", "180",
            "mysql", *wordpress_services,
        ],
        env,
    )
    call(compose + ["up", "-d", "--wait", "--wait-timeout", "60", "nginx"], env)
    return env


def cli(compose: list[str], env: dict[str, str], args: list[str], check: bool = True) -> int:
    return call(compose + ["run", "--rm", "--no-deps", "wpcli"] + args, env, check)


def setup_blog(compose: list[str], env: dict[str, str]) -> dict:
    if cli(compose, env, ["core", "is-installed"], check=False) != 0:
        cli(
            compose,
            env,
            [
                "core", "install",
                f"--url={SITE_URL}",
                "--title=Teste de carga WordPress",
                "--admin_user=locust-admin",
                f"--admin_password={os.getenv('WP_ADMIN_PASSWORD', 'LocustLocal!2026')}",
                "--admin_email=benchmark@example.test",
                "--skip-email",
            ],
        )
    cli(compose, env, ["eval-file", "/mnt/seed.php"])
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if set(manifest) != set(SCENARIOS):
        raise RuntimeError("O manifesto de cenários está incompleto.")
    return manifest


def check_site(instances: int, manifest: dict) -> None:
    seen: set[str] = set()
    post_id = manifest["texto-400kb"]["post_id"]
    image_path = manifest["imagem-1mb"]["image_path"]
    deadline = time.monotonic() + 90
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{SITE_URL}/?p={post_id}", timeout=10) as response:
                content = response.read()
                if response.status != 200 or len(content) < 400 * 1024:
                    raise RuntimeError("A publicação de texto está incompleta.")
                upstream = response.headers.get("X-Upstream", "")
                if not upstream:
                    raise RuntimeError("Faltou o cabeçalho X-Upstream.")
                seen.add(upstream)
            if len(seen) >= instances:
                with urllib.request.urlopen(SITE_URL + image_path, timeout=10) as response:
                    if response.status != 200 or len(response.read()) != manifest["imagem-1mb"]["image_bytes"]:
                        raise RuntimeError("A imagem de 1 MB não foi servida corretamente.")
                print(f"Instâncias verificadas em X-Upstream: {', '.join(sorted(seen))}", flush=True)
                return
        except (urllib.error.URLError, TimeoutError, RuntimeError) as error:
            last_error = str(error)
        time.sleep(1)
    raise RuntimeError(f"O site não ficou pronto com {instances} instância(s): {last_error}")


def run_load(compose: list[str], env: dict[str, str], scenario: str, instances: int,
             users: int, duration: str) -> dict:
    run_id = f"{scenario}_i{instances}_u{users}"
    run_env = env.copy()
    run_env["SCENARIO"] = scenario
    started_at = datetime.now(timezone.utc).isoformat()
    command = compose + [
        "run", "--rm", "--no-deps", "-e", f"SCENARIO={scenario}", "locust",
        "-f", "/mnt/locust/locustfile.py",
        "--host", "http://nginx",
        "--headless", "--users", str(users), "--spawn-rate", str(users),
        "--run-time", duration,
        "--csv", f"/mnt/results/raw/{run_id}", "--csv-full-history",
        "--only-summary",
    ]
    exit_code = call(command, run_env, check=False)
    stats_path = RAW / f"{run_id}_stats.csv"
    if not stats_path.is_file():
        raise RuntimeError(f"Locust não gerou {stats_path.name} (saída {exit_code}).")
    return {
        "run_id": run_id,
        "scenario": scenario,
        "instances": instances,
        "users": users,
        "duration": duration,
        "started_at": started_at,
        "locust_exit_code": exit_code,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", default="30s", help="Duração de cada teste Locust (padrão: 30s).")
    parser.add_argument("--smoke", action="store_true", help="Executa só 1 cenário com 1 instância e 10 usuários.")
    args = parser.parse_args()

    RESULTS.mkdir(exist_ok=True)
    RAW.mkdir(exist_ok=True)
    if os.name != "nt":
        RESULTS.chmod(0o777)
        RAW.chmod(0o777)
    call([sys.executable, str(ROOT / "generate_fixtures.py")], os.environ.copy())
    compose = compose_command()
    runs = []
    fixture_sizes = json.loads((ROOT / "generated/sizes.json").read_text(encoding="utf-8"))
    run_plan = (1,) if args.smoke else INSTANCES
    for instances in run_plan:
        env = start_stack(compose, instances)
        manifest = setup_blog(compose, env) if instances == 1 else json.loads(MANIFEST.read_text(encoding="utf-8"))
        check_site(instances, manifest)
        scenarios = SCENARIOS[:1] if args.smoke else SCENARIOS
        users_plan = USERS[:1] if args.smoke else USERS
        for scenario in scenarios:
            for users in users_plan:
                print(f"\n=== {scenario}, {instances} WordPress, {users} usuários ===", flush=True)
                runs.append(run_load(compose, env, scenario, instances, users, args.duration))
                (RESULTS / "runs.json").write_text(
                    json.dumps({"fixtures": fixture_sizes, "runs": runs}, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )

    if not args.smoke:
        call([sys.executable, str(ROOT / "analyze.py")], os.environ.copy())
    print(f"Concluídos {len(runs)} testes. Resultados em {RESULTS}.", flush=True)


if __name__ == "__main__":
    main()
