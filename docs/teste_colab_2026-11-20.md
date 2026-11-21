# Teste de execução no Google Colab (20/11/2026)

> Protótipo acadêmico, sem validade diagnóstica.

## Como o teste foi feito

Um notebook de teste recriou em `/content/cardioia-fase4`, numa máquina do Google Colab, os arquivos deste repositório (os cinco notebooks sem as saídas, `src/`, `app/config.json`, `requirements.txt` e os arquivos CSV e JSON de `data/`, sem imagens e sem modelos). Em seguida executou os cinco notebooks em ordem, cada um com `jupyter nbconvert --to notebook --execute` dentro de `notebooks/`, usando o kernel padrão do Colab. Nenhum pacote foi instalado. As saídas abaixo foram copiadas desse notebook de teste, que ficou guardado, com as saídas, no Google Drive do autor.

Os modelos foram treinados de novo, com o mesmo código e a mesma semente da execução local, em outro hardware. Por isso os resultados dos notebooks 02, 03, 03b e 04 são próximos, mas não iguais, aos da execução local.

## Ambiente

```
inicio_utc: 2026-11-20 21:20:51
colab: release-colab-external-images_20261118-060058_RC00
python: 3.13.16
bibliotecas: numpy 2.4.6 | pandas 2.2.3 | scikit-learn 1.6.1 | scipy 1.16.3 | opencv 4.14.0 | matplotlib 3.10.0 | pillow 11.3.0
tensorflow: tensorflow 2.21.0 | keras 3.13.2
gpu: Tesla T4, 15360 MiB
maquina: 2 núcleos de CPU, 13.3 GB de RAM, 121 GB livres em disco
Kernel usado nas execuções: padrão do ambiente | google.colab carregado e executável: True /usr/bin/python3
```

## Tempos

| Notebook | Resultado | Minutos | Tentativas |
|---|---|---|---|
| 01_preprocessamento | concluído | 8,8 (falhou) e 1,5 | 2 |
| 02_cnn_do_zero | concluído | 38,0 | 1 |
| 03_transfer_learning | concluído | 20,9 | 1 |
| 03b_comparacao_estatistica | concluído | 0,8 | 1 |
| 04_fairness | concluído | 1,5 | 1 |

Duração total do teste: 71,6 minutos.

## Notebook 01

Na primeira tentativa o servidor do Hugging Face recusou 36 das 5.552 imagens com o erro 429 (limite de requisições), e o notebook parou na verificação do download. A segunda tentativa retomou de onde parou.

```
[01_preprocessamento] início 21:21:08 UTC, tentativa 1
[01_preprocessamento]   1 min | originais 401 | processadas 0 | modelos -
[01_preprocessamento]   2 min | originais 1188 | processadas 0 | modelos -
[01_preprocessamento]   3 min | originais 1980 | processadas 0 | modelos -
[01_preprocessamento]   4 min | originais 2756 | processadas 0 | modelos -
[01_preprocessamento]   5 min | originais 3514 | processadas 0 | modelos -
[01_preprocessamento]   6 min | originais 4272 | processadas 0 | modelos -
[01_preprocessamento]   7 min | originais 4701 | processadas 0 | modelos -
[01_preprocessamento]   8 min | originais 4963 | processadas 0 | modelos -
[01_preprocessamento] FALHOU em 8.8 min | originais 5516 | processadas 0 | modelos -
5552/5552 processadas | novas 5516 | em cache 0 | erros 36
Erros: [('00027543_001.png', 'erro: 429 Client Error: Too Many Requests for url: https://huggingface.co/datasets/alkzar90/NIH-Chest-X-ray-dataset/resolve/main/data/images/images_011.zip'), ...]
AssertionError: há imagens com erro de download, execute a célula de novo
[01_preprocessamento] início 21:29:54 UTC, tentativa 2
[01_preprocessamento]   1 min | originais 5552 | processadas 3794 | modelos -
[01_preprocessamento] concluído em 1.5 min | originais 5552 | processadas 5552 | modelos -
```

Conferência com a execução local:

