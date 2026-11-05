"""Executa a matriz de testes: 2 versões × 2 modos de cache × N quantidades de usuários.

Por padrão sobe tudo com Docker Compose. Com --local, roda os mesmos serviços
como processos da máquina (Redis, Nginx, Python e Ruby instalados localmente).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
RAW = RESULTS / "raw"
PAGES = ROOT / "generated" / "sites"
VERSIONS = {"python": 5000, "ruby": 4567}
CACHE_MODES = ("on", "off")
DEFAULT_USERS = (10, 50, 100, 200)


def call(command, env=None, check=True, **kwargs):
    print("+", " ".join(str(c) for c in command), flush=True)
    done = subprocess.run(command, cwd=ROOT, env=env, check=False, **kwargs)
    if check and done.returncode:
        raise RuntimeError(f"Comando terminou com código {done.returncode}.")
    return done.returncode


def wait_http(url: str, timeout: float = 120) -> None:
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                body = response.read()
                if response.status == 200 and body:
                    return
        except Exception as error:  # noqa: BLE001 - só queremos esperar o serviço subir
            last = str(error)
        time.sleep(1)
    raise RuntimeError(f"{url} não respondeu: {last}")


# ---------------------------------------------------------------- Docker Compose
class DockerBackend:
    sites_base = "http://sites"

    def __init__(self):
        if shutil.which("docker") is None:
            raise RuntimeError("Docker não encontrado. Use --local para rodar sem contêineres.")
        self.compose = ["docker", "compose"]

    def env(self, cache):
        env = os.environ.copy()
        env["CACHE"] = cache
        return env

    @contextmanager
    def stack(self, cache):
        env = self.env(cache)
        call(self.compose + ["down", "--remove-orphans"], env)
        call(self.compose + ["up", "-d", "--build", "--wait", "redis", "sites",
                             "api-python", "api-ruby"], env)
        try:
            for version, port in VERSIONS.items():
                wait_http(f"http://127.0.0.1:{port}/api/http://sites/pagina-01.html")
            yield
        finally:
            call(self.compose + ["down", "--remove-orphans"], env, check=False)

    def flush_cache(self, cache):
        call(self.compose + ["exec", "-T", "redis", "redis-cli", "FLUSHALL"], self.env(cache))

    def locust(self, cache, version, args):
        host = f"http://api-{version}:{VERSIONS[version]}"
        return call(self.compose + ["run", "--rm", "--no-deps", "locust",
                                    "-f", "/mnt/locust/locustfile.py", "--host", host,
                                    *[a.replace(str(RAW), "/mnt/results/raw") for a in args]],
                    self.env(cache), check=False)


# ---------------------------------------------------------------- processos locais
class LocalBackend:
    sites_port = 8081
    redis_port = 6379

    def __init__(self, ruby):
        self.ruby = ruby
        self.sites_base = f"http://127.0.0.1:{self.sites_port}"
        self.tmp = Path(tempfile.mkdtemp(prefix="trabalho4-"))
        self.procs = []
        for tool in ("redis-server", "redis-cli", "nginx", ruby):
            if shutil.which(tool) is None:
                raise RuntimeError(f"{tool} não encontrado no PATH.")

    def _spawn(self, name, command, env=None, cwd=ROOT):
        log = open(self.tmp / f"{name}.log", "w")  # noqa: SIM115
        proc = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
        self.procs.append(proc)
        return proc

    def _base_services(self):
        conf = self.tmp / "nginx.conf"
        conf.write_text(
            f"""worker_processes 1;
