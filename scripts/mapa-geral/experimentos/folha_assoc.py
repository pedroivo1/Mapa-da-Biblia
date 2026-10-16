# Associação etiqueta -> região (E7b) desenhada num recorte: cada etiqueta (caixa verde) ligada por uma linha ao
# ponto interior da região que ficou com ela; deslocadas em laranja; sobras em vermelho; id da E6 ao lado.
import sys,json,cv2,numpy as np
sys.path.insert(0,'scripts/mapa-geral')
import cache, nomear
V2='scripts/mapa-geral/.cache/v2/'
k,x0,y0,w,h,var,out=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4]),int(sys.argv[5]),sys.argv[6],sys.argv[7]
et7=cache.Etapa('e7a'); et4=cache.Etapa('e4e'); ent=json.load(open(cache.Etapa('e6').caminho('entidades','.json')))
ids=[c for c in ent['por_ano'] if c[2]==k][0][3]
im=cv2.imread(V2+f'mapas/{k}.png'); rot=cv2.imread(et4.caminho(k,'.png'),cv2.IMREAD_UNCHANGED); info=json.load(open(et4.caminho(k,'.json')))
est={q['r'] for q in info['regioes'] if q['tipo']=='estado'}
dono,resto=nomear.associar(json.load(open(et7.caminho(k,'.json',var)))['caixas'],rot,est)
E=2; c=cv2.resize(im[y0:y0+h,x0:x0+w],None,fx=E,fy=E,interpolation=cv2.INTER_CUBIC)
def P(x,y): return (int((x-x0)*E),int((y-y0)*E))
for r,e in dono.items():
    ys,xs=np.nonzero(rot==r)
    if not len(xs): continue
    d=cv2.distanceTransform((rot==r).astype(np.uint8),cv2.DIST_L2,3); i=int(d.argmax()); py,px=divmod(i,rot.shape[1])
    bx,by,bw,bh=e['caixa']; cor=(0,140,255) if e.get('deslocada') else (0,150,0)
    cv2.rectangle(c,P(bx,by),P(bx+bw,by+bh),cor,1); cv2.line(c,P(bx+bw/2,by+bh/2),P(px,py),cor,1); cv2.circle(c,P(px,py),3,cor,-1)
    cv2.putText(c,ids.get(str(r),'?'),(P(px,py)[0]+4,P(px,py)[1]+12),0,0.35,(120,0,120),1)
for e in resto:
    bx,by,bw,bh=e['caixa']; cv2.rectangle(c,P(bx,by),P(bx+bw,by+bh),(0,0,255),1)
cv2.imwrite(out,c)
