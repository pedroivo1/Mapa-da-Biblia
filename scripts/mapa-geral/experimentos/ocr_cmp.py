import sys,time,cv2,numpy as np,os
sys.path.insert(0,'scripts/mapa-geral/experimentos')
import tesserocr
from PIL import Image
import texto_det2 as td
from rapidocr_onnxruntime import RapidOCR
R=RapidOCR()
B=tesserocr.PyTessBaseAPI(path=os.path.expanduser('~/.cache/mapa-biblia-lib/tessdata'),lang='eng',psm=tesserocr.PSM.SINGLE_LINE)
for v in ('load_system_dawg','load_freq_dawg'): B.SetVariable(v,'F')
def rec(im,nome,x,y,w,h,P=3):
    c=im[max(0,y-P):y+h+P,max(0,x-P):x+w+P]
    return c
def norm(c,nome,E):
    g=cv2.cvtColor(c,cv2.COLOR_BGR2GRAY).astype(np.float32); med=np.median(g)
    if nome=='claro': g=255-g; med=255-med
    g=np.clip((g-g.min())/max(1,med-g.min())*255,0,255).astype(np.uint8)
    return cv2.resize(g,None,fx=E,fy=E,interpolation=cv2.INTER_CUBIC)
im=cv2.imread('scripts/mapa-geral/.cache/v2/mapas/2053.png')
cx=[a for a in td.detectar(im) if 820<=a[1]<=1260 and 480<=a[2]<=820]
t=time.time(); rr=[]
for a in cx:
    g=norm(rec(im,*a),a[0],3); g3=cv2.cvtColor(cv2.copyMakeBorder(g,10,10,10,10,cv2.BORDER_CONSTANT,value=255),cv2.COLOR_GRAY2BGR)
    out,_=R(g3,use_det=False,use_cls=False,use_rec=True); rr.append(out[0] if out else None)
t1=time.time()-t; t=time.time(); tb=[]
for a in cx:
    g=norm(rec(im,*a),a[0],4); B.SetImage(Image.fromarray(cv2.copyMakeBorder(g,20,20,20,20,cv2.BORDER_CONSTANT,value=255))); tb.append((B.GetUTF8Text().strip(),B.MeanTextConf()))
t2=time.time()-t
for a,r,b in zip(cx,rr,tb): print(a[0][0],r,b)
print(len(cx),'rapid',round(t1,2),'best',round(t2,2))
