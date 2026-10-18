"""Um usuário virtual lê a publicação e, quando houver, a imagem embutida."""

import json
import os
from pathlib import Path

from locust import HttpUser, between, task


SCENARIO = os.getenv("SCENARIO", "imagem-1mb")
MANIFEST = json.loads(
    Path("/mnt/site/wp-content/uploads/locust/scenarios.json").read_text(encoding="utf-8")
)
if SCENARIO not in MANIFEST:
    raise ValueError(f"Cenário desconhecido: {SCENARIO}")
DATA = MANIFEST[SCENARIO]
HEADERS = {"Host": "localhost:8090"}


class BlogReader(HttpUser):
    wait_time = between(0.2, 0.8)

    @task
    def read_post(self):
        with self.client.get(
            f"/?p={DATA['post_id']}",
            name=f"{SCENARIO}: página",
            headers=HEADERS,
            allow_redirects=False,
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code} na publicação")
            elif DATA["image_path"] and DATA["image_path"].encode() not in response.content:
                response.failure("A publicação não contém o caminho da imagem")
            elif DATA["text_bytes"] and len(response.content) < DATA["text_bytes"]:
                response.failure("A resposta não contém o texto esperado")

        if DATA["image_path"]:
            with self.client.get(
                DATA["image_path"],
                name=f"{SCENARIO}: imagem",
                headers=HEADERS,
                allow_redirects=False,
                catch_response=True,
            ) as response:
                if response.status_code != 200:
                    response.failure(f"HTTP {response.status_code} na imagem")
                elif len(response.content) != DATA["image_bytes"]:
                    response.failure("Tamanho da imagem diferente do esperado")
