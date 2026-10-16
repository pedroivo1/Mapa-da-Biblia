import sys,time,cv2,numpy as np,os,re
sys.path.insert(0,'scripts/mapa-geral/experimentos')
import tesserocr
from PIL import Image
import texto_det2 as td
from rapidocr_onnxruntime import RapidOCR
R=RapidOCR()
B=tesserocr.PyTessBaseAPI(path=os.path.expanduser('~/.cache/mapa-biblia-lib/tessdata'),lang='eng',psm=tesserocr.PSM.SINGLE_LINE)
for v in ('load_system_dawg','load_freq_dawg'): B.SetVariable(v,'F')
B.SetVariable('tessedit_char_whitelist',"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .-'")
GT="Kaabu|Cacheu|Jolof|Mane|Toro|Kaarta|Jalon|Kong|Gold Coast|Ash.|Oyo|Benin|Hausa|Guinea|Mandara|Loa.||Wadai|Mbun.|Darfur|Lozi|Luba|Ruanda|Bam.|Ankole|Sennar|Mpondoland|Houaras|Burundi|Buganda|Bunyoro|Mozambique||Oman||Geledi|Yem.|Wars.|Kathiri|Majerteen|Bourbon|Mahri".split('|')
def limpa(s): return re.sub(r"[^A-Za-z. ]","",s).strip(' ')
def prep(im,nome,x,y,w,h,P,E,interp):
    c=im[max(0,y-P):y+h+P,max(0,x-P):x+w+P]
    g=cv2.cvtColor(c,cv2.COLOR_BGR2GRAY).astype(np.float32); med=np.median(g)
    if nome=='claro': g=255-g; med=255-med
    g=np.clip((g-g.min())/max(1,med-g.min())*255,0,255).astype(np.uint8)
    return cv2.resize(g,None,fx=E,fy=E,interpolation=interp)
def rapid(g,pad=10):
    g3=cv2.cvtColor(cv2.copyMakeBorder(g,pad,pad,pad,pad,cv2.BORDER_CONSTANT,value=255),cv2.COLOR_GRAY2BGR)
    out,_=R(g3,use_det=False,use_cls=False,use_rec=True); return (out[0][0],out[0][1]) if out else ('',0)
def tess(g):
    B.SetImage(Image.fromarray(cv2.copyMakeBorder(g,20,20,20,20,cv2.BORDER_CONSTANT,value=255))); return B.GetUTF8Text().strip(),B.MeanTextConf()/100
if __name__=='__main__':
    im=cv2.imread('scripts/mapa-geral/.cache/v2/mapas/2053.png')
    cx=[a for a in td.detectar(im) if 820<=a[1]<=1260 and 480<=a[2]<=820 and a[0]=='escuro'][:len(GT)]
    cfgs={}
    for P in (1,2,3):
      for E in (2,3,4,6):
        for nm,it in (('cub',cv2.INTER_CUBIC),('lan',cv2.INTER_LANCZOS4)):
          for eng in ('rapid','tess'):
            if eng=='tess' and E<3: continue
            cfgs[(eng,P,E,nm)]=[ (rapid if eng=='rapid' else tess)(prep(im,*a,P,E,it)) for a in cx]
    res=[]
    for k,v in cfgs.items():
        ok=sum(1 for g,(s,c) in zip(GT,v) if g and limpa(s).lower()==g.lower())
        res.append((ok,k))
    for r in sorted(res,reverse=True)[:12]: print(r)
    # ensemble: medoid per box across all configs weighted by conf
    import difflib
    ok=0
    for i,g in enumerate(GT):
        if not g: continue
        cands=[(limpa(v[i][0]),v[i][1]) for v in cfgs.values() if limpa(v[i][0])]
        best=max(set(c for c,_ in cands),key=lambda s:sum(w*difflib.SequenceMatcher(None,s,c).ratio() for c,w in cands)) if cands else ''
        ok+= best.lower()==g.lower()
        if best.lower()!=g.lower(): print('  ',g,'->',best)
    print('ensemble',ok,'/',sum(1 for g in GT if g))
