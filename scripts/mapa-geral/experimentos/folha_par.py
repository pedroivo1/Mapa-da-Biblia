# Recorte de um par de regiões (rótulos E4e) com as caixas de texto da E7a: região a em vermelho, b em azul.
import sys,json,cv2,numpy as np
sys.path.insert(0,'scripts/mapa-geral')
import cache
V2='scripts/mapa-geral/.cache/v2/'
k,ra,rb=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]); var=sys.argv[4] if len(sys.argv)>4 else None; out=sys.argv[5]
im=cv2.imread(V2+f'mapas/{k}.png'); rot=cv2.imread(V2+f'rotulos/{k}.png',cv2.IMREAD_UNCHANGED)
m=(rot==ra)|(rot==rb); ys,xs=np.nonzero(m); y0,y1,x0,x1=max(0,ys.min()-25),ys.max()+25,max(0,xs.min()-40),xs.max()+40
c=im[y0:y1,x0:x1].copy()
for r,cor in ((ra,(0,0,255)),(rb,(255,0,0))):
    mm=(rot[y0:y1,x0:x1]==r).astype(np.uint8); cs,_=cv2.findContours(mm,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE); cv2.drawContours(c,cs,-1,cor,1)
E=4; c=cv2.resize(c,None,fx=E,fy=E,interpolation=cv2.INTER_NEAREST)
et=cache.Etapa('e7a')
for t,x,y,w,h,hh,cands in json.load(open(et.caminho(k,'.json',var)))['caixas']:
    if x+w<x0 or x>x1 or y+h<y0 or y>y1: continue
    cv2.rectangle(c,((x-x0)*E,(y-y0)*E),((x+w-x0)*E,(y+h-y0)*E),(0,160,0),1)
    if cands: cv2.putText(c,f'{cands[0][0]} {cands[0][1]:.2f}',((x-x0)*E,(y-y0)*E-3),0,0.45,(0,120,0),1)
cv2.imwrite(out,c)
