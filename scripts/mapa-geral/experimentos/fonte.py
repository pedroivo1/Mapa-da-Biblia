# Qual fonte (e tamanho) o vídeo usa nos rótulos? Renderiza o texto conhecido e correlaciona com o recorte.
import sys,os,glob,cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,'scripts/mapa-geral/experimentos')
import texto_det2 as td
SS=8
def tinta(im,nome,x,y,w,h,P=6):
    g=cv2.cvtColor(im[y-P:y+h+P,x-P:x+w+P],cv2.COLOR_BGR2GRAY).astype(np.float32)
    med=np.median(g)
    t=(med-g) if nome=='escuro' else (g-med)
    return np.clip(t/max(1,t.max()),0,1)
def render(fonte,txt,tam,var=None):
    f=ImageFont.truetype(fonte,tam*SS)
    if var: 
        try: f.set_variation_by_name(var)
        except Exception: pass
    l,t,r,b=f.getbbox(txt)
    im=Image.new('L',(r-l+4*SS,b-t+4*SS),0); ImageDraw.Draw(im).text((2*SS-l,2*SS-t),txt,font=f,fill=255)
    return np.asarray(im,np.float32)/255
def melhor(ink,fonte,txt,tams,var=None):
    best=(-1,None)
    for tam in tams:
        big=render(fonte,txt,tam,var)
        for oy in range(0,SS,2):
            for ox in range(0,SS,2):
                b=big[oy:,ox:]; H,W=b.shape[0]//SS*SS,b.shape[1]//SS*SS
                tpl=b[:H,:W].reshape(H//SS,SS,W//SS,SS).mean((1,3))
                if tpl.shape[0]>ink.shape[0] or tpl.shape[1]>ink.shape[1]: continue
                s=cv2.matchTemplate(ink,tpl,cv2.TM_CCOEFF_NORMED).max()
                if s>best[0]: best=(s,tam)
    return best
if __name__=='__main__':
    im=cv2.imread('scripts/mapa-geral/.cache/v2/mapas/2053.png')
    cx=[a for a in td.detectar(im) if 820<=a[1]<=1260 and 480<=a[2]<=820 and a[0]=='escuro']
    import ocr_cmp2 as oc
    alvo={g:a for g,a in zip(oc.GT,cx) if g in ('Mozambique','Mpondoland','Majerteen','Bunyoro','Burundi','Darfur','Gold Coast','Kathiri','Wadai')}
    fontes=glob.glob(os.path.expanduser('~/.cache/mapa-biblia-lib/fontes/*.ttf'))+['/usr/share/fonts/liberation/LiberationSans-Regular.ttf']+glob.glob('/usr/share/fonts/**/DejaVuSans.ttf',recursive=True)+glob.glob('/usr/share/fonts/**/FiraSans-Regular.*',recursive=True)+glob.glob('/usr/share/fonts/**/Cantarell*Regular*',recursive=True)
    tams=[x/4 for x in range(20,48)]
    for f in fontes:
        r=[melhor(tinta(im,*a),f,g,tams) for g,a in alvo.items()]
        print(os.path.basename(f)[:28].ljust(28),round(float(np.mean([s for s,_ in r])),3),[t for _,t in r])
