# Por que uma entidade dura < 3 anos: para cada uma, a região no primeiro mapa dela e a região de maior sobreposição
# no mapa anterior (e no seguinte ao último), com cor, IoU e o id que essa região recebeu.
import sys,json,collections,numpy as np
sys.path.insert(0,'scripts/mapa-geral')
import rastrear as rs, cache as ca
V2=rs.V2
# uso: curtas_causa.py [variante da E6]  (os vetores vêm da fonte dessa variante: E5 ou E7u)
et6=ca.Etapa('e6'); VAR6=sys.argv[1] if len(sys.argv)>1 else et6.m['aprovada']
FONTE=et6.m['variantes'][VAR6]['params'].get('FONTE','e5'); etv=ca.Etapa(FONTE)
VARV=VAR6 if VAR6 in etv.m['variantes'] else etv.m['aprovada']
ent=json.load(open(et6.caminho('entidades','.json',VAR6))); anos=json.load(open(V2+'/anos.json'))
ordem=[int(a) for a in anos]; pos={a:i for i,a in enumerate(ordem)}
por=ent['por_ano']; idx={}
for i,c in enumerate(por): idx[(c[0],c[2])]=i
cache={}
def grade(k):
    if k not in cache:
        if len(cache)>40: cache.clear()
        v=json.load(open(etv.caminho(k,'.json',VARV))); cache[k]=(rs.rasterizar(v),v)
    return cache[k]
cat=collections.Counter(); ex=[]
curtas=[(e,d) for e,d in ent['entidades'].items() if pos[d['anos'][1]]-pos[d['anos'][0]]+1<3]
for e,d in curtas:
    a0,a1,k,rr=d['trechos'][0]
    i=idx[(a0,k)]
    res=[]
    for j in (i-1,i+1+len(d['trechos'])-1):
        if not 0<=j<len(por): res.append(None); continue
        g,v=grade(k); g2,v2=grade(por[j][2])
        m=np.isin(g,rr)
        if not m.any(): res.append(None); continue
        u,c=np.unique(g2[m],return_counts=True)
        best=None
        for r2,n in zip(u.tolist(),c.tolist()):
            if r2==0: continue
            iou=n/float(m.sum()+(g2==r2).sum()-n); dc=sum(abs(a-b) for a,b in zip(v['regioes'][str(rr[0])]['cor'],v2['regioes'][str(r2)]['cor']))
            if best is None or iou>best[0]: best=(round(iou,2),dc,por[j][3].get(str(r2)))
        res.append(best)
    p,n=res
    if p and p[1]<=60 and p[0]>=0.3: c='herdaria do anterior (fusão/divisão)'
    elif p and p[1]>60: c='cor diferente do anterior'
    else: c='sem sobreposição antes (estado novo)'
    cat[c]+=1
    if len(ex)<12: ex.append((e,d['anos'],p,n,c))
print(cat); [print(x) for x in ex]
