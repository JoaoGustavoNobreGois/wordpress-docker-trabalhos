"""Cria cargas determinísticas para os três cenários do enunciado."""

import json
import random
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "generated"


def chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


def create_png(path: Path, width: int, height: int, seed: int) -> None:
    rng = random.Random(seed)
    rows = (b"\x00" + rng.randbytes(width * 3) for _ in range(height))
    pixels = zlib.compress(b"".join(rows), level=6)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", pixels)
        + chunk(b"IEND", b"")
    )


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    create_png(OUTPUT / "imagem-1mb.png", 590, 590, 11)
    create_png(OUTPUT / "imagem-300kb.png", 320, 320, 29)

    paragraph = (
        "Teste de carga do WordPress: conteudo textual para medir o tempo de "
        "resposta do Nginx e das instancias do WordPress. "
    )
    target = 400 * 1024
    text = (paragraph * (target // len(paragraph) + 1))[:target]
    (OUTPUT / "texto-400kb.txt").write_text(text, encoding="ascii")

    sizes = {path.name: path.stat().st_size for path in OUTPUT.iterdir() if path.is_file()}
    (OUTPUT / "sizes.json").write_text(
        json.dumps(sizes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    for name, size in sorted(sizes.items()):
        print(f"{name}: {size:,} bytes")


if __name__ == "__main__":
    main()
