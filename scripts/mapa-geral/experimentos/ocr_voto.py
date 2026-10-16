# Leitura de um mesmo rótulo em vários mapas seguidos: o voto melhora o nome?
import sys,cv2,numpy as np,re,difflib,hashlib,json,os
sys.path.insert(0,'scripts/mapa-geral/experimentos')
import texto_det2 as td, ocr_cmp2 as oc
GT=dict(zip(range(100),oc.GT))
ref=[a for a in td.detectar(cv2.imread('scripts/mapa-geral/.cache/v2/mapas/2053.png')) if 820<=a[1]<=1260 and 480<=a[2]<=820 and a[0]=='escuro'][:len(oc.GT)]
leituras={i:[] for i in range(len(ref))}
for k in range(2030,2076):
    im=cv2.imread(f'scripts/mapa-geral/.cache/v2/mapas/{k}.png')
    if im is None: continue
    for a in td.detectar(im):
        if a[0]!='escuro': continue
        # o rótulo de referência mais próximo (centro a <= 4 px, tamanho parecido)
        for i,r in enumerate(ref):
            if abs(a[1]+a[3]/2-r[1]-r[3]/2)<=4 and abs(a[2]+a[4]/2-r[2]-r[4]/2)<=3 and abs(a[3]-r[3])<=4:
                for P,E,eng in ((2,6,oc.tess),(2,6,oc.rapid),(1,6,oc.rapid),(1,3,oc.rapid)):
                    s,c=eng(oc.prep(im,*a,P,E,cv2.INTER_CUBIC)); s=oc.limpa(s)
                    if s: leituras[i].append((s,c))
ok=0;n=0
for i,g in enumerate(oc.GT):
    if not g: continue
    n+=1; c=leituras[i]
    best=max(set(s for s,_ in c),key=lambda s:sum(w*difflib.SequenceMatcher(None,s,t).ratio() for t,w in c)) if c else ''
    ok+=best.lower()==g.lower()
    print(('OK ' if best.lower()==g.lower() else '-- ')+g,'->',best,len(c))
print(ok,'/',n)
