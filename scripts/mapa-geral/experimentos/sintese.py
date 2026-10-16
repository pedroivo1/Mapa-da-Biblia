# O texto certo ganha das leituras erradas quando renderizado e comparado com o recorte?
import sys,os,cv2,numpy as np
sys.path.insert(0,'scripts/mapa-geral/experimentos')
import texto_det2 as td, fonte as fo, ocr_cmp2 as oc
F=os.path.expanduser('~/.cache/mapa-biblia-lib/fontes/'+(sys.argv[1] if len(sys.argv)>1 else 'OpenSans.ttf'))
TAMS=[x/4 for x in range(22,40)]
im=cv2.imread('scripts/mapa-geral/.cache/v2/mapas/2053.png')
cx=[a for a in td.detectar(im) if 820<=a[1]<=1260 and 480<=a[2]<=820 and a[0]=='escuro'][:len(oc.GT)]
cand={i:set() for i in range(len(cx))}
for i,a in enumerate(cx):
    for P,E,eng in ((2,6,oc.tess),(2,6,oc.rapid),(1,6,oc.rapid),(1,3,oc.rapid),(2,3,oc.tess)):
        s=oc.limpa(eng(oc.prep(im,*a,P,E,cv2.INTER_CUBIC))[0])
        if s: cand[i].add(s)
ok=n=0
for i,g in enumerate(oc.GT):
    if not g: continue
    n+=1; ink=fo.tinta(im,*cx[i])
    sc=sorted(((fo.melhor(ink,F,c,TAMS)[0],c) for c in cand[i]|{g}),reverse=True)
    ok+=sc[0][1]==g
    print('OK' if sc[0][1]==g else '--',g,[(round(float(s),3),c) for s,c in sc[:4]])
print(ok,'/',n)
