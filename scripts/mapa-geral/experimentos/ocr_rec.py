import sys,time,cv2,numpy as np
sys.path.insert(0,'scripts/mapa-geral/experimentos')
import tesserocr
from PIL import Image
import texto_det2 as td
API=tesserocr.PyTessBaseAPI(path='/usr/share/tessdata',lang='eng',psm=tesserocr.PSM.SINGLE_LINE)
for v in ('load_system_dawg','load_freq_dawg'): API.SetVariable(v,'F')
def ler(im,nome,x,y,w,h,E=4,modo='cinza'):
    c=cv2.cvtColor(im[max(0,y-2):y+h+2,max(0,x-2):x+w+2],cv2.COLOR_BGR2GRAY).astype(np.float32)
    med=np.median(c)
    # normaliza: fundo -> branco, letra -> preto
    if nome=='claro': c=255-c; med=255-med
    c=np.clip((c-c.min())/max(1,med-c.min())*255,0,255).astype(np.uint8)
    c=cv2.resize(c,None,fx=E,fy=E,interpolation=cv2.INTER_CUBIC)
    if modo=='otsu': _,c=cv2.threshold(c,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    b=cv2.copyMakeBorder(c,20,20,20,20,cv2.BORDER_CONSTANT,value=255)
    API.SetImage(Image.fromarray(b)); return API.GetUTF8Text().strip(), API.MeanTextConf()
if __name__=='__main__':
    im=cv2.imread('scripts/mapa-geral/.cache/v2/mapas/2053.png')
    cx=td.detectar(im); t=time.time(); n=0
    for args in cx:
        r=ler(im,*args); n+=1
        if 820<=args[1]<=1260 and 480<=args[2]<=820: print(args[0][0], r, ler(im,*args,E=3), ler(im,*args,modo='otsu'))
    print(n,time.time()-t)
