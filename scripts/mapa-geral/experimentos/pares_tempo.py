# Evidência temporal para os pares candidatos (E4 -> E7): nos mapas vizinhos (mesma calibração, pixels alinhados),
# os pixels dos dois pedaços caem numa região só (um estado) ou em duas regiões separadas por linha / cor diferente
# (dois estados). A evidência mais próxima no tempo decide.
import sys,json,cv2,numpy as np
sys.path.insert(0,'scripts/mapa-geral')
import cache
from calibrar import merc
V2='scripts/mapa-geral/.cache/v2/'
JAN=int(sys.argv[1]) if len(sys.argv)>1 else 30
mapas=json.load(open(V2+'mapas.json')); ordem=sorted(mapas,key=lambda k:mapas[k]['quadro'])
cal=json.load(open(V2+'calibracao.json'))['por_mapa']; anos=json.load(open(V2+'anos.json'))
et4=cache.Etapa('e4e'); memo={}
def R(k):
    if k not in memo:
        if len(memo)>80: memo.clear()
        memo[k]=(cv2.imread(et4.caminho(k,'.png'),cv2.IMREAD_UNCHANGED),json.load(open(et4.caminho(k,'.json'))))
    return memo[k]
def mesma_cal(a,b): return all(abs(cal[a][x]-cal[b][x])<1e-6 for x in ('S','X0','Y0'))
def evidencia(k,ra,rb):
    rot,d=R(k); A=rot==ra; B=rot==rb
    i=ordem.index(k)
    for passo in range(1,JAN+1):
        for j in (i-passo,i+passo):
            if not (0<=j<len(ordem)): continue
            k2=ordem[j]
            if not mesma_cal(k,k2): continue
            r2,d2=R(k2); tipo={q['r']:q for q in d2['regioes']}
            va,na=np.unique(r2[A],return_counts=True); vb,nb=np.unique(r2[B],return_counts=True)
            a2=int(va[na.argmax()]); b2=int(vb[nb.argmax()])
            fa=na.max()/A.sum(); fb=nb.max()/B.sum()
            if fa<0.8 or fb<0.8: continue
            if tipo.get(a2,{}).get('tipo')!='estado' or tipo.get(b2,{}).get('tipo')!='estado': continue
            if a2==b2: return 'um',k2,passo
            ca,cb=tipo[a2]['cor'],tipo[b2]['cor']
            if sum(abs(x-y) for x,y in zip(ca,cb))>20: return 'dois(cor)',k2,passo
            cs=[c for c in d2['candidatos'] if {c['r_a'],c['r_b']}=={a2,b2}]
            if not cs: return 'dois(linha)',k2,passo
            if max(c['fracao_linha'] for c in cs)>0.3: return 'dois(linha)',k2,passo
    return None,None,None
if __name__=='__main__':
    pares=json.load(open('scripts/mapa-geral/pares.json'))['pares']
    ok=err=sol=nada=0
    for pr in pares:
        k=str(anos[str(pr['ano'])]['mapa']); rot,_=R(k); p=cal[k]; rs=[]
        for lon,lat in (pr['ponto_a'],pr['ponto_b']):
            u=int(round((lon+180)*p['S']-p['X0'])); v=int(round((merc(80.0)-merc(lat))*p['S']-p['Y0'])); rs.append(int(rot[v,u]))
        if rs[0]==rs[1]: continue
        ev,k2,ps=evidencia(k,rs[0],rs[1])
        tag='ok' if (ev=='um')==pr['mesmo_estado'] and ev else ('--' if ev else '??')
        print(tag,pr['id_folha'],pr['mesmo_estado'],ev,k2,ps)
