import sys,cv2,time
sys.path.insert(0,'scripts/mapa-geral/experimentos')
import texto_det2 as td, ocr_cmp2 as oc, reconhecer as rc
im=cv2.imread('scripts/mapa-geral/.cache/v2/mapas/2053.png')
cx=[a for a in td.detectar(im) if 820<=a[1]<=1260 and 480<=a[2]<=820 and a[0]=='escuro'][:len(oc.GT)]
ok=n=0; t0=time.time()
for a,g in zip(cx,oc.GT):
    nome,x,y,w,h=a
    cands=[oc.limpa(e(oc.prep(im,*a,P,E,cv2.INTER_CUBIC))[0]) for P,E,e in ((2,6,oc.rapid),(1,3,oc.rapid),(2,6,oc.tess))]
    P=6; ink=rc.tinta(im[y-P:y+h+P,x-P:x+w+P],nome=='claro')
    s,sc,t=rc.escolher(ink,cands,h)
    if g: n+=1; ok+=s==g; print('OK' if s==g else '--',g,'->',s,round(sc,3),t,cands)
print(ok,'/',n,round(time.time()-t0,1),'s')
