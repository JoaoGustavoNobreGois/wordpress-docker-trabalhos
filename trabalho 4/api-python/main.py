#!/usr/bin/env python
"""Serviço de extração de links (versão Python, passo 5 do tutorial).

Única mudança em relação ao tutorial: a variável CACHE=off desliga o Redis,
para comparar o serviço com e sem cache usando o mesmo código.
"""

import json
import os

from flask import Flask, request

from linkextractor import extract_links

app = Flask(__name__)
CACHE_ENABLED = os.getenv("CACHE", "on").lower() != "off"
redis_conn = None
if CACHE_ENABLED:
    import redis

    redis_conn = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))


@app.route("/")
def index():
    return "Usage: http://<hostname>[:<prt>]/api/<url>"


@app.route("/api/<path:url>")
def api(url):
    qs = request.query_string.decode("utf-8")
    if qs != "":
        url += "?" + qs

    jsonlinks = redis_conn.get(url) if CACHE_ENABLED else None
    cache_status = "HIT" if jsonlinks else "MISS"
    if not jsonlinks:
        links = extract_links(url)
        jsonlinks = json.dumps(links, indent=2)
        if CACHE_ENABLED:
            redis_conn.set(url, jsonlinks)

    response = app.response_class(
        status=200,
        mimetype="application/json",
        response=jsonlinks,
    )
    response.headers["X-Cache"] = cache_status if CACHE_ENABLED else "OFF"
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
