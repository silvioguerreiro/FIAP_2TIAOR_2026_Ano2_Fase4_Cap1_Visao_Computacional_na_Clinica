"""Grava a demonstracao do app CardioIA (versao web, React Native Web) em tela de celular.

Abre o app no Chrome instalado (Playwright, canal "chrome", sem janela), executa o roteiro de toques e
captura os quadros da tela pelo protocolo DevTools (Page.startScreencast). Registra o instante de cada
legenda em eventos.json e monta tela.mp4 a 30 quadros por segundo.

Requisitos: backend Flask em execucao (python app/app.py) com a versao web do app em /mobile/, e
pip install playwright imageio-ffmpeg.

Uso:
  python gravar_demo.py --saida ~/cardioia-data/video --imagem ~/cardioia-data/raw/00004630_002.png --esperado 47
"""
import argparse
import asyncio
import base64
import json
import subprocess
import time
import traceback
from pathlib import Path

from playwright.async_api import async_playwright

LARGURA, ALTURA, ESCALA, FPS = 390, 844, 2, 30

# Indicador visual de toque (a gravacao nao mostra cursor) e localizador da area rolavel da tela.
APOIO_JS = r"""
(() => {
  const estilo = 'position:fixed;width:46px;height:46px;margin:-23px 0 0 -23px;border-radius:50%;pointer-events:none;z-index:2147483647;' +
                 'background:rgba(255,160,0,0.40);border:3px solid rgba(255,140,0,0.95);box-shadow:0 0 0 2px rgba(255,255,255,0.85);';
  window.__dedo = (x, y) => {
    const d = document.createElement('div');
    d.id = '__dedo';
    d.style.cssText = estilo + `left:${x}px;top:${y}px;opacity:0;transform:scale(1.6);transition:opacity .25s ease-out, transform .25s ease-out;`;
    document.body.appendChild(d);
    requestAnimationFrame(() => { d.style.opacity = '1'; d.style.transform = 'scale(1)'; });
  };
  window.addEventListener('pointerdown', () => {
    const d = document.getElementById('__dedo');
    if (!d) return;
    d.removeAttribute('id');
    d.style.transition = 'opacity .45s ease-out, transform .45s ease-out';
    d.style.transform = 'scale(0.55)';
    setTimeout(() => { d.style.transform = 'scale(1.9)'; d.style.opacity = '0'; }, 120);
    setTimeout(() => d.remove(), 700);
  }, true);
  window.__rolavel = () => [...document.querySelectorAll('div')]
    .filter((e) => { const s = getComputedStyle(e); return (s.overflowY === 'auto' || s.overflowY === 'scroll') && e.clientHeight > 300; })
    .sort((a, b) => b.clientHeight - a.clientHeight)[0];
})();
"""


class Gravador:
    def __init__(self, page, cdp, pasta):
        self.page, self.cdp, self.pasta = page, cdp, pasta
        self.quadros = []   # (instante informado pelo Chrome, instante de chegada, arquivo)
        self.eventos = []

    def ao_receber(self, p):
        nome = f"q{len(self.quadros):06d}.jpg"
        self.quadros.append((p["metadata"]["timestamp"], time.time(), nome))
        asyncio.create_task(self._salvar(p, nome))

    async def _salvar(self, p, nome):
        (self.pasta / nome).write_bytes(base64.b64decode(p["data"]))
        try:
            await self.cdp.send("Page.screencastFrameAck", {"sessionId": p["sessionId"]})
        except Exception:
            pass

    def marca(self, tipo, **extra):
        self.eventos.append({"t": time.time(), "tipo": tipo, **extra})

    def legenda(self, ident):
        self.marca("legenda", id=ident)

    async def pausa(self, segundos):
        await self.page.wait_for_timeout(int(segundos * 1000))

    async def tocar(self, alvo, antes=0.7, arquivo=None):
        caixa = await alvo.bounding_box()
        x, y = caixa["x"] + caixa["width"] / 2, caixa["y"] + caixa["height"] / 2
        await self.page.evaluate("([x, y]) => window.__dedo(x, y)", [x, y])
        await self.pausa(antes)
        self.marca("toque", x=x, y=y)
        if arquivo:
            async with self.page.expect_file_chooser() as seletor:
                await self.page.touchscreen.tap(x, y)
            await (await seletor.value).set_files(arquivo)
        else:
            await self.page.touchscreen.tap(x, y)

    # Observacao: no React Native Web o metodo scrollTo do elemento e o do ScrollView ({x, y, animated}).
    # Por isso as rolagens abaixo usam o metodo nativo do DOM, scroll({top, behavior}).
    async def rolar_topo(self):
        await self.page.evaluate("() => window.__rolavel().scroll({ top: 0, behavior: 'smooth' })")

    async def rolar_fim(self):
        await self.page.evaluate("() => { const e = window.__rolavel(); e.scroll({ top: e.scrollHeight, behavior: 'smooth' }); }")

    async def rolar_ate(self, alvo, margem=8):
        await alvo.evaluate(
            "(el, m) => { const sc = window.__rolavel(); const r = el.getBoundingClientRect(), s = sc.getBoundingClientRect();"
            " sc.scroll({ top: sc.scrollTop + r.top - s.top - m, behavior: 'smooth' }); }", margem)

    async def resultado(self, texto):
        """Espera a analise terminar e confere se a tela mostra o valor esperado."""
        await self.pausa(0.25)
        await self.page.wait_for_function(
            "(t) => { const b = document.body.innerText; return !b.includes('Analisando a imagem') && b.includes(t); }",
            arg=texto, timeout=30000)
        self.marca("resultado", texto=texto)


