import sys,os,json; sys.path.insert(0,os.path.expanduser('~/.cache/mapa-biblia-lib/lib'))
import numpy as np, cv2
V2='scripts/mapa-geral/.cache/v2/'
mapas=json.load(open(V2+'mapas.json'))
ids=sorted(mapas,key=lambda k:mapas[k]['quadro'])
MAR=np.array([237,225,216])
prev=None; out=[]
sig={}
for k in ids:
    im=cv2.imread(f'{V2}mapas/{k}.png')
    if im is None: print('falta',k); continue
    small=cv2.resize(im,(480,240),interpolation=cv2.INTER_AREA).astype(np.int32)
    m=(np.abs(small-MAR).sum(2)<=24)
    m[200:,:]=m[200:,:]  # ornamento: ignora faixa
    m[205:240,170:310]=False
    if prev is not None:
        out.append((int(k),mapas[k]['quadro'],int((m!=prev).sum())))
    prev=m
json.dump(out,open(V2+'diag_mar.json','w'))
import collections
d=np.array([o[2] for o in out])
print(len(d),(d>0).sum(),(d>20).sum(),(d>100).sum())
print([o for o in out if o[2]>20][:60])
