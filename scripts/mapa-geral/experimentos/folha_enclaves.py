# Folha dos enclaves "suspeitos": < 300 px e linha na fronteira comum < 30 % (todos os mapas). Cada célula: quadro do
# vídeo ampliado com o contorno do enclave (verde) e do vizinho (magenta), ano, área, letra, linha.
import json,os,numpy as np,cv2
V2='scripts/mapa-geral/.cache/v2/'
mapas=json.load(open(V2+'mapas.json'))
sel=[]
for k in sorted(mapas,key=lambda k:mapas[k]['quadro']):
    j=json.load(open(V2+f'rotulos/{k}.json'))
    for e in j.get('enclaves',[]):
        if e['area_px']<300 and e.get('fracao_linha_fronteira',1)<0.3: sel.append((k,e))
print(len(sel),'em',len({k for k,_ in sel}),'mapas')
cs=[]
for k,e in sel:
    im=cv2.imread(V2+f'mapas/{k}.png'); reg=cv2.imread(V2+f'rotulos/{k}.png',cv2.IMREAD_UNCHANGED)
    x0,y0,x1,y1=e['caixa']; cx,cy=(x0+x1)//2,(y0+y1)//2; h=max(26,(x1-x0)//2+14,(y1-y0)//2+14)
    sl=(slice(max(0,cy-h),cy+h),slice(max(0,cx-h),cx+h)); c=im[sl].copy()
    for r,col in ((e['dono'],(255,0,255)),(e['r'],(0,220,0))):
        m=(reg[sl]==r).astype(np.uint8); b=m.astype(bool)&~cv2.erode(m,np.ones((3,3),np.uint8)).astype(bool); c[b]=col
    c=cv2.resize(c,(150,150),interpolation=cv2.INTER_NEAREST)
    cv2.putText(c,f"{mapas[k]['anos'][0]} {e['area_px']}px L{e['fracao_letra']} lf{e['fracao_linha_fronteira']}",(2,11),0,0.32,(0,0,200),1)
    cs.append(c)
lin=[np.hstack(cs[i:i+10]+[np.full_like(cs[0],255)]*(10-len(cs[i:i+10]))) for i in range(0,len(cs),10)]
for n,i in enumerate(range(0,len(lin),6)):
    cv2.imwrite(V2+f'revisao/enclaves-suspeitos-{n+1}.png',np.vstack(lin[i:i+6]))
json.dump([dict(e,mapa=k,ano=mapas[k]['anos'][0]) for k,e in sel],open(V2+'enclaves-suspeitos.json','w'),indent=0)
