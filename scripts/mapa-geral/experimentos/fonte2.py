# Ranking de fontes nos rótulos grandes do mapa 2053 (1799).
import sys,os,glob,cv2,numpy as np
sys.path.insert(0,'scripts/mapa-geral/experimentos')
import texto_det2 as td, reconhecer as rc
im=cv2.imread('scripts/mapa-geral/.cache/v2/mapas/2053.png')
cx=[a for a in td.detectar(im) if a[4]>=11 and a[3]>=40]
GT={0:'Russian America',6:'Philippines',8:'Joseon',10:'New Spain',11:"Rupert's Land",18:'North Greenland',24:'Diriyah',25:'Qajars',26:'Khiva',27:'Kazakhs',29:'Russia',31:'Qing',32:'Siam'}
fontes=[os.path.expanduser('~/.cache/mapa-biblia-lib/fontes/'+f) for f in sys.argv[1:]]
res=[]
for f in fontes:
    rc.FONTE=f; rc._fontes.clear(); rc._rend.clear(); sc=[]
    for i,g in GT.items():
        n,x,y,w,h=cx[i]; P=6; ink=rc.tinta(im[y-P:y+h+P,x-P:x+w+P],n=='claro')
        base=h; tams=[t/2 for t in range(int(base*0.8*2),int(base*2.0*2))]
        sc.append(max(rc.nota_margem(ink,g,t) for t in tams))
    res.append((float(np.mean(sc)),os.path.basename(f),[round(s,2) for s in sc]))
for r in sorted(res,reverse=True): print(round(r[0],3),r[1],r[2])
