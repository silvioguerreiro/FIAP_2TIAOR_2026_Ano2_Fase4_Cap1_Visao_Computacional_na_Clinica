"""Experimento de robustez: o que acontece se a etapa de compressao JPEG do pre-processamento for omitida?

No notebook 01 cada imagem e reduzida para 224 x 224 e gravada em JPEG (qualidade 95). Os modelos foram
treinados e avaliados somente com essas imagens. Este script recalcula as probabilidades do conjunto de
teste a partir das imagens originais, com e sem a etapa JPEG (mesmo redimensionamento nos dois casos),
e compara os resultados. Serve para verificar se o prototipo precisa repetir a etapa JPEG ao receber
uma imagem original.

Uso: CARDIOIA_RAW=~/cardioia-data/raw python src/experimento_jpeg.py
Saidas: data/experimento_jpeg.csv (por imagem) e data/experimento_jpeg_resumo.json
"""
import json
import os
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import roc_auc_score
from tensorflow.keras.applications.resnet50 import preprocess_input

RAIZ = Path(__file__).resolve().parents[1]
RAW = Path(os.environ.get("CARDIOIA_RAW", RAIZ / "data" / "raw" / "imagens_originais")).expanduser()
man = pd.read_csv(RAIZ / "data" / "manifesto.csv")
man = man[man.split == "test"].reset_index(drop=True)
y = (man.classe == "cardiomegalia").astype(int).values


def reduzir(nome):
    """Mesmas operacoes do notebook 01 ate o redimensionamento."""
    img = cv2.imread(str(RAW / nome), cv2.IMREAD_UNCHANGED)
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY if img.shape[2] == 4 else cv2.COLOR_BGR2GRAY)
    if img.dtype != np.uint8:
        img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    return cv2.resize(img, (224, 224), interpolation=cv2.INTER_AREA)


sem = np.stack([reduzir(n) for n in man.imagem])                                   # sem JPEG
com = np.stack([cv2.imdecode(cv2.imencode(".jpg", a, [cv2.IMWRITE_JPEG_QUALITY, 95])[1], cv2.IMREAD_GRAYSCALE) for a in sem])
print("Imagens:", len(man), "| diferenca media de pixel entre as versoes:", round(float(np.abs(sem.astype(int) - com.astype(int)).mean()), 3),
      "| maxima:", int(np.abs(sem.astype(int) - com.astype(int)).max()))


def prever(modelo, prep, arr):
    saida = []
    for i in range(0, len(arr), 64):
        x = np.repeat(arr[i:i + 64].astype("float32")[..., None], 3, axis=-1)
        saida.append(modelo.predict(prep(x), verbose=0).ravel())
    return np.concatenate(saida)


def metr(p):
    yp = (p >= 0.5).astype(int)
    return {"acuracia": float((yp == y).mean()), "recall": float(yp[y == 1].mean()), "especificidade": float(1 - yp[y == 0].mean()),
            "auc": float(roc_auc_score(y, p))}


def faixa(p, lim_sens):
    return np.where(p >= 0.5, 2, np.where(p >= lim_sens, 1, 0))


cfg = json.loads((RAIZ / "app" / "config.json").read_text(encoding="utf-8"))
tabela = man[["arquivo", "imagem", "classe"]].copy()
resumo = {}
for nome, arquivo, prep in [("resnet50", "resnet50_final.keras", preprocess_input), ("cnn_do_zero", "cnn_do_zero.keras", lambda x: x / 255.0)]:
    modelo = tf.keras.models.load_model(RAIZ / "models" / arquivo)
    pc, ps = prever(modelo, prep, com), prever(modelo, prep, sem)
    salvo = pd.read_csv(RAIZ / "data" / f"pred_teste_{nome}.csv").set_index("arquivo").prob.reindex(man.arquivo).values
    tabela[f"{nome}_com_jpeg"], tabela[f"{nome}_sem_jpeg"] = pc, ps
    d = np.abs(ps - pc)
    resumo[nome] = {
        "com_jpeg_reproduz_notebook_dif_max": float(np.abs(pc - salvo).max()),
        "dif_abs_media": float(d.mean()), "dif_abs_mediana": float(np.median(d)), "dif_abs_p95": float(np.percentile(d, 95)), "dif_abs_max": float(d.max()),
        "dif_media_com_sinal_sem_menos_com": float((ps - pc).mean()),
        "imagens_que_trocam_de_lado_no_limiar_0.5": int(((pc >= 0.5) != (ps >= 0.5)).sum()),
        "metricas_com_jpeg": metr(pc), "metricas_sem_jpeg": metr(ps),
    }
    if nome == "resnet50":
        resumo[nome]["imagens_que_trocam_de_faixa_no_prototipo"] = int((faixa(pc, cfg["limiar_sensivel"]) != faixa(ps, cfg["limiar_sensivel"])).sum())
tabela.to_csv(RAIZ / "data" / "experimento_jpeg.csv", index=False)
(RAIZ / "data" / "experimento_jpeg_resumo.json").write_text(json.dumps(resumo, indent=2))
print(json.dumps(resumo, indent=2))