async def roteiro(g, page, args):
    ex = lambda n: page.get_by_label(f"Analisar exemplo {n}")
    g.marca("inicio")
    # 1. Abertura
    g.legenda("A1"); await g.pausa(5.5)
    g.legenda("A2"); await g.pausa(5.5)
    # 2. Exemplo com cardiomegalia
    g.legenda("B1"); await g.pausa(1.8)
    await g.tocar(ex(3))
    await g.resultado("Probabilidade de cardiomegalia: 88%")
    await g.pausa(3.0)
    g.legenda("B2"); await g.pausa(6.0)
    g.legenda("B3"); await g.pausa(6.0)
    # 3. Exemplo sem achado
    g.legenda("C1"); await g.pausa(0.8)
    await g.rolar_topo(); await g.pausa(1.3)
    await g.tocar(ex(2))
    await g.resultado("Probabilidade de cardiomegalia: 34%")
    await g.pausa(2.0)
    g.legenda("C2"); await g.pausa(7.0)
    # 4. Envio de imagem do dispositivo
    g.legenda("D1"); await g.pausa(0.8)
    await g.rolar_topo(); await g.pausa(1.5)
    await g.tocar(page.get_by_role("button", name="Escolher imagem"), arquivo=args.imagem)
    await g.resultado(f"Probabilidade de cardiomegalia: {args.esperado}%")
    await g.pausa(2.5)
    g.legenda("D2"); await g.pausa(6.5)
    g.legenda("D3"); await g.pausa(6.5)
    # 5. Erros do modelo e limitacoes
    g.legenda("F1"); await g.pausa(0.8)
    await g.rolar_topo(); await g.pausa(2.2)
    await g.tocar(ex(1))
    await g.resultado("Probabilidade de cardiomegalia: 97%")
    await g.pausa(1.5)
    g.legenda("F2"); await g.pausa(6.5)
    await g.rolar_ate(page.get_by_text("Como interpretar"), 30); await g.pausa(1.0)
    g.legenda("F3"); await g.pausa(7.0)
    g.legenda("F4"); await g.pausa(6.5)
    # 6. Conexao com o backend
    g.legenda("E1"); await g.pausa(1.2)
    await g.tocar(page.get_by_text("Configurar endereço do servidor"))
    await page.get_by_text("Testar conexão").wait_for(state="visible")
    await g.pausa(0.4)
    await g.rolar_fim(); await g.pausa(1.6)
    await g.tocar(page.get_by_text("Testar conexão"))
    await g.pausa(4.5)
    g.marca("fim")


