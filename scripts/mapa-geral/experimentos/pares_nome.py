# Uniões pela etiqueta (E7): um par candidato (mesma cor, sem linha) cuja etiqueta passa pelos dois pedaços e que não
# tem etiqueta própria em cada um é o mesmo estado. Avalia em pares.json com os textos (E7a) de uma variante.
import sys,json,cv2,numpy as np
sys.path.insert(0,'scripts/mapa-geral')
import cache
from calibrar import merc
V2='scripts/mapa-geral/.cache/v2/'
VAR=sys.argv[1] if len(sys.argv)>1 else None
NOTA=0.55; SPAN=float(sys.argv[2]) if len(sys.argv)>2 else 0.1; LINHA=0.1
anos=json.load(open(V2+'anos.json')); cal=json.load(open(V2+'calibracao.json'))['por_mapa']
P=json.load(open('scripts/mapa-geral/pares.json'))['pares']
et=cache.Etapa('e7a')
def fracoes(caixas,rot,estados):
    out=[]
    for c in caixas:
        if not c[6] or c[6][0][1]<NOTA: continue
        t,x,y,w,h=c[:5]; sub=rot[y:y+h,x:x+w]; v,n=np.unique(sub,return_counts=True)
        out.append(({int(a):int(b)/sub.size for a,b in zip(v,n) if int(a) in estados},c[6][0][0]))
    return out
def decidir(k,ra,rb,cache_={}):
    if k not in cache_:
        rot=cv2.imread(V2+f'rotulos/{k}.png',cv2.IMREAD_UNCHANGED); d=json.load(open(V2+f'rotulos/{k}.json'))
        est={r['r'] for r in d['regioes'] if r['tipo']=='estado'}
        cache_[k]=(fracoes(json.load(open(et.caminho(k,'.json',VAR)))['caixas'],rot,est),d)
    fr,d=cache_[k]
    cs=[c for c in d['candidatos'] if {c['r_a'],c['r_b']}=={ra,rb}]
    if not cs: return False,'sem candidato'
    linha=max(c['fracao_linha'] for c in cs)
    span=[t for f,t in fr if f.get(ra,0)>=SPAN and f.get(rb,0)>=SPAN]
    own_a=[t for f,t in fr if f.get(ra,0)>=0.5 and f.get(rb,0)<SPAN]
    own_b=[t for f,t in fr if f.get(rb,0)>=0.5 and f.get(ra,0)<SPAN]
    un= bool(span) and not (own_a and own_b) and linha<=LINHA
    return un,f'span={span} a={own_a} b={own_b} linha={linha}'
err=[];sol=[]
for pr in P:
    k=str(anos[str(pr['ano'])]['mapa'])
    if k not in et.itens(VAR or et.m['aprovada']): continue
    reg=cv2.imread(V2+f'rotulos/{k}.png',cv2.IMREAD_UNCHANGED); p=cal[k]; rs=[]
    for lon,lat in (pr['ponto_a'],pr['ponto_b']):
        u=int(round((lon+180)*p['S']-p['X0'])); v=int(round((merc(80.0)-merc(lat))*p['S']-p['Y0'])); rs.append(int(reg[v,u]))
    if rs[0]==rs[1]: un,mot=True,'E4'
    else: un,mot=decidir(k,rs[0],rs[1])
    if pr['mesmo_estado'] and not un: sol.append((pr['id_folha'],mot))
    if not pr['mesmo_estado'] and un: err.append((pr['id_folha'],mot))
print('erradas',len(err)); [print('  ',x) for x in err]
print('soltos',len(sol)); [print('  ',x) for x in sol]
