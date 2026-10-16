# pares.json depois das uniões da E7d (arquivo .cache/v2/e7/unioes-<var>.json): erradas e soltas.
import sys,json,cv2
sys.path.insert(0,'scripts/mapa-geral')
import cache
from calibrar import merc
V2='scripts/mapa-geral/.cache/v2/'
var=sys.argv[1]
U=json.load(open(V2+f'e7/unioes-{var}.json'))['mapas']
anos=json.load(open(V2+'anos.json')); cal=json.load(open(V2+'calibracao.json'))['por_mapa']
et4=cache.Etapa('e4e'); err=[]; sol=[]; n=0
for pr in json.load(open('scripts/mapa-geral/pares.json'))['pares']:
    k=str(anos[str(pr['ano'])]['mapa']); rot=cv2.imread(et4.caminho(k,'.png'),cv2.IMREAD_UNCHANGED); p=cal[k]; rs=[]
    for lon,lat in (pr['ponto_a'],pr['ponto_b']):
        u=int(round((lon+180)*p['S']-p['X0'])); v=int(round((merc(80.0)-merc(lat))*p['S']-p['Y0'])); rs.append(int(rot[v,u]))
    m={rb:ra for ra,rb,_ in U.get(k,[])}
    a,b=(m.get(r,r) for r in rs); n+=1
    if pr['mesmo_estado'] and a!=b: sol.append(pr['id_folha'])
    if not pr['mesmo_estado'] and a==b: err.append(pr['id_folha'])
print(f'pares {n}: uniões erradas {len(err)} {err}; pedaços soltos {len(sol)} de {sum(1 for p in json.load(open("scripts/mapa-geral/pares.json"))["pares"] if p["mesmo_estado"])}')
