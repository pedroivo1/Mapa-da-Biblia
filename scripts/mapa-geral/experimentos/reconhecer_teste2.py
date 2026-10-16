import sys,cv2,time,os
sys.path.insert(0,'scripts/mapa-geral/experimentos')
import texto_det2 as td, ocr_cmp2 as oc, reconhecer as rc
rc.FONTE=os.path.expanduser('~/.cache/mapa-biblia-lib/fontes/'+(sys.argv[1] if len(sys.argv)>1 else 'OpenSans.ttf'))
im=cv2.imread('scripts/mapa-geral/.cache/v2/mapas/2053.png')
cx=[a for a in td.detectar(im) if 820<=a[1]<=1260 and 480<=a[2]<=820 and a[0]=='escuro'][:len(oc.GT)]
ok=n=dentro=0; t0=time.time(); tocr=0
VAR=[(P,E,e) for P in (1,2,3) for E in (3,4,6) for e in (oc.rapid,oc.tess)]
for a,g in zip(cx,oc.GT):
    nome,x,y,w,h=a; t1=time.time()
    cands={oc.limpa(e(oc.prep(im,*a,P,E,cv2.INTER_CUBIC))[0]) for P,E,e in VAR}
    tocr+=time.time()-t1
    cands={c for c in cands if c and rc.valido(c)}
    P=6; ink=rc.tinta(im[y-P:y+h+P,x-P:x+w+P],nome=='claro')
    rc.PEN=0
    s,sc,t=rc.escolher(ink,cands,h,buscar=False)
    if g: n+=1; ok+=s==g; dentro+=g in cands; print('OK' if s==g else '--',g,'->',s,round(sc,3),t,len(cands),g in cands)
print(ok,'/',n,'certo entre os candidatos',dentro,round(time.time()-t0,1),'s  ocr',round(tocr,1))
