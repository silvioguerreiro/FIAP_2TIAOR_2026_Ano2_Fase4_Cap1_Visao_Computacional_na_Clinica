# Roteiro do vídeo do Ir Além 2

Vídeo: `video/cardioia_mobile_demo.mp4`, 2 minutos, com legendas na imagem e sem narração. A tabela reproduz as legendas e os tempos do vídeo entregue (também em `video/cardioia_mobile_demo.srt`).

| Tempo | Cena | Legenda |
|---|---|---|
| 0:00 a 0:05 | Abertura | Cartão com título, autor e aviso de protótipo acadêmico |
| 0:05 a 0:15 | Arquitetura | O app envia a radiografia e recebe do backend a categoria detectada pela CNN. |
| 0:15 a 0:21 | 1. Abertura do app | Este é o CardioIA, app feito em React Native com Expo. A gravação usa a versão web, em tela de celular. |
| 0:21 a 0:26 | 1. Abertura do app | Ao abrir, o app consulta o backend Flask e carrega as radiografias de exemplo, que vêm do conjunto de teste. |
| 0:26 a 0:32 | 2. Exemplo com cardiomegalia | Ao tocar no Exemplo 3, a imagem é analisada no backend pela CNN treinada na atividade (ResNet50 com Transfer Learning). |
| 0:32 a 0:38 | 2. Exemplo com cardiomegalia | Categoria detectada: Cardiomegalia, com 88% de probabilidade. O cartão fica vermelho quando o achado é sugestivo. |
| 0:38 a 0:44 | 2. Exemplo com cardiomegalia | A barra mostra os limites de decisão, e o texto explica o resultado em linguagem simples. |
| 0:44 a 0:49 | 3. Exemplo sem achado | Segundo teste, com o Exemplo 2. |
| 0:49 a 0:56 | 3. Exemplo sem achado | Probabilidade de 34%, abaixo do limite de 41%. Categoria detectada: Sem achado, em verde. |
| 0:56 a 1:03 | 4. Envio de imagem do dispositivo | Terceiro teste: o botão Escolher imagem envia um arquivo do dispositivo pela rota POST /api/predict. |
| 1:03 a 1:09 | 4. Envio de imagem do dispositivo | Resultado de 47%. Entre 41% e 50% o app mostra Inconclusivo, em laranja, e recomenda revisão. |
| 1:09 a 1:16 | 4. Envio de imagem do dispositivo | Pelo rótulo do dataset, esta imagem é um caso de cardiomegalia. A faixa inconclusiva evita que ele seja descartado. |
| 1:16 a 1:22 | 5. Erros do modelo e limitações | O modelo também erra. O Exemplo 1 é rotulado como Sem achado no dataset. |
| 1:22 a 1:29 | 5. Erros do modelo e limitações | O app indicou Cardiomegalia, com 97%: um falso positivo, mantido na demonstração para mostrar esse limite. |
| 1:29 a 1:36 | 5. Erros do modelo e limitações | No conjunto de teste, de cada 100 casos reais o modelo identificou 87, e de cada 100 alertas 77 estavam corretos. |
| 1:36 a 1:43 | 5. Erros do modelo e limitações | O app avalia apenas cardiomegalia e não está validado para menores de 18 anos. O resultado não substitui o médico. |
| 1:43 a 1:52 | 6. Conexão com o backend | Por fim, a integração: o endereço do backend Flask é configurável, e o app confirma a conexão e o modelo em uso. |
| 1:52 a 2:00 | Fechamento | Cartão de resumo: interface em React Native, backend Flask com a CNN, três categorias e limitações informadas |

## Imagens usadas

| Cena | Imagem | Rótulo no dataset | Resultado no app |
|---|---|---|---|
| Exemplo 3 | 00000128_000.png | Cardiomegalia | Cardiomegalia, 88% |
| Exemplo 2 | 00027500_004.png | Sem achado | Sem achado, 34% |
| Envio pelo botão Escolher imagem | 00004630_002.png (original, 1024 x 1024) | Cardiomegalia | Inconclusivo, 47% |
| Exemplo 1 | 00009019_000.png | Sem achado | Cardiomegalia, 97% (falso positivo) |

Todas são do conjunto de teste. A imagem enviada pelo botão foi escolhida entre as que ficam na faixa inconclusiva, para que o vídeo mostrasse as três categorias.
