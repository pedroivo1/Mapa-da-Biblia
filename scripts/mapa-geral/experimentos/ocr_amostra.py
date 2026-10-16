# Acerto da leitura (melhor candidata do recorte) na amostra conferida (texto-amostra.json), a partir de textos/<id>.json.
import sys,os,json
sys.path.insert(0,'scripts/mapa-geral')
import cache
et=cache.Etapa('e7a'); VAR=sys.argv[1] if len(sys.argv)>1 else None
am=json.load(open('scripts/mapa-geral/texto-amostra.json'))['mapas']
ok=n=semcx=0; erros=[]
for k,lst in am.items():
    cx=json.load(open(et.caminho(k,'.json',VAR)))['caixas']
    for e in lst:
        n+=1
        dentro=[c for c in cx if c[1]-3<=e['x']<=c[1]+c[3]+3 and c[2]-3<=e['y']<=c[2]+c[4]+3]
        if not dentro: semcx+=1; erros.append((k,e['texto'],'(sem caixa)')); continue
        lidos=[c[6][0][0] for c in dentro if c[6]]
        if e['texto'] in lidos: ok+=1
        else: erros.append((k,e['texto'],lidos))
print(f'leitura exata {ok}/{n} = {ok/n:.1%}  sem caixa {semcx}')
for x in erros: print(' ',x)
