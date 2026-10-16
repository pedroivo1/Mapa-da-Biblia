# Detecção de texto v2: letras do vídeo são neutras (cinza-escuro ou branco), regiões são coloridas.
# Máscara: escuro = black-hat>30 & cinza<=150 & croma<=45; claro = top-hat>30 & cinza>=190 & croma<=40.
# Componentes com forma de letra; palavras = letras na mesma linha (sobreposição vertical >= 50 %) com vão <= 0,7 h.
import sys,json,numpy as np,cv2
V2='scripts/mapa-geral/.cache/v2/'
def mascaras(im):
    g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
    ch=(im.max(2).astype(np.int16)-im.min(2)).astype(np.int16)
    med=cv2.medianBlur(g,15).astype(np.int16); gi=g.astype(np.int16)
    bh=med-gi; th=gi-med
    out={'escuro':(bh>30)&(g<=150)&(ch<=60),'claro':(th>30)&(g>=175)}
    k5=cv2.getStructuringElement(cv2.MORPH_RECT,(5,5)); k3=np.ones((3,3),np.uint8)
    for n,m in out.items():      # traço de letra é fino: tira as partes grossas (terra, mancha) e a borda delas
        m8=m.astype(np.uint8); grosso=cv2.dilate(cv2.morphologyEx(m8,cv2.MORPH_OPEN,k5),k3)
        out[n]=m&(grosso==0)
    return out
def letras(b):
    n,lab,st,_=cv2.connectedComponentsWithStats(b.astype(np.uint8),connectivity=8)
    out=[]
    for i in range(1,n):
        x,y,w,h,a=st[i]
        if 2<=h<=34 and w<=300 and a<=(0.92*w*h+4 if w<=1.5*h else 0.7*w*h): out.append([x,y,w,h,a])
    return out
def agrupar(L):
    L=sorted(L,key=lambda t:t[0]); pai=list(range(len(L)))
    def f(i):
        while pai[i]!=i: pai[i]=pai[pai[i]]; i=pai[i]
        return i
    for i,(x,y,w,h,a) in enumerate(L):
        for j in range(i+1,len(L)):
            x2,y2,w2,h2,a2=L[j]
            if x2>x+w+40: break
            hh=max(h,h2,6); gap=x2-(x+w)
            ov=min(y+h,y2+h2)-max(y,y2)
            if gap<=0.7*hh and ov>=0.5*min(h,h2) and max(h,h2)<=2.2*max(3,min(h,h2)) or (gap<=0.7*hh and min(h,h2)<=3 and ov>=0):
                pai[f(j)]=f(i)
    g={}
    for i in range(len(L)): g.setdefault(f(i),[]).append(L[i])
    out=[]
    for m in g.values():
        x0=min(t[0] for t in m); y0=min(t[1] for t in m); x1=max(t[0]+t[2] for t in m); y1=max(t[1]+t[3] for t in m)
        hs=sorted(t[3] for t in m); hm=hs[len(hs)//2]
        if (len([t for t in m if t[3]>=3])>=2 or (len(m)==1 and m[0][2]>=2*m[0][3])) and 3<=hm<=30 and y1-y0>=5 and x1-x0>=1.2*(y1-y0): out.append((int(x0),int(y0),int(x1-x0),int(y1-y0),len(m)))
    return out
def detectar(im):
    return [(nome,)+p[:4] for nome,b in mascaras(im).items() for p in agrupar(letras(b))]
if __name__=='__main__':
    for k in sys.argv[1:]:
        im=cv2.imread(V2+f'mapas/{k}.png'); cx=detectar(im); o=im.copy()
        for nome,x,y,w,h in cx: cv2.rectangle(o,(x-1,y-1),(x+w,y+h),(0,0,255) if nome=='escuro' else (255,0,0),1)
        cv2.imwrite(f'/tmp/claude-1000/-data-Documents-Programing-Mapa-da-Biblia/ed6218b9-c80c-4986-8a8a-3f15c2c0664b/scratchpad/det{k}.png',o); print(k,len(cx))
