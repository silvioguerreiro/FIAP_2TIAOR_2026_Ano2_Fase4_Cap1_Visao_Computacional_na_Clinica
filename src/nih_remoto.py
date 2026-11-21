"""Download seletivo de imagens do NIH Chest X-ray a partir do espelho publico no Hugging Face.

O dataset completo ocupa cerca de 42 GB em 12 arquivos zip. Como o formato zip guarda um
indice (diretorio central) no fim do arquivo, e possivel ler apenas esse indice e depois
pedir ao servidor so os bytes de cada imagem desejada (requisicoes HTTP com Range).
Assim baixamos apenas o subconjunto usado no projeto.
"""
import io
import json
import struct
import time
import zipfile
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

BASE = "https://huggingface.co/datasets/alkzar90/NIH-Chest-X-ray-dataset/resolve/main/data"
ZIPS = [f"images/images_{i:03d}.zip" for i in range(1, 13)]


class _HttpFile(io.RawIOBase):
    """Arquivo somente leitura sobre HTTP Range, suficiente para o modulo zipfile ler o indice."""

    def __init__(self, url, sessao):
        self.url, self.s, self.pos = url, sessao, 0
        r = self.s.head(url, allow_redirects=True, timeout=60)
        r.raise_for_status()
        self.tam = int(r.headers["Content-Length"])
        self._ini, self._buf = None, b""

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.tam + off)
        return self.pos

    def read(self, n=-1):
        if n < 0:
            n = self.tam - self.pos
        fim = min(self.pos + n, self.tam)
        if fim <= self.pos:
            return b""
        if self._ini is None or self.pos < self._ini or fim > self._ini + len(self._buf):
            # le blocos grandes a partir do fim para cobrir o diretorio central com poucas requisicoes
            ini = max(0, min(self.pos, self.tam - 4 * 1024 * 1024))
            r = self.s.get(self.url, headers={"Range": f"bytes={ini}-{max(fim, ini + 4 * 1024 * 1024) - 1}"}, timeout=120)
            r.raise_for_status()
            self._ini, self._buf = ini, r.content
        dados = self._buf[self.pos - self._ini: fim - self._ini]
        self.pos = fim
        return dados


def construir_indice(cache_json):
    """Le o diretorio central dos 12 zips e devolve {nome_da_imagem: [zip, offset, tam_comprimido, metodo]}."""
    cache_json = Path(cache_json)
    if cache_json.exists():
        # descarta entradas "._*", arquivos auxiliares do macOS presentes em alguns zips do espelho
        return {k: v for k, v in json.loads(cache_json.read_text()).items() if not k.startswith(".")}
    s = requests.Session()
    indice = {}
    for z in ZIPS:
        f = _HttpFile(f"{BASE}/{z}", s)
        with zipfile.ZipFile(f) as zf:
            for info in zf.infolist():
                nome = Path(info.filename).name
                if nome.endswith(".png") and not nome.startswith("."):
                    indice[nome] = [z, info.header_offset, info.compress_size, info.compress_type]
        print(f"{z}: indice lido, total acumulado {len(indice)} imagens")
    cache_json.parent.mkdir(parents=True, exist_ok=True)
    cache_json.write_text(json.dumps(indice))
    return indice


def _baixar_uma(nome, entrada, destino, sessao, tentativas=5):
    saida = Path(destino) / nome
    if saida.exists() and saida.stat().st_size > 0:
        return "cache"
    z, off, csize, metodo = entrada
    fim = off + 30 + 400 + csize  # cabecalho local (30) + folga para nome e campo extra
    for t in range(tentativas):
        try:
            r = sessao.get(f"{BASE}/{z}", headers={"Range": f"bytes={off}-{fim}"}, timeout=120)
            if r.status_code == 429:  # limite de requisicoes do servidor: espera o tempo pedido antes de tentar de novo
                pedido = r.headers.get("Retry-After", "")
                time.sleep(min(int(pedido) if pedido.isdigit() else 10 * (t + 1), 60))
            r.raise_for_status()
            b = r.content
            assert b[:4] == b"PK\x03\x04", "cabecalho local invalido"
            n, m = struct.unpack("<HH", b[26:30])
            comp = b[30 + n + m: 30 + n + m + csize]
            assert len(comp) == csize, "conteudo truncado"
            dados = comp if metodo == 0 else zlib.decompressobj(-15).decompress(comp)
            assert dados[:8] == b"\x89PNG\r\n\x1a\n", "nao e PNG"
            tmp = saida.with_suffix(".part")
            tmp.write_bytes(dados)
            tmp.rename(saida)
            return "baixada"
        except Exception as e:  # rede instavel: tenta de novo com espera crescente
            erro = e
            time.sleep(2 * (t + 1))
    return f"erro: {erro}"


def baixar_imagens(nomes, destino, indice, n_threads=12, rodadas_extras=3, pausa=30):
    """Baixa as imagens listadas para a pasta destino. Retoma de onde parou se interrompido.

    O servidor limita o numero de requisicoes e pode recusar algumas imagens (erro 429). As que
    falham na primeira passagem sao tentadas de novo em ate `rodadas_extras` rodadas, com menos
    conexoes e uma pausa de `pausa` segundos antes de cada uma.
    """
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    sessao = requests.Session()
    ad = requests.adapters.HTTPAdapter(pool_connections=n_threads, pool_maxsize=n_threads)
    sessao.mount("https://", ad)
    res = {"cache": 0, "baixada": 0, "erro": []}
    with ThreadPoolExecutor(n_threads) as ex:
        fut = {ex.submit(_baixar_uma, n, indice[n], destino, sessao): n for n in nomes}
        for i, f in enumerate(as_completed(fut), 1):
            r = f.result()
            if r.startswith("erro"):
                res["erro"].append((fut[f], r))
            else:
                res[r] += 1
            if i % 500 == 0 or i == len(fut):
                print(f"{i}/{len(fut)} processadas | novas {res['baixada']} | em cache {res['cache']} | erros {len(res['erro'])}", flush=True)
    for rodada in range(1, rodadas_extras + 1):
        if not res["erro"]:
            break
        pendentes, res["erro"] = [n for n, _ in res["erro"]], []
        print(f"{len(pendentes)} imagens com erro. Nova tentativa em {pausa} s (rodada extra {rodada} de {rodadas_extras})", flush=True)
        time.sleep(pausa)
        with ThreadPoolExecutor(max(2, n_threads // 4)) as ex:
            fut = {ex.submit(_baixar_uma, n, indice[n], destino, sessao): n for n in pendentes}
            for f in as_completed(fut):
                r = f.result()
                if r.startswith("erro"):
                    res["erro"].append((fut[f], r))
                else:
                    res[r] += 1
        print(f"Rodada extra {rodada}: novas {res['baixada']} | em cache {res['cache']} | erros {len(res['erro'])}", flush=True)
    return res
