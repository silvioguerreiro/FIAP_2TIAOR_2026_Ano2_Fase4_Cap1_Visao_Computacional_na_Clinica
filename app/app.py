"""CardioIA Fase 4: prototipo do Assistente Cardiologico Virtual (Flask).

Recebe uma radiografia de torax, aplica o mesmo pre-processamento do treino e mostra a classe
prevista, a probabilidade e uma explicacao em linguagem acessivel.
Prototipo academico, sem validade diagnostica.

Uso:  python app.py   (abre em http://127.0.0.1:5050)
"""
import io
import json
import os
from pathlib import Path

import numpy as np
from flask import Flask, jsonify, render_template, request, send_from_directory
from PIL import Image

AQUI = Path(__file__).resolve().parent
CFG = json.loads((AQUI / "config.json").read_text(encoding="utf-8"))
IMG_SIZE = 224
EXTENSOES = {".png", ".jpg", ".jpeg"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB por imagem

_modelo = None
CAMINHO_MODELO = (AQUI / CFG["modelo"]).resolve()


class ModeloAusente(RuntimeError):
    """O arquivo do modelo treinado nao esta na pasta models/ (ele nao vai para o repositorio)."""


class ImagemInvalida(ValueError):
    """O arquivo enviado nao pode ser lido como imagem."""


def modelo():
    """Carrega o modelo uma unica vez, no primeiro uso."""
    global _modelo
    if _modelo is None:
        if not CAMINHO_MODELO.exists():
            raise ModeloAusente(CAMINHO_MODELO.name)
        import tensorflow as tf
        _modelo = tf.keras.models.load_model(CAMINHO_MODELO)
    return _modelo


def abrir_cinza(arquivo_bytes):
    """Decodifica a imagem em escala de cinza de 8 bits.

    Imagens de 16 bits sao reescaladas para 0 a 255 pelo minimo e maximo, como no notebook 01.
    """
    try:
        im = Image.open(io.BytesIO(arquivo_bytes))
        im.load()
    except (OSError, ValueError, Image.DecompressionBombError) as e:
        raise ImagemInvalida() from e
    if im.mode.startswith("I") or im.mode == "F":
        import cv2
        return cv2.normalize(np.asarray(im), None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    return np.asarray(im.convert("L"))


def preparar(arquivo_bytes):
    """Mesmo pipeline do notebook 01: escala de cinza, 224 x 224 (INTER_AREA), JPEG qualidade 95,
    3 canais e normalizacao do modelo.

    A etapa JPEG faz parte do pipeline: o modelo foi treinado e avaliado somente com imagens que passaram
    por ela, e a probabilidade muda quando ela e omitida (ver src/experimento_jpeg.py).
    Imagens que ja chegam em 224 x 224 sao tratadas como ja processadas.
    """
    import cv2
    img = abrir_cinza(arquivo_bytes)
    if img.shape != (IMG_SIZE, IMG_SIZE):
        img = cv2.resize(img, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_AREA)
        _, jpg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        img = cv2.imdecode(jpg, cv2.IMREAD_GRAYSCALE)
    x = np.repeat(img.astype("float32")[..., None], 3, axis=-1)[None]
    if CFG["preprocessamento"] == "resnet50":
        from tensorflow.keras.applications.resnet50 import preprocess_input
        x = preprocess_input(x)
    else:
        x = x / 255.0
    return x


def percentual(prob):
    """Percentual inteiro mostrado na tela, coerente com a faixa de decisao.

    A faixa e decidida pela probabilidade exata. Sem este ajuste, 0,498 apareceria como 50% com resultado
    inconclusivo, e 0,409 como 41% com resultado sem achado, contrariando a legenda dos limites.
    """
    pct = round(prob * 100)
    for limite in (CFG["limiar_padrao"], CFG["limiar_sensivel"]):
        if prob < limite and pct >= round(limite * 100):
            pct = round(limite * 100) - 1
    return pct


def interpretar(prob):
    """Converte a probabilidade em faixa, rotulo e explicacao acessivel."""
    baixo, alto = CFG["limiar_sensivel"], CFG["limiar_padrao"]
    pct = percentual(prob)
    if prob >= alto:
        return {"faixa": "alta", "classe": "Cardiomegalia",
                "titulo": "Sinais sugestivos de coração aumentado",
                "explicacao": f"O modelo estimou {pct}% de probabilidade de cardiomegalia, que é o aumento do tamanho do "
                              "coração na radiografia. Imagens com este padrão devem ser encaminhadas com prioridade para "
                              "avaliação de um médico."}
    if prob >= baixo:
        return {"faixa": "intermediaria", "classe": "Inconclusivo",
                "titulo": "Resultado inconclusivo, revisão recomendada",
                "explicacao": f"O modelo estimou {pct}% de probabilidade de cardiomegalia. O valor está em uma zona de "
                              "incerteza: não é alto o bastante para indicar o achado, nem baixo o bastante para afastá-lo. "
                              "Nesta faixa o modelo erra com mais frequência, por isso a revisão por um médico é recomendada."}
    return {"faixa": "baixa", "classe": "Sem achado",
            "titulo": "Sem sinais sugestivos de coração aumentado",
            "explicacao": f"O modelo estimou {pct}% de probabilidade de cardiomegalia. Ele não identificou o padrão de "
                          "coração aumentado nesta imagem. Isso não afasta outras alterações, que este modelo não avalia."}


def prever(arquivo_bytes):
    rede = modelo()                      # primeiro o modelo: se faltar, o erro informado e o do modelo
    prob = float(rede.predict(preparar(arquivo_bytes), verbose=0)[0, 0])
    r = interpretar(prob)
    r.update({"probabilidade": round(prob, 4), "percentual": percentual(prob), "modelo": CFG["nome_modelo"],
              "aviso": "Protótipo acadêmico, sem validade diagnóstica. Não substitui a avaliação de um médico."})
    return r


def ler_upload():
    f = request.files.get("imagem")
    if f is None or f.filename == "":
        return None, "Nenhuma imagem foi enviada."
    if Path(f.filename).suffix.lower() not in EXTENSOES:
        return None, "Formato não aceito. Envie uma imagem PNG ou JPG."
    return f.read(), None


@app.after_request
def cors(resp):
    # permite que o app mobile (Ir Alem 2) consuma a API em desenvolvimento
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


@app.get("/")
def inicio():
    return render_template("index.html", cfg=CFG, exemplos=_exemplos(), resultado=None, erro=None)


def _pagina_resultado(dados, nome, exemplos):
    import base64
    r = prever(dados)
    img = Image.fromarray(abrir_cinza(dados))
    img.thumbnail((420, 420))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    r["miniatura"] = base64.b64encode(buf.getvalue()).decode()
    r["arquivo"] = nome
    return render_template("index.html", cfg=CFG, exemplos=exemplos, resultado=r, erro=None)


def _exemplos():
    return sorted(p.name for p in (AQUI / "static" / "exemplos").glob("*.jpg"))


@app.post("/prever")
def prever_html():
    exemplos = _exemplos()
    dados, erro = ler_upload()
    if erro:
        return render_template("index.html", cfg=CFG, exemplos=exemplos, resultado=None, erro=erro), 400
    try:
        return _pagina_resultado(dados, request.files["imagem"].filename, exemplos)
    except ImagemInvalida:
        return render_template("index.html", cfg=CFG, exemplos=exemplos, resultado=None,
                               erro="O arquivo enviado não é uma imagem válida."), 400


@app.get("/exemplo/<nome>")
def exemplo(nome):
    exemplos = _exemplos()
    if nome not in exemplos:
        return render_template("index.html", cfg=CFG, exemplos=exemplos, resultado=None, erro="Exemplo não encontrado."), 404
    return _pagina_resultado((AQUI / "static" / "exemplos" / nome).read_bytes(), nome, exemplos)


@app.route("/api/predict", methods=["POST", "OPTIONS"])
def prever_api():
    if request.method == "OPTIONS":
        return "", 204
    dados, erro = ler_upload()
    if erro:
        return jsonify({"erro": erro}), 400
    try:
        return jsonify(prever(dados))
    except ImagemInvalida:
        return jsonify({"erro": "O arquivo enviado não é uma imagem válida."}), 400


@app.get("/api/info")
def info():
    """Dados que o app mobile precisa para montar a tela: limites, metricas e imagens de exemplo."""
    return jsonify({"modelo": CFG["nome_modelo"], "limiar_padrao": CFG["limiar_padrao"], "limiar_sensivel": CFG["limiar_sensivel"],
                    "metricas": CFG["metricas"], "exemplos": _exemplos(),
                    "aviso": "Protótipo acadêmico, sem validade diagnóstica. Não substitui a avaliação de um médico."})


@app.get("/api/exemplo/<nome>")
def exemplo_api(nome):
    if nome not in _exemplos():
        return jsonify({"erro": "Exemplo não encontrado."}), 404
    return jsonify(prever((AQUI / "static" / "exemplos" / nome).read_bytes()))


# Versao web do app React Native (gerada com "npx expo export --platform web" e copiada para app/mobile_web).
# Opcional: serve para demonstrar o app no navegador, na mesma origem da API.
DIR_MOBILE = AQUI / "mobile_web"


@app.get("/mobile/")
@app.get("/mobile/<path:caminho>")
def mobile_web(caminho="index.html"):
    if not DIR_MOBILE.exists():
        return jsonify({"erro": "Versão web do app mobile não foi gerada."}), 404
    alvo = caminho if (DIR_MOBILE / caminho).is_file() else "index.html"
    return send_from_directory(DIR_MOBILE, alvo)


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "modelo": CFG["nome_modelo"], "modelo_disponivel": CAMINHO_MODELO.exists()})


@app.errorhandler(ModeloAusente)
def sem_modelo(e):
    msg = (f"Modelo treinado não encontrado. Baixe o arquivo {e.args[0]} pelo link indicado no README e salve na pasta models/, "
           "ou execute os notebooks de treino.")
    if request.path.startswith("/api/"):
        return jsonify({"erro": msg}), 503
    return render_template("index.html", cfg=CFG, exemplos=_exemplos(), resultado=None, erro=msg), 503


@app.errorhandler(413)
def grande(_):
    return jsonify({"erro": "Imagem maior que 10 MB."}), 413


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5050)), debug=False)