```
Manifesto (seleção das imagens e divisão em treino, validação e teste) idêntico ao da execução local: True
Imagens processadas aqui: 5552 arquivos, 71.45 MB, resumo c271e772ba7e74be
Imagens processadas na execução local: 5552 arquivos, 71.45 MB, resumo c271e772ba7e74be
Amostra de 6 imagens (arquivo, diferença máxima de pixel, diferença média, arquivo idêntico): [('00000008_000.jpg', 0, 0.0, True), ('00000255_002.jpg', 0, 0.0, True), ('00000001_000.jpg', 0, 0.0, True), ('00000016_000.jpg', 0, 0.0, True), ('00000033_000.jpg', 0, 0.0, True), ('00000041_003.jpg', 0, 0.0, True)]
Resumo do pré-processamento aqui: {'total_imagens': 5552, 'total_pacientes': 4342, 'por_split': {'train': {'sem_achado': 1943, 'cardiomegalia': 1985}, 'val': {'sem_achado': 416, 'cardiomegalia': 389}, 'test': {'sem_achado': 417, 'cardiomegalia': 402}}, 'media_treino': 0.4977, 'desvio_treino': 0.2498}
Resumo do pré-processamento local: {'total_imagens': 5552, 'total_pacientes': 4342, 'por_split': {'train': {'sem_achado': 1943, 'cardiomegalia': 1985}, 'val': {'sem_achado': 416, 'cardiomegalia': 389}, 'test': {'sem_achado': 417, 'cardiomegalia': 402}}, 'media_treino': 0.4977, 'desvio_treino': 0.2498}
```

O resumo é um SHA-256 calculado sobre o caminho e o conteúdo de todos os arquivos JPEG processados, em ordem.

## Notebooks 02 e 03

```
[02_cnn_do_zero] concluído em 38.0 min | originais 5552 | processadas 5552 | modelos cnn_do_zero.keras 22:04:33
CNN do zero, execução local:    {'acuracia': 0.7985, 'precisao': 0.7869, 'recall': 0.8085, 'f1': 0.7975, 'auc': 0.8742, 'fn': 77, 'fp': 88, 'epocas': 40, 'treino_min': 33.1, 'tensorflow': '2.21.0'}
CNN do zero, execução no Colab: {'acuracia': 0.8046, 'precisao': 0.7881, 'recall': 0.8234, 'f1': 0.8054, 'auc': 0.8769, 'fn': 71, 'fp': 89, 'epocas': 40, 'treino_min': 37.5, 'tensorflow': '2.21.0'}
[03_transfer_learning] concluído em 20.9 min | originais 5552 | processadas 5552 | modelos cnn_do_zero.keras 22:04:33, resnet50_etapa1.keras 22:14:28, resnet50_etapa2.keras 22:25:26, resnet50_final.keras 22:29:44
ResNet50, execução local:    {'acuracia': 0.8071, 'precisao': 0.7699, 'recall': 0.8657, 'f1': 0.815, 'auc': 0.8816, 'fn': 54, 'fp': 104, 'epocas': [8, 9], 'treino_min': 31.6, 'tensorflow': '2.21.0'}
ResNet50, execução no Colab: {'acuracia': 0.8071, 'precisao': 0.7877, 'recall': 0.8308, 'f1': 0.8087, 'auc': 0.879, 'fn': 68, 'fp': 90, 'epocas': [8, 11], 'treino_min': 19.9, 'tensorflow': '2.21.0'}
```

Métricas no conjunto de teste, com limiar 0,5.

## Notebook 03b, com os modelos treinados no Colab

`comparacao_bootstrap.csv`:

```
metrica,CNN do zero,ResNet50,diferenca (ResNet50 - CNN),IC exclui zero
acuracia,"0.805 [0.773, 0.835]","0.807 [0.777, 0.837]","+0.002 [-0.025, +0.031]",não
precisao,"0.788 [0.735, 0.833]","0.788 [0.735, 0.831]","-0.000 [-0.031, +0.032]",não
recall,"0.823 [0.775, 0.865]","0.831 [0.785, 0.873]","+0.007 [-0.033, +0.048]",não
f1,"0.805 [0.762, 0.841]","0.809 [0.767, 0.844]","+0.003 [-0.025, +0.034]",não
auc,"0.877 [0.847, 0.902]","0.879 [0.851, 0.905]","+0.002 [-0.018, +0.023]",não
```

