import sys,os,json,cv2
sys.path.insert(0,'scripts/mapa-geral')
import texto
am=json.load(open('scripts/mapa-geral/texto-amostra.json'))['mapas']
ok=n=nc=0; perdidos=[]
for k,lst in am.items():
    im=cv2.imread(f'scripts/mapa-geral/.cache/v2/mapas/{k}.png')
    rot=cv2.imread(f'scripts/mapa-geral/.cache/v2/rotulos/{k}.png',cv2.IMREAD_UNCHANGED); d=json.load(open(f'scripts/mapa-geral/.cache/v2/rotulos/{k}.json'))
    br={r['r'] for r in d['regioes'] if min(r['cor'])>=235}
    cx=texto.detectar(im,texto.PARAMS,rot,br); nc+=len(cx)
    for e in lst:
        n+=1
        if any(x-3<=e['x']<=x+w+3 and y-3<=e['y']<=y+h+3 for t,x,y,w,h in cx): ok+=1
        else: perdidos.append((k,e['texto']))
print(f'recall {ok}/{n} = {ok/n:.1%}  caixas {nc}'); print(perdidos)
