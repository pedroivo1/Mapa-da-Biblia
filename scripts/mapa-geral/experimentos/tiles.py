import sys,os,json; sys.path.insert(0,'scripts/mapa-geral')
import calibrar as c, cv2, numpy as np
cal=json.load(open(c.V2+'/calibracao.json')); mapas=json.load(open(c.V2+'/mapas.json'))
terra,lagos=c.carregar_mundo()
def limpa(m,amin):
    n,lab,st,_=cv2.connectedComponentsWithStats((m>0).astype(np.uint8),connectivity=8)
    keep=np.zeros(n,bool); keep[1:]=st[1:,cv2.CC_STAT_AREA]>=amin
    return (keep[lab]*255).astype(np.uint8)
for t in [t for t in cal['trechos'] if t['n']>=20]:
    a,b=t['ids']
    ids=sorted([k for k in mapas if mapas[a]['quadro']<=mapas[k]['quadro']<=mapas[b]['quadro']],key=lambda k:mapas[k]['quadro'])
    k=ids[len(ids)//2]; p=cal['por_mapa'][k]
    im=cv2.imread(f"{c.V2}/mapas/{k}.png"); tv,val=c.mascara_terra(im)
    r=c.renderizar(terra,lagos,p['S'],p['X0'],p['Y0'])
    y0,y1=c.regiao_valida(p['S'],p['Y0'])
    print('trecho',t['S'],'mapa',k,'linhas',y0,y1)
    # tiles 4 colunas x 3 linhas; melhor deslocamento (dx,dy) em ±8 px que minimiza XOR
    cols=np.linspace(0,1920,5).astype(int); rows=np.linspace(y0,y1,4).astype(int)
    for ri in range(3):
        line=[]
        for ci in range(4):
            xs,xe,ys,ye=cols[ci],cols[ci+1],rows[ri],rows[ri+1]
            A=tv[ys:ye,xs:xe]>0; V=val[ys:ye,xs:xe]>0
            best=None
            R=np.pad(r,((10,10),(10,10)))>0
            for dy in range(-8,9):
                for dx in range(-8,9):
                    B=R[ys+10+dy:ye+10+dy,xs+10+dx:xe+10+dx]
                    cost=((A!=B)&V).sum()
                    if best is None or cost<best[0]: best=(cost,dx,dy)
            c0=((A!=R[ys+10:ye+10,xs+10:xe+10])&V).sum()
            line.append(f"({best[1]:+d},{best[2]:+d}) {100*c0/max(1,V.sum()):.1f}%->{100*best[0]/max(1,V.sum()):.1f}%")
        print('  linha',ri,' | '.join(line))
