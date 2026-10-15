import sys,os,json; sys.path.insert(0,'scripts/mapa-geral')
import calibrar as c, cv2, numpy as np
cal=json.load(open(c.V2+'/calibracao.json')); mapas=json.load(open(c.V2+'/mapas.json'))
terra,lagos=c.carregar_mundo()
kern=np.ones((3,3),np.uint8)
for t in [t for t in cal['trechos'] if t['n']>=20]:
    a,b=t['ids']
    ids=sorted([k for k in mapas if mapas[a]['quadro']<=mapas[k]['quadro']<=mapas[b]['quadro']],key=lambda k:mapas[k]['quadro'])
    amostra=[ids[int(len(ids)*f)] for f in (0.1,0.3,0.5,0.7,0.9)]
    acum={'oeste':[], 'centro':[], 'leste':[]}; fora=[]; sh={'oeste':[], 'centro':[], 'leste':[]}
    for k in amostra:
        p=cal['por_mapa'][k]; im=cv2.imread(f"{c.V2}/mapas/{k}.png"); tv,val=c.mascara_terra(im)
        r=c.renderizar(terra,lagos,p['S'],p['X0'],p['Y0'])
        br=cv2.morphologyEx(r,cv2.MORPH_GRADIENT,kern)>0; bv=cv2.morphologyEx(tv,cv2.MORPH_GRADIENT,kern)>0
        dist=cv2.distanceTransform((~br).astype(np.uint8),cv2.DIST_L2,3)
        y0,y1=c.regiao_valida(p['S'],p['Y0'])
        m=np.zeros((960,1920),bool); m[y0+3:y1-3,3:-3]=True; m&=val>0
        s=bv&m; fora.append(float((dist[s]>12).mean()))
        for nm,(xa,xb) in {'oeste':(0,640),'centro':(640,1280),'leste':(1280,1920)}.items():
            q=np.zeros_like(s); q[:,xa:xb]=True; d=dist[s&q]; d=d[d<=12]
            acum[nm].append(float(d.mean()) if len(d)>50 else np.nan)
            # deslocamento local ótimo (±6 px) do terço inteiro
            A=tv[y0:y1,xa:xb]>0; V=val[y0:y1,xa:xb]>0
            R=np.pad(r,((10,10),(10,10)))>0
            best=None
            for dy in range(-6,7):
                for dx in range(-6,7):
                    B=R[y0+10+dy:y1+10+dy,xa+10+dx:xb+10+dx]
                    cst=int(((A!=B)&V).sum())
                    if best is None or cst<best[0]: best=(cst,dx,dy)
            sh[nm].append((best[1],best[2]))
    print('trecho',t['S'],'fora médio %.3f'%np.mean(fora))
    for nm in acum: print('   ',nm,'resíduo médio %.2f px'%np.nanmean(acum[nm]),'deslocamentos ótimos',sh[nm])
