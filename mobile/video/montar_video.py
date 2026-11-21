"""Monta o video de demonstracao do app CardioIA (Ir Alem 2) com legendas.

Entrada: tela.mp4 (gravacao da tela do app, 780 x 1688, 30 fps) e eventos.json (instante de cada legenda),
gerados por gravar_demo.py. Saida: video 1920 x 1080 com a tela do app em moldura de celular,
roteiro e legendas ao lado, cartoes de abertura, arquitetura e fechamento, e arquivo .srt.

Uso: python montar_video.py previa   (desenha os cartoes e quadros de conferencia)
     python montar_video.py render   (gera o video final)
Requer: Pillow, numpy, ffmpeg com libx264 no PATH e as fontes Inter (ajuste FONTES para o seu sistema).
O video entregue foi montado em Linux (ffmpeg 6.1), a partir da gravacao feita no macOS.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Pasta com tela.mp4 e eventos.json (saida do gravar_demo.py). Os arquivos intermediarios ficam em <pasta>/montagem.
DADOS = Path(os.environ.get("CARDIOIA_VIDEO", "~/cardioia-data/video")).expanduser()
SEG, PREV = DADOS / "montagem" / "seg", DADOS / "montagem" / "previa"
SAIDA = Path(__file__).resolve().parent
W, H, FPS = 1920, 1080, 30
FONTES = "/usr/share/fonts/opentype/inter/"

BRANCO, SUAVE, APAGADO, AMBAR, ESCURO = (255, 255, 255), (196, 208, 232), (124, 143, 184), (255, 183, 77), (13, 24, 51)
PX, PY, PW, PH = 170, 64, 440, 952          # tela do celular dentro do quadro
BEZ, R_IN = 18, 44
X0, X1 = 700, 1830                          # painel da direita

PASSOS = ["Abertura do app", "Exemplo com cardiomegalia", "Exemplo sem achado", "Envio de imagem do dispositivo",
          "Erros do modelo e limitações", "Conexão com o backend"]
LEGENDAS = {
    "A1": (1, "Este é o CardioIA, app feito em React Native com Expo. A gravação usa a versão web, em tela de celular."),
    "A2": (1, "Ao abrir, o app consulta o backend Flask e carrega as radiografias de exemplo, que vêm do conjunto de teste."),
    "B1": (2, "Ao tocar no Exemplo 3, a imagem é analisada no backend pela CNN treinada na atividade (ResNet50 com Transfer Learning)."),
    "B2": (2, "Categoria detectada: Cardiomegalia, com 88% de probabilidade. O cartão fica vermelho quando o achado é sugestivo."),
    "B3": (2, "A barra mostra os limites de decisão, e o texto explica o resultado em linguagem simples."),
    "C1": (3, "Segundo teste, com o Exemplo 2."),
    "C2": (3, "Probabilidade de 34%, abaixo do limite de 41%. Categoria detectada: Sem achado, em verde."),
    "D1": (4, "Terceiro teste: o botão Escolher imagem envia um arquivo do dispositivo pela rota POST /api/predict."),
    "D2": (4, "Resultado de 47%. Entre 41% e 50% o app mostra Inconclusivo, em laranja, e recomenda revisão."),
    "D3": (4, "Pelo rótulo do dataset, esta imagem é um caso de cardiomegalia. A faixa inconclusiva evita que ele seja descartado."),
    "F1": (5, "O modelo também erra. O Exemplo 1 é rotulado como Sem achado no dataset."),
    "F2": (5, "O app indicou Cardiomegalia, com 97%: um falso positivo, mantido na demonstração para mostrar esse limite."),
    "F3": (5, "No conjunto de teste, de cada 100 casos reais o modelo identificou 87, e de cada 100 alertas 77 estavam corretos."),
    "F4": (5, "O app avalia apenas cardiomegalia e não está validado para menores de 18 anos. O resultado não substitui o médico."),
    "E1": (6, "Por fim, a integração: o endereço do backend Flask é configurável, e o app confirma a conexão e o modelo em uso."),
}
LEGENDA_ARQUITETURA = "O app envia a radiografia e recebe do backend a categoria detectada pela CNN."
D_TITULO, D_ARQ, D_FIM = 5.5, 10.0, 8.0
AVISO = "Protótipo acadêmico, sem validade diagnóstica"


def F(peso, tam, display=False):
    return ImageFont.truetype(f"{FONTES}{'InterDisplay' if display else 'Inter'}-{peso}.otf", tam)


def fundo():
    y = np.linspace(0, 1, H)[:, None, None]
    arr = np.array([11, 21, 46]) + (np.array([25, 47, 94]) - np.array([11, 21, 46])) * y
    arr = np.repeat(arr, W, axis=1)
    arr += np.random.default_rng(7).uniform(-1.2, 1.2, arr.shape)          # pontilhado leve contra faixas no degrade
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def rr(w, h, raio, s=4):
    """Mascara de retangulo arredondado com borda suavizada."""
    m = Image.new("L", (w * s, h * s), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius=raio * s, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def caixa(img, x0, y0, x1, y1, raio, cor, alfa, borda=None):
    w, h = x1 - x0, y1 - y0
    m = rr(w, h, raio)
    if borda:
        cor_b, alfa_b, esp = borda
        img.paste(Image.new("RGB", (w, h), cor_b), (x0, y0), m.point(lambda v: v * alfa_b // 255))
        m2 = rr(w - 2 * esp, h - 2 * esp, max(raio - esp, 1))
        reg = fundo_ref.crop((x0 + esp, y0 + esp, x1 - esp, y1 - esp))
        img.paste(reg, (x0 + esp, y0 + esp), m2)
        img.paste(Image.new("RGB", (w - 2 * esp, h - 2 * esp), cor), (x0 + esp, y0 + esp), m2.point(lambda v: v * alfa // 255))
    else:
        img.paste(Image.new("RGB", (w, h), cor), (x0, y0), m.point(lambda v: v * alfa // 255))


def espacado(d, x, y, texto, fonte, cor, esp=2.5):
    for ch in texto:
        d.text((x, y), ch, font=fonte, fill=cor)
        x += fonte.getlength(ch) + esp
    return x


def larg_espacado(texto, fonte, esp=2.5):
    return sum(fonte.getlength(ch) + esp for ch in texto) - esp


def quebrar(texto, fonte, larg):
    linhas, atual = [], ""
    for p in texto.split():
        t = (atual + " " + p).strip()
        if fonte.getlength(t) <= larg:
            atual = t
        else:
            linhas.append(atual)
            atual = p
    return linhas + ([atual] if atual else [])


def pilula(img, d, x, y, texto):
    f = F("Medium", 26)
    w = int(f.getlength(texto)) + 56
    caixa(img, x, y, x + w, y + 54, 27, AMBAR, 26, borda=(AMBAR, 200, 2))
    ImageDraw.Draw(img).text((x + 28, y + 27), texto, font=f, fill=AMBAR, anchor="lm")
    return w


def seta(d, x0, y0, x1, y1, cor, esp=4, ponta=16):
    d.line((x0, y0, x1, y1), fill=cor, width=esp)
    ang = np.arctan2(y1 - y0, x1 - x0)
    p = [(x1 + ponta * 0.6 * np.cos(ang), y1 + ponta * 0.6 * np.sin(ang)),
         (x1 - ponta * np.cos(ang - 0.5), y1 - ponta * np.sin(ang - 0.5)), (x1 - ponta * np.cos(ang + 0.5), y1 - ponta * np.sin(ang + 0.5))]
    d.polygon(p, fill=cor)


fundo_ref = fundo()


# ---------------------------------------------------------------- cartoes
def cartao_titulo():
    img = fundo_ref.copy()
    d = ImageDraw.Draw(img, "RGBA")
    # linha de ECG decorativa
    xs, pts = 1020, []
    for k in range(3):
        b = xs + k * 290
        pts += [(b, 560), (b + 70, 560), (b + 95, 535), (b + 115, 560), (b + 140, 560), (b + 158, 600), (b + 182, 430), (b + 206, 640), (b + 224, 560), (b + 290, 560)]
    traco = Image.new("L", (W, H), 0)                      # desenhado em mascara para o traco ter opacidade uniforme
    ImageDraw.Draw(traco).line(pts, fill=255, width=6, joint="curve")
    img.paste(Image.new("RGB", (W, H), BRANCO), (0, 0), traco.filter(ImageFilter.GaussianBlur(0.8)).point(lambda v: v * 34 // 255))
    d = ImageDraw.Draw(img, "RGBA")
    x = 170
    espacado(d, x, 250, "FIAP  ·  INTELIGÊNCIA ARTIFICIAL  ·  TURMA 2TIAOR  ·  FASE 4", F("SemiBold", 24), AMBAR)
    d.text((x - 6, 290), "CardioIA", font=F("Bold", 150, True), fill=BRANCO)
    d.text((x, 478), "Assistente Cardiológico Virtual", font=F("Medium", 54, True), fill=SUAVE)
    d.rectangle((x, 590, x + 120, 596), fill=AMBAR)
    d.text((x, 632), "Ir Além 2: integração com aplicativo mobile", font=F("SemiBold", 44), fill=BRANCO, features=["-calt"])
    d.text((x, 700), "App em React Native (Expo), backend Flask e CNN ResNet50", font=F("Regular", 34), fill=SUAVE)
    d.text((x, 812), "Silvio Prestes Guerreiro Junior  ·  RM 567958", font=F("Medium", 30), fill=SUAVE)
    pilula(img, d, x, 900, AVISO)
    return img


def cartao_arquitetura():
    img = fundo_ref.copy()
    d = ImageDraw.Draw(img, "RGBA")
    espacado(d, 150, 96, "COMO O APP FUNCIONA", F("SemiBold", 24), AMBAR)
    d.text((148, 132), "Do celular ao modelo e de volta", font=F("Bold", 62, True), fill=BRANCO)
    blocos = [("CELULAR", "App React Native", "Expo: envio da imagem e tela de resultado"),
              ("BACKEND", "API Flask", "Pré-processamento e chamada do modelo"),
              ("MODELO", "CNN ResNet50", "Transfer Learning, treinada na atividade")]
    bw, bh, by, gap = 480, 236, 330, 90
    xs = [150 + i * (bw + gap) for i in range(3)]
    for x, (tag, tit, desc) in zip(xs, blocos):
        caixa(img, x, by, x + bw, by + bh, 26, BRANCO, 22, borda=(BRANCO, 80, 2))
        d = ImageDraw.Draw(img, "RGBA")
        espacado(d, x + 34, by + 32, tag, F("SemiBold", 22), AMBAR)
        d.text((x + 32, by + 70), tit, font=F("Bold", 42, True), fill=BRANCO)
        for i, lin in enumerate(quebrar(desc, F("Regular", 27), bw - 68)):
            d.text((x + 34, by + 138 + i * 36), lin, font=F("Regular", 27), fill=SUAVE)
    ym = by + bh // 2
    for i, rot in enumerate(["POST /api/predict", "imagem 224 x 224"]):
        xa, xb = xs[i] + bw + 10, xs[i + 1] - 16
        seta(d, xa, ym, xb, ym, AMBAR)
    # rotulos das setas acima dos blocos (o vao entre eles e estreito)
    for i, rot in enumerate(["POST /api/predict", "imagem 224 x 224"]):
        d.text((xs[i] + bw + gap / 2, by - 18), rot, font=F("Medium", 24), fill=SUAVE, anchor="mb")
    # caminho de volta
    yv = by + bh + 70
    xc1, xc3 = xs[0] + bw // 2, xs[2] + bw // 2
    d.line((xc3, by + bh + 8, xc3, yv, xc1, yv), fill=(*SUAVE, 255), width=4, joint="curve")
    seta(d, xc1, yv, xc1, by + bh + 14, SUAVE)
    rot = "JSON: categoria detectada, probabilidade e explicação"
    f = F("Medium", 26)
    lw = int(f.getlength(rot)) + 44
    xm = (xc1 + xc3) // 2
    img.paste(fundo_ref.crop((xm - lw // 2, yv - 24, xm + lw // 2, yv + 24)), (xm - lw // 2, yv - 24))
    ImageDraw.Draw(img).text((xm, yv), rot, font=f, fill=SUAVE, anchor="mm")
    # legenda
    caixa(img, 150, 790, 1770, 950, 26, BRANCO, 20, borda=(BRANCO, 60, 2))
    ImageDraw.Draw(img).text((960, 870), LEGENDA_ARQUITETURA, font=F("Medium", 38), fill=BRANCO, anchor="mm")
    return img


def cartao_fim():
    img = fundo_ref.copy()
    d = ImageDraw.Draw(img, "RGBA")
    x = 170
    espacado(d, x, 150, "CARDIOIA FASE 4  ·  IR ALÉM 2", F("SemiBold", 24), AMBAR)
    d.text((x - 2, 188), "Resumo", font=F("Bold", 76, True), fill=BRANCO)
    itens = ["Interface em React Native, com envio de imagem e exibição do resultado",
             "Backend Flask servindo a CNN treinada na atividade (ResNet50)",
             "Três categorias na tela: Sem achado, Inconclusivo e Cardiomegalia",
             "Erros e limitações do modelo informados a quem usa o app"]
    for i, t in enumerate(itens):
        y = 350 + i * 86
        d.ellipse((x, y + 14, x + 18, y + 32), fill=AMBAR)
        d.text((x + 44, y), t, font=F("Medium", 38), fill=BRANCO)
    d.text((x, 730), "Código e instruções de execução na pasta mobile/ do repositório", font=F("Regular", 32), fill=SUAVE)
    d.text((x, 812), "Silvio Prestes Guerreiro Junior  ·  RM 567958  ·  FIAP, turma 2TIAOR", font=F("Medium", 28), fill=SUAVE)
    pilula(img, d, x, 900, AVISO)
    return img


# ---------------------------------------------------------------- cenas do app
def base_app():
    img = fundo_ref.copy()
    ow, oh, ro = PW + 2 * BEZ, PH + 2 * BEZ, R_IN + BEZ
    sombra = Image.new("L", (W, H), 0)
    sombra.paste(rr(ow, oh, ro), (PX - BEZ, PY - BEZ + 16))
    sombra = sombra.filter(ImageFilter.GaussianBlur(26)).point(lambda v: int(v * 0.6))
    img = Image.composite(Image.new("RGB", (W, H), (2, 5, 14)), img, sombra)
    img.paste(Image.new("RGB", (ow + 4, oh + 4), (70, 86, 122)), (PX - BEZ - 2, PY - BEZ - 2), rr(ow + 4, oh + 4, ro + 2))
    img.paste(Image.new("RGB", (ow, oh), (9, 12, 20)), (PX - BEZ, PY - BEZ), rr(ow, oh, ro))
    d = ImageDraw.Draw(img, "RGBA")
    espacado(d, X0, 74, "CARDIOIA FASE 4  ·  IR ALÉM 2", F("SemiBold", 24), AMBAR)
    d.text((X0 - 2, 108), "App mobile em React Native", font=F("Bold", 58, True), fill=BRANCO)
    d.line((X0, 204, X1, 204), fill=(255, 255, 255, 46), width=2)
    d.text((X0, 1016), AVISO, font=F("Regular", 22), fill=APAGADO)
    return img


def sobreposicao(base, passo, texto):
    """Quadro completo (fundo, moldura, roteiro e legenda) com a area da tela transparente."""
    img = base.copy()
    d = ImageDraw.Draw(img, "RGBA")
    for i, nome in enumerate(PASSOS, 1):
        y = 238 + (i - 1) * 68
        cx, cy = X0 + 23, y + 23
        if i == passo:
            d.ellipse((cx - 23, cy - 23, cx + 23, cy + 23), fill=AMBAR)
            d.text((cx, cy + 1), str(i), font=F("Bold", 26), fill=ESCURO, anchor="mm")
            d.text((X0 + 66, cy), nome, font=F("SemiBold", 34), fill=BRANCO, anchor="lm")
        elif i < passo:
            d.ellipse((cx - 23, cy - 23, cx + 23, cy + 23), fill=(255, 255, 255, 38))
            d.line((cx - 9, cy + 1, cx - 3, cy + 8, cx + 10, cy - 7), fill=SUAVE, width=4, joint="curve")
            d.text((X0 + 66, cy), nome, font=F("Regular", 32), fill=SUAVE, anchor="lm")
        else:
            d.ellipse((cx - 22, cy - 22, cx + 22, cy + 22), outline=APAGADO, width=2)
            d.text((cx, cy + 1), str(i), font=F("Medium", 24), fill=APAGADO, anchor="mm")
            d.text((X0 + 66, cy), nome, font=F("Regular", 32), fill=APAGADO, anchor="lm")
    cy0, cy1 = 690, 984
    caixa(img, X0, cy0, X1, cy1, 28, BRANCO, 22, borda=(BRANCO, 70, 2))
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle((X0 + 2, cy0 + 40, X0 + 8, cy1 - 40), radius=3, fill=AMBAR)
    f = F("Medium", 40)
    linhas = quebrar(texto, f, X1 - X0 - 96)
    alt = 56
    y = (cy0 + cy1) // 2 - (len(linhas) * alt) // 2 + alt // 2
    for i, lin in enumerate(linhas):
        d.text((X0 + 48, y + i * alt), lin, font=f, fill=BRANCO, anchor="lm")
    furo = Image.new("L", (W, H), 0)
    furo.paste(rr(PW, PH, R_IN), (PX, PY))
    img.putalpha(furo.point(lambda v: 255 - v))
    return img, len(linhas)


def eventos():
    d = json.loads((DADOS / "eventos.json").read_text())
    leg = [(e["t"], e["id"]) for e in d["eventos"] if e["tipo"] == "legenda"]
    fim = next(e["t"] for e in d["eventos"] if e["tipo"] == "fim")
    total = int(round(d["video"]["duracao"] * FPS))
    cortes = [min(int(round(t * FPS)), total) for t, _ in leg] + [min(int(round(fim * FPS)), total)]
    return [(leg[i][1], cortes[i], cortes[i + 1]) for i in range(len(leg))]


def quadro_tela(t, destino):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(DADOS / "tela.mp4"), "-frames:v", "1", str(destino)], check=True)
    return Image.open(destino).convert("RGB")


def previa():
    PREV.mkdir(parents=True, exist_ok=True)
    cartao_titulo().save(PREV / "c_titulo.png")
    cartao_arquitetura().save(PREV / "c_arquitetura.png")
    cartao_fim().save(PREV / "c_fim.png")
    base = base_app()
    ev = {i: (a, b) for i, a, b in eventos()}
    for ident in ("A1", "B2", "D3", "E1"):
        ov, n = sobreposicao(base, *LEGENDAS[ident])
        a, b = ev[ident]
        tela = quadro_tela((a + (b - a) * 0.7) / FPS, PREV / "tela.png").resize((PW, PH), Image.LANCZOS)
        comp = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        comp.paste(tela, (PX, PY))
        comp.alpha_composite(ov)
        comp.convert("RGB").save(PREV / f"p_{ident}.png")
    base = base_app()
    print("linhas por legenda:", {k: sobreposicao(base, *v)[1] for k, v in LEGENDAS.items()})
    print("duracao de cada legenda (s):", {i: round((b - a) / FPS, 2) for i, a, b in eventos()})


COD = ["-r", str(FPS), "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-g", "60",
       "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", "-video_track_timescale", "15360"]
YUV = "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p"


def ff(args, destino):
    tmp = destino.with_name(destino.stem + ".tmp.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args, *COD, str(tmp)], check=True)
    tmp.rename(destino)


def cena_fixa(png, dur, destino, fin=0.3, fout=0.3):
    vf = f"loop=loop=-1:size=1,trim=duration={dur},fade=t=in:st=0:d={fin},fade=t=out:st={dur - fout}:d={fout},{YUV}"
    ff(["-framerate", str(FPS), "-i", str(png), "-vf", vf], destino)


def render():
    for p in (SEG, SAIDA):
        p.mkdir(parents=True, exist_ok=True)
    arquivos = []
    cartao_titulo().save(SEG / "c_titulo.png")
    cena_fixa(SEG / "c_titulo.png", D_TITULO, SEG / "s00_titulo.mp4", fin=0.6)
    cartao_arquitetura().save(SEG / "c_arquitetura.png")
    cena_fixa(SEG / "c_arquitetura.png", D_ARQ, SEG / "s01_arquitetura.mp4")
    arquivos += [SEG / "s00_titulo.mp4", SEG / "s01_arquitetura.mp4"]
    base = base_app()
    ev = eventos()
    for k, (ident, a, b) in enumerate(ev):
        ov, _ = sobreposicao(base, *LEGENDAS[ident])
        png = SEG / f"ov_{ident}.png"
        ov.save(png)
        dur = (b - a) / FPS
        fade = ""
        if k == 0:
            fade = "fade=t=in:st=0:d=0.3,"
        if k == len(ev) - 1:
            fade = f"fade=t=out:st={dur - 0.4:.3f}:d=0.4,"
        fc = (f"[0:v]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS,"
              f"scale={PW}:{PH}:flags=lanczos:in_color_matrix=bt709:in_range=tv,format=gbrp,pad={W}:{H}:{PX}:{PY}:black[ph];"
              f"[1:v]format=gbrap[ov];[ph][ov]overlay=0:0:format=gbrp,{fade}{YUV}[v]")
        dest = SEG / f"s{k + 2:02d}_{ident}.mp4"
        ff(["-i", str(DADOS / "tela.mp4"), "-i", str(png), "-filter_complex", fc, "-map", "[v]"], dest)
        arquivos.append(dest)
        print(ident, f"{dur:.2f}s", flush=True)
    cartao_fim().save(SEG / "c_fim.png")
    cena_fixa(SEG / "c_fim.png", D_FIM, SEG / "s99_fim.mp4", fout=0.8)
    arquivos.append(SEG / "s99_fim.mp4")
    (SEG / "lista.txt").write_text("".join(f"file '{a}'\n" for a in arquivos))
    mudo = SEG / "sem_audio.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(SEG / "lista.txt"), "-c", "copy", str(mudo)], check=True)
    final = SAIDA / "cardioia_mobile_demo.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mudo), "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "64k", "-shortest", "-movflags", "+faststart", str(final)], check=True)
    # legendas em arquivo separado (.srt)
    def hms(t):
        ms = int(round(t * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    blocos = [(D_TITULO, D_TITULO + D_ARQ, LEGENDA_ARQUITETURA)]
    t0 = D_TITULO + D_ARQ
    blocos += [(t0 + a / FPS, t0 + b / FPS, LEGENDAS[i][1]) for i, a, b in ev]
    (SAIDA / "cardioia_mobile_demo.srt").write_text("".join(f"{n}\n{hms(a)} --> {hms(b)}\n{t}\n\n" for n, (a, b, t) in enumerate(blocos, 1)), encoding="utf-8")
    print("pronto:", final)


if __name__ == "__main__":
    {"previa": previa, "render": render}[sys.argv[1]]()
