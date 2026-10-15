import sys,os,json; sys.path.insert(0,'scripts/mapa-geral')
import calibrar as c, cv2, numpy as np
T='/tmp/claude-1000/-data-Documents-Programing-Mapa-da-Biblia/ed6218b9-c80c-4986-8a8a-3f15c2c0664b/scratchpad/'
cal=json.load(open(c.V2+'/calibracao.json')); mapas=json.load(open(c.V2+'/mapas.json'))
terra,lagos=c.carregar_mundo()
for t in [t for t in cal['trechos'] if t['n']>=20]:
    a,b=t['ids']
    ids=sorted([k for k in mapas if mapas[a]['quadro']<=mapas[k]['quadro']<=mapas[b]['quadro']],key=lambda k:mapas[k]['quadro'])
    k=ids[len(ids)//2]; p=cal['por_mapa'][k]
    im=cv2.imread(f"{c.V2}/mapas/{k}.png"); tv,val=c.mascara_terra(im)
    r=c.renderizar(terra,lagos,p['S'],p['X0'],p['Y0'])
    kern=np.ones((3,3),np.uint8)
    bv=cv2.morphologyEx(tv,cv2.MORPH_GRADIENT,kern)>0
    br=cv2.morphologyEx(r,cv2.MORPH_GRADIENT,kern)>0
    dist=cv2.distanceTransform((~br).astype(np.uint8),cv2.DIST_L2,3)
    far=bv&(dist>12)&(val>0)
    out=(im*0.5+127).astype(np.uint8)
    out[br]=(0,0,255)         # costa do mundo.json (vermelho)
    out[far]=(255,0,255)      # costa do vídeo a > 12 px (magenta)
    name=f"{T}fora_{t['S']}.png"
    cv2.imwrite(name,out)
    # resíduo por região, sem corte, e fração fora, por terço oeste/centro/leste e norte/sul
    y0,y1=c.regiao_valida(p['S'],p['Y0'])
    m=np.zeros((960,1920),bool); m[y0+3:y1-3,3:-3]=True; m&=val>0
    sel=bv&m
    print('trecho',t['S'],k)
    for ln,(ya,yb) in {'norte':(y0,(y0+y1)//2),'sul':((y0+y1)//2,y1)}.items():
        row=[]
        for cn,(xa,xb) in {'oeste':(0,640),'centro':(640,1280),'leste':(1280,1920)}.items():
            q=np.zeros_like(sel); q[ya:yb,xa:xb]=True; s=sel&q
            d=dist[s]
            if len(d)<50: row.append(f"{cn}: n={len(d)}"); continue
            perto=d[d<=12]
            row.append(f"{cn}: n={len(d)} med={np.median(perto):.2f} p90={np.percentile(perto,90):.2f} fora={100*(1-len(perto)/len(d)):.0f}%")
        print('  ',ln,' | '.join(row))
