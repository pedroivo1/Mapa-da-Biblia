# Detecção de texto: black-hat (texto escuro sobre claro) e top-hat (texto claro sobre escuro/colorido) na luminância,
# limiar, componentes com forma de letra, agrupados em palavras/linhas.
import sys,json,numpy as np,cv2
V2='scripts/mapa-geral/.cache/v2/'
def detectar(im):
    g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
    k=cv2.getStructuringElement(cv2.MORPH_RECT,(15,15))
    bh=cv2.morphologyEx(g,cv2.MORPH_BLACKHAT,k); th=cv2.morphologyEx(g,cv2.MORPH_TOPHAT,k)
    out=[]
    for nome,m in (('escuro',bh),('claro',th)):
        b=((m>40)&((g<=125) if nome=='escuro' else (g>=195))).astype(np.uint8)
        n,lab,st,_=cv2.connectedComponentsWithStats(b,connectivity=8)
        keep=np.zeros(n,bool)
        for i in range(1,n):
            x,y,w,h,a=st[i]
            if 3<=h<=40 and w<=60 and a>=4 and a<=0.9*w*h+5: keep[i]=True
        letras=keep[lab].astype(np.uint8)*255
        # agrupa letras em palavras: dilatação horizontal
        pal=cv2.dilate(letras,cv2.getStructuringElement(cv2.MORPH_RECT,(7,3)))
        n2,l2,s2,_=cv2.connectedComponentsWithStats((pal>0).astype(np.uint8),connectivity=8)
        for i in range(1,n2):
            x,y,w,h,a=s2[i]
            if w>=8 and 6<=h<=45 and w>=0.8*h: out.append((nome,int(x),int(y),int(w),int(h)))
    return out
if __name__=='__main__':
    for k in sys.argv[1:]:
        im=cv2.imread(V2+f'mapas/{k}.png'); cx=detectar(im); o=im.copy()
        for nome,x,y,w,h in cx: cv2.rectangle(o,(x,y),(x+w,y+h),(0,0,255) if nome=='escuro' else (255,0,255),1)
        cv2.imwrite(f'/tmp/claude-1000/-data-Documents-Programing-Mapa-da-Biblia/ed6218b9-c80c-4986-8a8a-3f15c2c0664b/scratchpad/det{k}.png',o); print(k,len(cx))
