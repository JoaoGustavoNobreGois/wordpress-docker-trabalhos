from locust import HttpUser, task, between

# Lista com 10 URLs diferentes exigidas pelo enunciado do Trabalho 4
URLS_TESTE = [
    "http://example.com/",
    "http://www.iana.org/domains/reserved",
    "http://info.cern.ch/",
    "http://httpbin.org/html",
    "http://example.org/",
    "http://example.net/",
    "http://example.edu/",
    "http://www.w3.org/TR/PNG/iso_8859-1.txt",
    "http://tools.ietf.org/html/rfc7231",
    "http://github.com/"
]

class LinkExtractorUser(HttpUser):
    wait_time = between(0.5, 1.5)

    @task
    def extract_links_sequence(self):
        # Executa a sequência de 10 invocações passando uma URL diferente a cada passo
        for url in URLS_TESTE:
            with self.client.get(
                f"/?url={url}", 
                name="Extrair Links (10 URLs)", 
                catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Falha HTTP {response.status_code} para a URL: {url}")
                else:
                    response.success()