async def gravar(args, saida):
    pasta = saida / "quadros"
    pasta.mkdir(parents=True, exist_ok=True)
    for f in pasta.glob("*.jpg"):
        f.unlink()
    problemas = []
    async with async_playwright() as pw:
        # --force-device-scale-factor=2 faz a captura de tela sair em 780 x 1688 (2x), como em um celular real
        nav = await pw.chromium.launch(channel="chrome", headless=True, args=["--force-device-scale-factor=2"])
        ctx = await nav.new_context(viewport={"width": LARGURA, "height": ALTURA}, device_scale_factor=ESCALA,
                                    is_mobile=True, has_touch=True, locale="pt-BR")
        await ctx.add_init_script(APOIO_JS)
        page = await ctx.new_page()
        page.on("console", lambda m: problemas.append(f"console {m.type}: {m.text}") if m.type == "error" else None)
        page.on("requestfailed", lambda r: problemas.append(f"requisicao falhou: {r.url}"))
        await page.goto(args.url, wait_until="networkidle")
        await page.get_by_label("Analisar exemplo 1").wait_for(state="visible")
        cdp = await ctx.new_cdp_session(page)
        g = Gravador(page, cdp, pasta)
        cdp.on("Page.screencastFrame", g.ao_receber)
        await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "everyNthFrame": 1})
        await g.pausa(1.2)
        try:
            await roteiro(g, page, args)
        except Exception:
            problemas.append("ROTEIRO INTERROMPIDO: " + traceback.format_exc())
            await page.screenshot(path=str(saida / "falha.png"))
        await cdp.send("Page.stopScreencast")
        await g.pausa(0.4)
        await nav.close()
    return g, problemas


def montar(saida, g):
    """Gera tela.mp4 com taxa constante: cada quadro de saida usa a ultima captura anterior ao seu instante."""
    import imageio_ffmpeg
    from PIL import Image
    marcas = {e["tipo"]: e["t"] for e in g.eventos if e["tipo"] in ("inicio", "fim")}
    quadros = sorted(g.quadros)
    # usa o relogio do Chrome se ele estiver alinhado com o relogio local; senao, o instante de chegada
    desvio = sorted(c - t for t, c, _ in quadros)[len(quadros) // 2]
    tempos = [t for t, _, _ in quadros] if abs(desvio) < 0.5 else [c for _, c, _ in quadros]
    t0, t1 = marcas["inicio"], marcas.get("fim", tempos[-1])
    n = int(round((t1 - t0) * FPS))
    larg, alt = Image.open(saida / "quadros" / quadros[0][2]).size
    tmp = saida / "tela.tmp.mp4"
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "image2pipe", "-c:v", "mjpeg", "-framerate", str(FPS), "-i", "-",
           "-vf", "scale=in_color_matrix=bt601:in_range=full:out_color_matrix=bt709:out_range=tv,format=yuv420p",
           "-c:v", "libx264", "-crf", "14", "-preset", "veryfast", "-pix_fmt", "yuv420p",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", str(tmp)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    j, dados = 0, None
    for k in range(n):
        t = t0 + k / FPS
        while j + 1 < len(quadros) and tempos[j + 1] <= t:
            j, dados = j + 1, None
        if dados is None:
            dados = (saida / "quadros" / quadros[j][2]).read_bytes()
        proc.stdin.write(dados)
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg falhou")
    tmp.rename(saida / "tela.mp4")
    return {"t0": t0, "duracao": n / FPS, "quadros_capturados": len(quadros), "quadros_no_video": n, "dimensao": [larg, alt],
            "desvio_relogio_chrome": round(desvio, 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:5050/mobile/")
    ap.add_argument("--saida", default="~/cardioia-data/video")
    ap.add_argument("--imagem", required=True, help="radiografia enviada pelo botao Escolher imagem")
    ap.add_argument("--esperado", required=True, help="percentual que a tela deve mostrar para essa imagem, ex.: 47")
    args = ap.parse_args()
    args.imagem = str(Path(args.imagem).expanduser())
    saida = Path(args.saida).expanduser()
    saida.mkdir(parents=True, exist_ok=True)
    for antigo in ("tela.mp4", "eventos.json", "falha.png"):
        (saida / antigo).unlink(missing_ok=True)
    g, problemas = asyncio.run(gravar(args, saida))
    info = montar(saida, g) if not any(p.startswith("ROTEIRO") for p in problemas) else {}
    t0 = info.get("t0", g.eventos[0]["t"] if g.eventos else 0)
    eventos = [{**e, "t": round(e["t"] - t0, 3)} for e in g.eventos]
    (saida / "eventos.json").write_text(json.dumps({"video": info, "eventos": eventos, "problemas": problemas, "imagem_enviada": Path(args.imagem).name,
                                                    "url": args.url, "viewport": [LARGURA, ALTURA], "escala": ESCALA}, indent=1, ensure_ascii=False))
    print(json.dumps({"video": info, "problemas": problemas}, ensure_ascii=False))


if __name__ == "__main__":
    main()
