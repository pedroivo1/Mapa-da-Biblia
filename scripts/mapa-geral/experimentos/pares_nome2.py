# Uniões da E7 (pares candidatos da E4) com a associação etiqueta -> região (nomear.associar). Avalia em pares.json.
import sys,json,cv2,numpy as np
sys.path.insert(0,'scripts/mapa-geral')
import cache, nomear
from calibrar import merc
V2='scripts/mapa-geral/.cache/v2/'
VAR=sys.argv[1]; P=json.loads(sys.argv[2]) if len(sys.argv)>2 else {}
LINHA=P.get('LINHA',0.1); L1=P.get('L1',0.5); L0=P.get('L0',0.7); COR=P.get('COR',20)
anos=json.load(open(V2+'anos.json')); cal=json.load(open(V2+'calibracao.json'))['por_mapa']
pares=json.load(open('scripts/mapa-geral/pares.json'))['pares']
et=cache.Etapa('e7a'); et4=cache.Etapa('e4e')
memo={}
def dados(k):
    if k not in memo:
        rot=cv2.imread(et4.caminho(k,'.png'),cv2.IMREAD_UNCHANGED); d=json.load(open(et4.caminho(k,'.json')))
        est={q['r'] for q in d['regioes'] if q['tipo']=='estado'}
        dono,resto=nomear.associar(json.load(open(et.caminho(k,'.json',VAR)))['caixas'],rot,est)
        memo[k]=(rot,d,dono)
    return memo[k]
def decidir(k,ra,rb):
    rot,d,dono=dados(k)
    cs=[c for c in d['candidatos'] if {c['r_a'],c['r_b']}=={ra,rb}]
    if not cs: return False,'sem candidato'
    c=max(cs,key=lambda c:c['fronteira_px'])
    linha=max(x['fracao_linha'] for x in cs); letra=c['fracao_letra']; dc=c['dif_cor']
    na,nb=dono.get(ra),dono.get(rb)
    ta,tb=(na['texto'] if na else None),(nb['texto'] if nb else None)
    mot=f'a={ta} b={tb} letra={letra} linha={linha} cor={dc}'
    if linha>LINHA or dc>COR: return False,mot
    if ta and tb: return nomear.normal(ta)==nomear.normal(tb),mot
    if ta or tb: return letra>=L1,mot
    return letra>=L0,mot
err=[];sol=[];n=0
for pr in pares:
    k=str(anos[str(pr['ano'])]['mapa'])
    if k not in et.itens(VAR): continue
    n+=1
    reg=cv2.imread(et4.caminho(k,'.png'),cv2.IMREAD_UNCHANGED); p=cal[k]; rs=[]
    for lon,lat in (pr['ponto_a'],pr['ponto_b']):
        u=int(round((lon+180)*p['S']-p['X0'])); v=int(round((merc(80.0)-merc(lat))*p['S']-p['Y0'])); rs.append(int(reg[v,u]))
    if rs[0]==rs[1]: un,mot=True,'E4'
    else: un,mot=decidir(k,rs[0],rs[1])
    if pr['mesmo_estado'] and not un: sol.append((pr['id_folha'],mot))
    if not pr['mesmo_estado'] and un: err.append((pr['id_folha'],mot))
print('pares',n,'erradas',len(err),'soltos',len(sol))
for x in err: print('  E',x)
for x in sol: print('  S',x)
