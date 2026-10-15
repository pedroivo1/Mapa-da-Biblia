# IoU de regiões pequenas (rasterizadas de volta no quadro) para tolerâncias diferentes do coverage_simplify (E5).
import sys,json,numpy as np
sys.path.insert(0,'scripts/mapa-geral')
import vetorizar as v, cv2
from calibrar import merc, renderizar
cal=json.load(open(v.V2+'/calibracao.json'))['por_mapa']
terra,_=v.carregar_terra()
w=json.load(open(v.MUNDO))
def an(lista): return [np.stack([np.asarray(a,float)[:,0]+180, merc(80.0)-merc(np.asarray(a,float)[:,1])],1) for a in lista]
ta=an([a for f in w['fundo'] if f['tipo']=='terra' for a in f['aneis']]); la=an([f['pontos'] for f in w['fundo'] if f['tipo']=='mar'])
for k,rs in (('2053',[194,211,215]),('1137',[110]),('1805',[54])):
    p=cal[k]; reg=cv2.imread(v.V2+f'/rotulos/{k}.png',cv2.IMREAD_UNCHANGED).astype(np.int32); info=json.load(open(v.V2+f'/rotulos/{k}.json'))
    tpx=renderizar(ta,[],p['S'],p['X0'],p['Y0'])>0; lpx=renderizar(la,[],p['S'],p['X0'],p['Y0'])>0
    mask=(reg>0)&tpx&~lpx
    for tol,DESL in ((1.0,0.0),(1.0,0.5)):
        v.TOL_PX=tol
        f,_,_,_=v.vetorizar_mapa(reg.astype(np.uint16),info,p,terra,None)
        out=[]
        for r in rs:
            pol=[]
            for parte in v.partes(f[r]):
                for anel in [parte.exterior]+list(parte.interiors):
                    a=np.asarray(anel.coords); pol.append(np.round(np.stack([(a[:,0]+180)*p['S']-p['X0']-DESL,(merc(80.0)-merc(a[:,1]))*p['S']-p['Y0']-DESL],1)*16).astype(np.int32))
            t=np.zeros(reg.shape,np.uint8); cv2.fillPoly(t,pol,1,shift=4)
            A=(reg==r)&mask; B=(t>0)&mask
            out.append((r,int(A.sum()),round((A&B).sum()/max(1,(A|B).sum()),3)))
        print(k,tol,out)
