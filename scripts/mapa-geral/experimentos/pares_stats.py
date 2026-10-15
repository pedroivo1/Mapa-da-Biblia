# Estatísticas de todos os pares vizinhos de mesma cor ANTES das uniões, com folha para rotular à mão.
import sys,json,numpy as np,os,cv2
sys.path.insert(0,'scripts/mapa-geral')
import rotular as r
src=open('scripts/mapa-geral/rotular.py').read()
src=src.replace("    pai = {}\n","    DEP['pares']=pares; DEP['ws0']=ws.copy(); DEP['cor']={v: cores[i] for i, v in nova.items()}\n    pai = {}\n",1)
g={'__name__':'dep','DEP':{},'__file__':os.path.abspath('scripts/mapa-geral/rotular.py')}
exec(compile(src,'rot','exec'),g)
anos=json.load(open(r.V2+'/anos.json'))
saida=[]; cel=[]
for ano in [int(a) for a in sys.argv[1:]]:
    k=str(anos[str(ano)]['mapa']); im=cv2.imread(r.V2+f'/mapas/{k}.png')
    g['rotular_mapa'](im,None); D=g['DEP']; ws=D['ws0']
    area=np.bincount(np.maximum(ws,0).ravel())
    for kk,(tot,tt,ff,ll) in D['pares'].items():
        a,b=divmod(kk,100000)
        if a not in D['cor'] or b not in D['cor']: continue
        dc=int(np.abs(D['cor'][a]-D['cor'][b]).sum())
        if dc>20 or tot<2: continue
        fr=np.zeros(ws.shape,bool)
        fr[:,1:]|=((ws[:,1:]==a)&(ws[:,:-1]==b))|((ws[:,1:]==b)&(ws[:,:-1]==a))
        fr[1:]|=((ws[1:]==a)&(ws[:-1]==b))|((ws[1:]==b)&(ws[:-1]==a))
        fy,fx=np.where(fr); cx,cy=int(np.median(fx)),int(np.median(fy))
        mn=min(area[a],area[b])
        i=len(saida)
        saida.append(dict(i=i,ano=ano,a=int(a),b=int(b),tot=int(tot),letra=round(tt/tot,3),preench=round(ff/tot,3),linha=round(ll/tot,3),outro=round((tot-tt-ff)/tot,3),menor=int(mn),claro=bool(min(D['cor'][a].min(),D['cor'][b].min())>=200),dc=dc))
        meia=40; xa,ya,xb,yb=max(0,cx-meia),max(0,cy-meia),min(1920,cx+meia),min(960,cy+meia)
        o=im[ya:yb,xa:xb].copy(); o2=o.copy()
        for v,c in ((a,(0,0,255)),(b,(255,0,255))):
            mv=(ws==v).astype(np.uint8); e=mv.astype(bool)&~cv2.erode(mv,np.ones((3,3),np.uint8)).astype(bool); o2[e[ya:yb,xa:xb]]=c
        o2[fr[ya:yb,xa:xb]]=(0,255,0)
        c=np.hstack([cv2.resize(o,(180,180),interpolation=cv2.INTER_NEAREST),cv2.resize(o2,(180,180),interpolation=cv2.INTER_NEAREST)])
        cv2.putText(c,f"#{i} L{tt/tot:.2f} P{ff/tot:.2f} O{(tot-tt-ff)/tot:.2f} n{tot}",(2,13),cv2.FONT_HERSHEY_SIMPLEX,0.45,(0,0,200),1)
        amb = not ((tt/tot>=0.9 and (tot-tt-ff)/tot<=0.1) or (tt+ff)/tot<0.5)
        if amb: cel.append(cv2.resize(c,(480,240),interpolation=cv2.INTER_NEAREST))
json.dump(saida,open(r.V2+'/pares-stats.json','w'))
linhas=[]
for i in range(0,len(cel),3):
    f=cel[i:i+3]
    while len(f)<3: f.append(np.full_like(cel[0],255))
    linhas.append(np.hstack(f))
for n,i in enumerate(range(0,len(linhas),5)):
    cv2.imwrite(r.V2+f'/revisao/pares-amb-{n+1}.png',np.vstack(linhas[i:i+5]))
print(len(saida),'pares;',len(cel),'ambíguos;',(len(linhas)+4)//5,'folhas')
