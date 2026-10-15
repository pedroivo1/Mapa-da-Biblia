import sys,os,json; sys.path.insert(0,'scripts/mapa-geral')
import calibrar as c, cv2, numpy as np
V2=c.V2
anos=json.load(open(V2+'/anos.json')); cal=json.load(open(V2+'/calibracao.json'))['por_mapa']
def marcar(ano, pts, saida):
    a=anos[str(ano)]; k=str(a['mapa']); p=cal[k]
    im=cv2.imread(f'{V2}/mapas/{k}.png')
    for i,(lon,lat) in enumerate(pts):
        u=(lon+180)*p['S']-p['X0']; v=(c.merc(80.0)-c.merc(lat))*p['S']-p['Y0']
        ui,vi=int(round(float(u))),int(round(float(v)))
        cv2.circle(im,(ui,vi),6,(0,0,255),2); cv2.putText(im,str(i),(ui+8,vi-8),cv2.FONT_HERSHEY_SIMPLEX,0.9,(0,0,255),2)
    cv2.imwrite(saida,im)
if __name__=='__main__':
    ano=int(sys.argv[1]); pts=json.loads(sys.argv[2]); marcar(ano,pts,sys.argv[3])
