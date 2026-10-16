# Recall da detecção na amostra conferida (texto-amostra.json). Parâmetros extras via JSON no argv[1].
import sys,os,json,cv2
sys.path.insert(0,'scripts/mapa-geral')
import texto
p=dict(texto.PARAMS); 
if len(sys.argv)>1: p.update(json.loads(sys.argv[1]))
am=json.load(open('scripts/mapa-geral/texto-amostra.json'))['mapas']
ok=n=nc=0; perdidos=[]
for k,lst in am.items():
    im=cv2.imread(f'scripts/mapa-geral/.cache/v2/mapas/{k}.png'); cx=texto.detectar(im,p); nc+=len(cx)
    for e in lst:
        n+=1
        if any(x-3<=e['x']<=x+w+3 and y-3<=e['y']<=y+h+3 for t,x,y,w,h in cx): ok+=1
        else: perdidos.append((k,e['texto']))
print(f'recall {ok}/{n} = {ok/n:.1%}  caixas {nc}'); print(perdidos)
