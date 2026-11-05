# Trabalho 4 — testes de desempenho com o Link Extractor

Testes de carga com [Locust](https://locust.io) nas duas versões do serviço de extração de links do tutorial [Application Containerization and Microservice Orchestration](https://github.com/ibnesayeed/linkextractor): **Python** (passo 5, Flask) e **Ruby** (passo 6, Sinatra), cada uma **com e sem** o cache Redis, e com 10, 50, 100 e 200 usuários virtuais. São 16 testes (2 versões × 2 modos de cache × 4 cargas).

## Arquitetura do teste

```
Locust ──HTTP──> api-python :5000  ┐            ┌─> sites (Nginx com 10 páginas HTML)
         ou ──> api-ruby   :4567  ┴─ CACHE=on ─┤
                                    └──────────> redis
```

- `api-python/` e `api-ruby/`: código do tutorial, com uma única mudança — a variável `CACHE=off` desliga o Redis. A resposta traz o cabeçalho `X-Cache` (`HIT`, `MISS` ou `OFF`) para conferência. Na versão Ruby, `open(url)` virou `URI.open(url)` (exigência do Ruby 3) e o servidor é o Puma.
- `sites`: as [10 páginas](generate_pages.py) que o serviço extrai, com 25 a 500 links cada. Elas ficam num Nginx local para não sobrecarregar sites de terceiros e para que os testes sejam reproduzíveis.
- `www/`: o front-end PHP do tutorial, mantido no Compose para completar a arquitetura. Os testes chamam o serviço de extração diretamente (`/api/<url>`), como pede o enunciado.

## Usuário virtual

O [locustfile](locustfile.py) faz uma sequência de **10 invocações** a `/api/<url>`, cada uma com uma página diferente, e espera de 0,5 a 1,5 s antes de repetir:

```python
URLS = [f"{SITES_BASE}/pagina-{n:02d}.html" for n in range(1, 11)]

class LinkExtractorUser(HttpUser):
    wait_time = between(0.5, 1.5)

    @task
    def extrair_dez_urls(self):
        for n, url in enumerate(URLS, start=1):
            with self.client.get(f"/api/{url}", name=f"/api/pagina-{n:02d}",
                                 catch_response=True) as response:
                ...  # falha se não for HTTP 200 ou se o JSON vier vazio
```

## Executar

Com Docker (Compose v2) e Python 3.10+ com `matplotlib`, a partir da raiz do repositório:

```bash
python "trabalho 4/run_matrix.py"
```

Opções: `--users 10,50,100,200`, `--duration 60s` e `--smoke` (teste rápido). Antes de cada teste o Redis é esvaziado (`FLUSHALL`), então no modo com cache a primeira passada por cada página é sempre um `MISS`.

Sem Docker, o mesmo script roda os serviços como processos locais (requer `redis-server`, `nginx`, Ruby com `sinatra`, `puma`, `nokogiri`, `redis` e Python com `flask`, `requests`, `beautifulsoup4`, `redis`):

```bash
python "trabalho 4/run_matrix.py" --local --ruby /usr/bin/ruby
```

Também há o workflow manual [Trabalho 4](../.github/workflows/trabalho-4.yml) no GitHub Actions.

Para ver a interface do Locust com uma das versões:

```bash
cd "trabalho 4"
python generate_pages.py
CACHE=on docker compose --profile load up -d --build
```

A interface fica em <http://localhost:8089>; o host padrão é `http://api-python:5000` (troque para `http://api-ruby:4567` para testar a versão Ruby).

## Resultados

Ver [results/README.md](results/README.md): resumo em CSV (média, mediana, p90, p95, p99, máximo, vazão e falhas), gráficos e CSVs brutos do Locust.
