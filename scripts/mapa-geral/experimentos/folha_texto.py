# Folha para conferir a detecção de texto à mão: recorte do mapa ampliado 2×, grade a cada 20 px (coordenadas do
# quadro em 1920×960), caixas detectadas (vermelho = escuro, azul = claro) e, se houver, os pontos da amostra
# (verde = detectado, magenta = perdido).
# Uso: python3 folha_texto.py <mapa> <x0> <y0> [<w> <h>] [saida.png]
import sys,os,json,cv2,numpy as np
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
import texto
V2='scripts/mapa-geral/.cache/v2/'
k=sys.argv[1]; x0,y0=int(sys.argv[2]),int(sys.argv[3])
w=int(sys.argv[4]) if len(sys.argv)>4 else 480; h=int(sys.argv[5]) if len(sys.argv)>5 else 300
out=sys.argv[6] if len(sys.argv)>6 else f'/tmp/claude-1000/-data-Documents-Programing-Mapa-da-Biblia/ed6218b9-c80c-4986-8a8a-3f15c2c0664b/scratchpad/folha_{k}_{x0}_{y0}.png'
im=cv2.imread(V2+f'mapas/{k}.png'); cx=texto.detectar(im)
c=cv2.resize(im[y0:y0+h,x0:x0+w],None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC)
for gx in range((x0//20+1)*20,x0+w,20):
    cv2.line(c,((gx-x0)*2,0),((gx-x0)*2,2*h),(200,200,200) if gx%100 else (120,120,120),1)
    if gx%100==0: cv2.putText(c,str(gx),((gx-x0)*2+2,10),0,0.35,(0,0,0),1)
for gy in range((y0//20+1)*20,y0+h,20):
    cv2.line(c,(0,(gy-y0)*2),(2*w,(gy-y0)*2),(200,200,200) if gy%100 else (120,120,120),1)
    if gy%100==0: cv2.putText(c,str(gy),(2,(gy-y0)*2-2),0,0.35,(0,0,0),1)
for t,x,y,ww,hh in cx:
    cv2.rectangle(c,((x-x0)*2-1,(y-y0)*2-1),((x+ww-x0)*2,(y+hh-y0)*2),(0,0,255) if t=='escuro' else (255,0,0),1)
am=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','texto-amostra.json')
if os.path.exists(am):
    for e in json.load(open(am))['mapas'].get(k,[]):
        px,py=e['x'],e['y']
        ok=any(x-3<=px<=x+ww+3 and y-3<=py<=y+hh+3 for t,x,y,ww,hh in cx)
        cv2.circle(c,((px-x0)*2,(py-y0)*2),4,(0,200,0) if ok else (255,0,255),-1)
cv2.imwrite(out,c); print(out,len(cx))
