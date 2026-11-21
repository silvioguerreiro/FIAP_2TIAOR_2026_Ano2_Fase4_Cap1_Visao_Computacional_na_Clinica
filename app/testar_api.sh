#!/bin/bash
# Teste rapido do prototipo com o servidor ja em execucao (python app.py)
# Uso: ./testar_api.sh [endereco]     padrao: http://127.0.0.1:5050
B=${1:-http://127.0.0.1:5050}
cd "$(dirname "$0")"
campos() { python3 -c 'import sys,json; d=json.load(sys.stdin); print(*[d.get(k) for k in sys.argv[1:]])' "$@"; }
codigo() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
echo "health: $(curl -s $B/api/health)"
for i in 1 2 3 4 5 6; do
  echo "exemplo_$i: $(curl -s -F imagem=@static/exemplos/exemplo_$i.jpg $B/api/predict | campos classe probabilidade percentual)"
done
echo "sem arquivo (espera 400): $(codigo -X POST $B/api/predict)"
echo "extensao nao aceita (espera 400): $(codigo -F imagem=@config.json $B/api/predict)"
printf 'nao sou imagem' > /tmp/cardioia_falso.png
echo "png corrompido (espera 400): $(codigo -F imagem=@/tmp/cardioia_falso.png $B/api/predict)"
head -c 3000 static/exemplos/exemplo_1.jpg > /tmp/cardioia_truncado.jpg
echo "jpg truncado (espera 400): $(codigo -F imagem=@/tmp/cardioia_truncado.jpg $B/api/predict)"
echo "pagina inicial (espera 200): $(codigo $B/)"
echo "exemplo pela pagina (espera 200): $(codigo $B/exemplo/exemplo_2.jpg)"
echo "exemplo inexistente (espera 404): $(codigo $B/api/exemplo/nao_existe.jpg)"
