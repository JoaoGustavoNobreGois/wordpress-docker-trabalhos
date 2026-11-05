"""Usuário virtual: 10 invocações seguidas ao serviço de extração de links,
cada uma com uma URL diferente, e depois uma pausa de 0,5 a 1,5 s."""

import os

from locust import HttpUser, between, task

# Endereço das páginas visto de dentro do serviço de extração.
SITES_BASE = os.getenv("SITES_BASE", "http://sites").rstrip("/")
URLS = [f"{SITES_BASE}/pagina-{n:02d}.html" for n in range(1, 11)]


class LinkExtractorUser(HttpUser):
    wait_time = between(0.5, 1.5)

    @task
    def extrair_dez_urls(self):
        for n, url in enumerate(URLS, start=1):
            with self.client.get(
                f"/api/{url}",
                name=f"/api/pagina-{n:02d}",
                catch_response=True,
            ) as response:
                if response.status_code != 200:
                    response.failure(f"HTTP {response.status_code}")
                    continue
                try:
                    links = response.json()
                except ValueError:
                    response.failure("Resposta não é JSON")
                    continue
                if not links:
                    response.failure("Nenhum link extraído")
