#!/usr/bin/env bash
# Rodada completa do mapa geral v2 em qualidade máxima (docs/mapa-geral-plano-2.md §11, 2026-10-16): geometria em 4K
# (quadros 3840×1920 reduzidos do vídeo 8K), quadro mediano por mapa e OCR das etiquetas no 8K, numa cache SEPARADA
# (.cache-4k). A cache de hoje (.cache) não é tocada; aprovar = trocar as pastas (ver docs/mapa-geral.md).
# Uso (na raiz do repositório):  scripts/mapa-geral/cadeia-4k.sh [etapa-inicial] [etapa-final]
#   etapas: e2 e3 amostras e4-rapida e4-media e4-todos e5 e6 e7a e7 e8 testes   (padrão: da e2 até testes; cada etapa é
#   incremental, então repetir é barato; "e3 e4-rapida" roda só esse trecho, para conferir antes das horas da E4).
#   Logs em .cache-4k/v2/painel/. Rode num serviço à parte do terminal, com teto de memória (a E2.4 gasta ~3,5 GB por
#   processo; em 2026-10-16, dentro do terminal, o systemd-oomd matou o terminal inteiro e a sessão junto):
#   systemd-run --user --unit=cadeia-4k -p MemoryMax=11G -p WorkingDirectory=$PWD --setenv=HOME=$HOME --setenv=PATH=$PATH \
#     scripts/mapa-geral/cadeia-4k.sh [etapa-inicial] [etapa-final]
#   (journalctl --user -u cadeia-4k para o estado; systemctl --user stop cadeia-4k para parar). Acompanhe no painel:
#   MAPA_GERAL_CACHE=$PWD/scripts/mapa-geral/.cache-4k MAPA_GERAL_ESCALA=2 MAPA_GERAL_ESCALA_OCR=4 python3 scripts/mapa-geral/painel.py 8003
set -u
cd "$(dirname "$0")/../.."
export MAPA_GERAL_CACHE="$PWD/scripts/mapa-geral/.cache-4k"
export MAPA_GERAL_ESCALA=2
export MAPA_GERAL_ESCALA_OCR=4
export PYTHONPATH="$HOME/.cache/mapa-biblia-lib/lib${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONUNBUFFERED=1
LOGS="$MAPA_GERAL_CACHE/v2/painel"
mkdir -p "$LOGS"
S=scripts/mapa-geral
inicio="${1:-e2}"
fim="${2:-testes}"
ETAPAS=(e2 e3 amostras e4-rapida e4-media e4-todos e5 e6 e7a e7 e8 testes)
ativo=0

rodar() {  # rodar <nome-do-log> <comando...>: para a cadeia no primeiro erro
  local nome="$1"; shift
  echo "== $(date '+%H:%M:%S') $nome: $*" | tee -a "$LOGS/cadeia.log"
  if ! "$@" > "$LOGS/$nome.log" 2>&1; then
    echo "!! $nome falhou (código $?): veja $LOGS/$nome.log" | tee -a "$LOGS/cadeia.log"
    exit 1
  fi
  tail -2 "$LOGS/$nome.log" | tee -a "$LOGS/cadeia.log"
}

for etapa in "${ETAPAS[@]}"; do
  [ "$etapa" = "$inicio" ] && ativo=1
  [ $ativo = 1 ] || continue
  case $etapa in
    e2)   rodar e2 python3 $S/quadros.py tudo ;;                      # varredura (1920), OCR do ano, montagem, medianas 8K/4K/1920
    e3)   rodar e3 python3 $S/calibrar.py
          rodar e3-transicoes python3 $S/transicoes.py ;;
    amostras) rodar amostras python3 $S/amostras.py ;;
    e4-rapida) rodar e4-rapida python3 $S/rotular.py --amostra rapida ;;
    e4-media)  rodar e4-media  python3 $S/rotular.py --amostra media ;;
    e4-todos)  rodar e4-todos  python3 $S/rotular.py --amostra todos ;;
    e5)   rodar e5-todos  python3 $S/vetorizar.py --amostra todos
          MAPA_GERAL_PARAMS='{"TOL_PX": 2.0}' rodar e5-tol2 python3 $S/vetorizar.py --amostra todos --variante tol2 ;;
    e6)   rodar e6 python3 $S/rastrear.py ;;
    e7a)  rodar e7a-rapida python3 $S/nomear.py textos --amostra rapida
          rodar e7a-todos  python3 $S/nomear.py textos --amostra todos ;;
    e7)   rodar e7-unioes  python3 $S/nomear.py unioes
          rodar e7-vetores python3 $S/nomear.py vetores --variante e7
          MAPA_GERAL_EXP=e7 rodar e6-e7u python3 $S/rastrear.py --fonte e7u --variante e7
          rodar e7-nomes python3 $S/nomear.py nomes --variante-e6 e7 --variante-vetores e7 --variante v1
          python3 $S/cache.py aprovar e7 v1 >> "$LOGS/cadeia.log"; python3 $S/cache.py aprovar e7u e7 >> "$LOGS/cadeia.log"
          python3 $S/cache.py aprovar e6 e7 >> "$LOGS/cadeia.log" ;;
    e8)   rodar e8-medir python3 $S/construir.py --so-medir
          rodar e8 python3 $S/construir.py --saida "$MAPA_GERAL_CACHE/dados"
          MAPA_GERAL_EXP=tol2 rodar e8-tol2-medir python3 $S/construir.py --so-medir ;;
    testes) rodar testes python3 $S/testar.py e2 e3 e4 e5 e6 e7 ;;
  esac
  [ "$etapa" = "$fim" ] && break
done
echo "== $(date '+%H:%M:%S') cadeia concluída" | tee -a "$LOGS/cadeia.log"