## Notebook 04, com os modelos treinados no Colab

`fairness_resumo.csv`:

```
atributo,igualdade de oportunidade (dif. recall),dif. FPR,odds equalizadas,paridade demografica (dif. selecao)
sexo,0.005,0.013,0.013,0.072
faixa,0.393,0.079,0.393,0.212
visao,0.015,0.055,0.055,0.053
```

`fairness_permutacao.csv`:

```
atributo,dif. recall,p estratificado (recall),p simples (recall),dif. FPR,p estratificado (FPR),p simples (FPR)
sexo,0.005376344086021501,0.916210837891621,0.9092009079909201,0.013218989860703106,0.8123418765812341,0.7457125428745712
faixa,0.3932038834951457,0.002899971000289997,0.006449935500644994,0.07905138339920947,0.6574134258657414,0.6947630523694763
visao,0.01473214285714286,0.8631113688863111,0.7493225067749323,0.054684956986747274,0.1909180908190918,0.18325816741832582
```

`fairness_mitigacao.csv`:

```
cenario,recall AP,recall PA,FPR AP,FPR PA,dif. recall,dif. FPR,acuracia,recall,fpr,fn,fp
"limiar único 0,5",0.839,0.824,0.246,0.191,0.015,0.055,0.807,0.831,0.216,68,90
limiar por grupo,0.823,0.829,0.225,0.191,0.006,0.033,0.81,0.826,0.206,70,86
```

`fairness_faixa_replicacao.csv`:

```
conjunto,modelo,faixa,n,positivas,recall,FPR,AUC
validação,ResNet50,0-17,30,10,0.8,0.25,0.895
validação,ResNet50,18-39,219,101,0.842,0.169,0.926
validação,ResNet50,40-59,331,152,0.816,0.19,0.893
validação,ResNet50,60+,225,126,0.794,0.313,0.838
validação,CNN do zero,0-17,30,10,0.8,0.3,0.81
validação,CNN do zero,18-39,219,101,0.792,0.169,0.897
validação,CNN do zero,40-59,331,152,0.789,0.212,0.88
validação,CNN do zero,60+,225,126,0.825,0.343,0.813
validação,média dos dois,0-17,30,10,0.9,0.15,0.925
validação,média dos dois,18-39,219,101,0.851,0.153,0.929
validação,média dos dois,40-59,331,152,0.855,0.179,0.908
validação,média dos dois,60+,225,126,0.817,0.323,0.838
teste,ResNet50,0-17,41,18,0.5,0.261,0.664
teste,ResNet50,18-39,237,127,0.85,0.182,0.888
teste,ResNet50,40-59,342,154,0.812,0.218,0.892
teste,ResNet50,60+,199,103,0.893,0.24,0.872
teste,CNN do zero,0-17,41,18,0.889,0.261,0.872
teste,CNN do zero,18-39,237,127,0.819,0.145,0.912
teste,CNN do zero,40-59,342,154,0.805,0.218,0.862
teste,CNN do zero,60+,199,103,0.845,0.271,0.871
teste,média dos dois,0-17,41,18,0.778,0.261,0.821
teste,média dos dois,18-39,237,127,0.85,0.136,0.915
teste,média dos dois,40-59,342,154,0.805,0.181,0.89
teste,média dos dois,60+,199,103,0.883,0.229,0.887
```

## Resumo gravado pelo notebook de teste