pid {self.tmp}/nginx.pid;
error_log {self.tmp}/nginx-error.log;
events {{ worker_connections 4096; }}
http {{
  access_log off;
  client_body_temp_path {self.tmp}/body;
  proxy_temp_path {self.tmp}/proxy;
  fastcgi_temp_path {self.tmp}/fastcgi;
  uwsgi_temp_path {self.tmp}/uwsgi;
  scgi_temp_path {self.tmp}/scgi;
  server {{
    listen 127.0.0.1:{self.sites_port};
    root "{PAGES}";
  }}
}}
""",
            encoding="utf-8",
        )
        self._spawn("nginx", ["nginx", "-c", str(conf), "-g", "daemon off;"])
        self._spawn("redis", ["redis-server", "--port", str(self.redis_port), "--save", "",
                              "--appendonly", "no"])
        wait_http(f"{self.sites_base}/pagina-01.html", 30)

    @contextmanager
    def stack(self, cache):
        self._base_services()
        env = os.environ.copy()
        env.update(CACHE=cache, REDIS_URL=f"redis://127.0.0.1:{self.redis_port}")
        self._spawn(f"python-{cache}", [sys.executable, "main.py"], env, ROOT / "api-python")
        self._spawn(f"ruby-{cache}", [self.ruby, "linkextractor.rb"], env, ROOT / "api-ruby")
        try:
            for port in VERSIONS.values():
                wait_http(f"http://127.0.0.1:{port}/api/{self.sites_base}/pagina-01.html")
            yield
        finally:
            for proc in reversed(self.procs):
                proc.terminate()
            for proc in self.procs:
                try:
                    proc.wait(10)
                except subprocess.TimeoutExpired:
                    proc.kill()
            self.procs.clear()
            time.sleep(1)

    def flush_cache(self, cache):
        call(["redis-cli", "-p", str(self.redis_port), "FLUSHALL"])

    def locust(self, cache, version, args):
        env = os.environ.copy()
        env["SITES_BASE"] = self.sites_base
        return call([sys.executable, "-m", "locust", "-f", str(ROOT / "locustfile.py"),
                     "--host", f"http://127.0.0.1:{VERSIONS[version]}", *args], env, check=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local", action="store_true", help="Roda sem Docker, com processos locais.")
    parser.add_argument("--ruby", default=os.getenv("RUBY", "ruby"), help="Interpretador Ruby (modo --local).")
    parser.add_argument("--users", default=",".join(map(str, DEFAULT_USERS)),
                        help="Quantidades de usuários, separadas por vírgula (padrão: 10,50,100,200).")
    parser.add_argument("--duration", default="60s", help="Duração de cada teste (padrão: 60s).")
    parser.add_argument("--smoke", action="store_true", help="Só 10 usuários por 10 s em cada combinação.")
    args = parser.parse_args()

    users_plan = [int(u) for u in args.users.split(",")]
    duration = args.duration
    if args.smoke:
        users_plan, duration = [10], "10s"

    RESULTS.mkdir(exist_ok=True)
    RAW.mkdir(exist_ok=True)
    if os.name != "nt":
        RESULTS.chmod(0o777)
        RAW.chmod(0o777)
    call([sys.executable, str(ROOT / "generate_pages.py")])
    backend = LocalBackend(args.ruby) if args.local else DockerBackend()

    runs = []
    manifest = RESULTS / "runs.json"
    for cache in CACHE_MODES:
        with backend.stack(cache):
            for version in VERSIONS:
                for users in users_plan:
                    run_id = f"{version}_cache-{cache}_u{users}"
                    print(f"\n=== {version}, cache {cache}, {users} usuários ===", flush=True)
                    backend.flush_cache(cache)
                    started = datetime.now(timezone.utc).isoformat()
                    code = backend.locust(cache, version, [
                        "--headless", "--users", str(users), "--spawn-rate", str(max(1, users // 5)),
                        "--run-time", duration, "--stop-timeout", "10",
                        "--csv", str(RAW / run_id), "--csv-full-history", "--only-summary",
                    ])
                    if not (RAW / f"{run_id}_stats.csv").is_file():
                        raise RuntimeError(f"Locust não gerou {run_id}_stats.csv (saída {code}).")
                    runs.append({
                        "run_id": run_id, "versao": version, "cache": cache, "usuarios": users,
                        "duracao": duration, "inicio": started, "locust_exit_code": code,
                        "modo": "local" if args.local else "docker",
                    })
                    manifest.write_text(json.dumps({"runs": runs}, indent=2, ensure_ascii=False) + "\n",
                                        encoding="utf-8")

    if not args.smoke:
        call([sys.executable, str(ROOT / "analyze.py")])
    print(f"Concluídos {len(runs)} testes. Resultados em {RESULTS}.", flush=True)


if __name__ == "__main__":
    main()
