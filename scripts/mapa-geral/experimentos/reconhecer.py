# Reconhecedor de rótulo: OCR (RapidOCR + Tesseract) dá candidatos; a renderização com uma fonte sem serifa
# (Open Sans) escolhe o que melhor explica o recorte e corrige letra a letra (busca local por edições).
import sys,os,re,time,cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,'scripts/mapa-geral/experimentos')
FONTE=os.path.expanduser('~/.cache/mapa-biblia-lib/fontes/OpenSans.ttf')
SS=4
ALFA="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.' -"
CONF={'i':'lIjtrf1','l':'iIt1','I':'lit','r':'nt','n':'rmuh','m':'n','u':'nv','v':'uy','c':'eoa','e':'cao','o':'aecu','a':'oesu','s':'ae','h':'bkn','b':'hd','k':'hx','g':'qy','q':'g','y':'gv','d':'b','f':'tl','t':'fli','B':'R','R':'B','D':'O','O':'DQ','C':'G','G':'C','K':'X','X':'K','V':'Y','Y':'V','M':'N','N':'M','E':'F','F':'E','.':',',' ':''}
_fontes={}
def fonte(tam):
    k=round(tam*SS*4)/4
    if k not in _fontes: _fontes[k]=ImageFont.truetype(FONTE,k)
    return _fontes[k]
_rend={}
def render(txt,tam):
    k=(txt,tam)
    if k in _rend: return _rend[k]
    f=fonte(tam); l,t,r,b=f.getbbox(txt)
    im=Image.new('L',(max(1,r-l)+2*SS,max(1,b-t)+2*SS),0); ImageDraw.Draw(im).text((SS-l,SS-t),txt,font=f,fill=255)
    a=np.asarray(im,np.float32)/255
    if len(_rend)>20000: _rend.clear()
    tpls=[]
    for oy in range(SS):
        for ox in range(SS):
            b=a[oy:,ox:]; H,W=b.shape[0]//SS*SS,b.shape[1]//SS*SS
            tpls.append(b[:H,:W].reshape(H//SS,SS,W//SS,SS).mean((1,3)))
    _rend[k]=tpls; return tpls
def tinta(crop,claro):
    g=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY).astype(np.float32); med=np.median(g)
    t=(g-med) if claro else (med-g)
    return np.clip(t/max(1.0,t.max()),0,1)
MODO='margem'
def nota(ink4,txt,tam):
    if MODO=='margem': return nota_margem(ink4,txt,tam)
    # correlação no recorte inteiro (tinta que o texto não explica conta contra), na melhor posição
    if not txt.strip(): return -1.0
    N=ink4.size; mi=float(ink4.mean()); si=float(ink4.std())+1e-6
    best=-1.0
    for tpl in render(txt,tam):
        if tpl.shape[0]>ink4.shape[0] or tpl.shape[1]>ink4.shape[1]: continue
        st_=float(tpl.sum()); mt=st_/N; vt=float((tpl*tpl).sum())/N-mt*mt
        if vt<=0: continue
        dot=float(cv2.matchTemplate(ink4,tpl,cv2.TM_CCORR).max())
        best=max(best,(dot/N-mi*mt)/(si*vt**0.5))
    return best
def nota_margem(ink,txt,tam):
    # NCC local com o texto cercado de uma margem vazia (~1 letra dos lados, 1 px em cima/embaixo): letra que falta
    # ou sobra ao lado conta contra; tinta longe (outro rótulo, fronteira) não.
    if not txt.strip(): return -1.0
    mx=max(2,int(round(0.55*tam))); best=-1.0
    for tpl in render(txt,tam):
        t=cv2.copyMakeBorder(tpl,1,1,mx,mx,cv2.BORDER_CONSTANT,value=0)
        if t.shape[0]>ink.shape[0] or t.shape[1]>ink.shape[1]:
            pad=(max(0,t.shape[0]-ink.shape[0]),max(0,t.shape[1]-ink.shape[1]))
            ink2=cv2.copyMakeBorder(ink,pad[0],pad[0],pad[1],pad[1],cv2.BORDER_CONSTANT,value=0)
        else: ink2=ink
        best=max(best,float(cv2.matchTemplate(ink2,t,cv2.TM_CCOEFF_NORMED).max()))
    return best
def valido(s):
    # maiúscula só no começo de palavra; ponto só no fim de palavra; sem espaço duplo
    for w in s.split(' '):
        if not w: return False
        if any(c.isupper() for c in w[1:]) and not w.isupper(): return False
        if '.' in w[:-1] or w[0] in ".'-": return False
    return True
def dist(a,b):
    d=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        p,d[0]=d[0],i
        for j,cb in enumerate(b,1):
            p,d[j]=d[j],min(d[j]+1,d[j-1]+1,p+(ca!=cb))
    return d[-1]
PEN=0.012
def tamanho(ink4,txt,h):
    # o tamanho da fonte (px) que melhor explica o recorte, a partir da altura da caixa
    base=max(4.0,h/0.95)
    tams=[x/4 for x in range(int(base*0.55*4),int(base*1.6*4)+1)]
    sc=[(nota(ink4,txt,t),t) for t in tams]
    s,t=max(sc); return t,s
def limpa(s): return re.sub(r"\s+"," ",re.sub(r"[^A-Za-z.' -]","",s)).strip(" -'")
def editar(s):
    out=set()
    for i,c in enumerate(s):
        out.add(s[:i]+s[i+1:])
        for d in CONF.get(c,''): out.add(s[:i]+d+s[i+1:])
    for i in range(len(s)+1):
        for d in 'ilrtnaeo.':
            out.add(s[:i]+d+s[i:])
    for i in range(len(s)-1):
        if s[i:i+2]=='rn': out.add(s[:i]+'m'+s[i+2:])
        if s[i]=='m': out.add(s[:i]+'rn'+s[i+1:])
    out.discard(s); return [x for x in out if x.strip()]
def escolher(ink4,cands,h,buscar=True,rodadas=4):
    cands=[c for c in {limpa(c) for c in cands} if len(c)>=1]
    if not cands: return '',0.0,None
    tams=[x/4 for x in range(int(h*0.85*4),int(h*1.5*4)+1)]
    ocr=list(cands)
    def nt(c):
        s,t=max((nota(ink4,c,t),t) for t in tams)
        return s-PEN*min(dist(c,o) for o in ocr),t
    sc=sorted(((nt(c),c) for c in cands),reverse=True)
    (best_s,t),best=sc[0]
    if buscar:
        for _ in range(rodadas):
            viz=[(nt(c)[0],c) for c in editar(best) if valido(c)]
            if not viz: break
            s,c=max(viz)
            if s>best_s+0.002: best_s,best=s,c
            else: break
    return best,best_s,t