```
{"inicio_utc": "2026-11-20 21:20:51", "colab": "release-colab-external-images_20261118-060058_RC00", "python": "3.13.16", "bibliotecas": "numpy 2.4.6 | pandas 2.2.3 | scikit-learn 1.6.1 | scipy 1.16.3 | opencv 4.14.0 | matplotlib 3.10.0 | pillow 11.3.0", "tensorflow": "tensorflow 2.21.0 | keras 3.13.2", "gpu": "Tesla T4, 15360 MiB", "maquina": "2 núcleos de CPU, 13.3 GB de RAM, 121 GB livres em disco", "kernel": "padrão do ambiente | google.colab carregado e executável: True /usr/bin/python3", "notebooks": {"01_preprocessamento": {"ok": true, "minutos": 1.5, "tentativas": 2}, "02_cnn_do_zero": {"ok": true, "minutos": 38.0, "tentativas": 1}, "03_transfer_learning": {"ok": true, "minutos": 20.9, "tentativas": 1}, "03b_comparacao_estatistica": {"ok": true, "minutos": 0.8, "tentativas": 1}, "04_fairness": {"ok": true, "minutos": 1.5, "tentativas": 1}}, "manifesto_identico": true, "imagens_processadas": {"arquivos": 5552, "bytes": 71454717, "resumo": "c271e772ba7e74be", "identicas_as_locais": true}, "amostra_pixels": [["00000008_000.jpg", 0, 0.0, true], ["00000255_002.jpg", 0, 0.0, true], ["00000001_000.jpg", 0, 0.0, true], ["00000016_000.jpg", 0, 0.0, true], ["00000033_000.jpg", 0, 0.0, true], ["00000041_003.jpg", 0, 0.0, true]], "cnn_do_zero": {"local": {"acuracia": 0.7985, "precisao": 0.7869, "recall": 0.8085, "f1": 0.7975, "auc": 0.8742, "fn": 77, "fp": 88, "epocas": 40, "treino_min": 33.1, "tensorflow": "2.21.0"}, "colab": {"acuracia": 0.8046, "precisao": 0.7881, "recall": 0.8234, "f1": 0.8054, "auc": 0.8769, "fn": 71, "fp": 89, "epocas": 40, "treino_min": 37.5, "tensorflow": "2.21.0"}}, "resnet50": {"local": {"acuracia": 0.8071, "precisao": 0.7699, "recall": 0.8657, "f1": 0.815, "auc": 0.8816, "fn": 54, "fp": 104, "epocas": [8, 9], "treino_min": 31.6, "tensorflow": "2.21.0"}, "colab": {"acuracia": 0.8071, "precisao": 0.7877, "recall": 0.8308, "f1": 0.8087, "auc": 0.879, "fn": 68, "fp": 90, "epocas": [8, 11], "treino_min": 19.9, "tensorflow": "2.21.0"}}, "arquivos_iguais_aos_locais": {"comparacao_bootstrap.csv": false, "fairness_resumo.csv": false, "fairness_permutacao.csv": false, "fairness_mitigacao.csv": false, "fairness_faixa_replicacao.csv": false}, "duracao_total_min": 71.6, "notebooks_executados": ["01_preprocessamento.ipynb", "02_cnn_do_zero.ipynb", "03_transfer_learning.ipynb", "03b_comparacao_estatistica.ipynb", "04_fairness.ipynb"]}
```

## Teste a partir do GitHub (20/11/2026, depois da publicação)

Um notebook de teste clonou o repositório público no Google Colab e executou os notebooks 01, 03b e 04 com `jupyter nbconvert --execute`. Os notebooks 02 e 03, de treino, não foram repetidos. Saída do teste:

```
{'inicio_utc': '2026-11-21 01:08:17', 'commit': '3f80b37 2026-11-20 21:06:13 -0400', 'arquivos': 85, 'python': '3.13.18', 'gpu': 'nenhuma'}
01_preprocessamento {'codigo': 0, 'minutos': 8.4}
03b_comparacao_estatistica {'codigo': 0, 'minutos': 0.8}
04_fairness {'codigo': 0, 'minutos': 1.7}
download: 5552/5552 processadas | novas 5552 | em cache 0 | erros 0
imagens_processadas: [5552, 71454717, "c271e772ba7e74be"]   imagens_iguais_a_referencia: true
manifesto_identico: true   csv_de_dados_identicos: true   minutos_total: 10.9
arquivos alterados: prints/01 a prints/05 e prints/15 (figuras regravadas pelos notebooks)
```

O servidor não recusou nenhuma imagem nesse teste, portanto as rodadas extras de `src/nih_remoto.py` não chegaram a ser acionadas.
