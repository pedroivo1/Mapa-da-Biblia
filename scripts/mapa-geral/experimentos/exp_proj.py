import sys,os,json; sys.path.insert(0,'scripts/mapa-geral')
import calibrar as c, numpy as np, cv2
d=json.load(open(c.MUNDO))
aneis=[np.asarray(a,float) for f in d['fundo'] if f['tipo']=='terra' for a in f['aneis']]
lagos=[np.asarray(f['pontos'],float) for f in d['fundo'] if f['tipo']=='mar']
def mk(yf):
    def prep(a): return np.stack([a[:,0]+180.0, yf(80.0)-yf(a[:,1])],1)
    return [prep(a) for a in aneis],[prep(a) for a in lagos]
proj={
 'mercator': lambda lat: c.merc(lat),
 'miller': lambda lat: 1.25*np.degrees(np.log(np.tan(np.pi/4+0.4*np.radians(lat)))),
 'equirect': lambda lat: np.asarray(lat,float),
 'gall': lambda lat: np.degrees(np.sin(np.radians(lat)))*0+ (1+np.sqrt(2)/2)*np.degrees(np.tan(np.radians(lat)/2)),
}
def fit(terra,lagos,tv,val,p0):
    # custo com y0 fixo da projeção; regiao valida: linhas 120..900
    def cu(p):
        S,X0,Y0,sy=p
        img=np.zeros((960,1920),np.uint8)
        for k in (-1,0,1):
            pol=[]
            for a in terra:
                x=(a[:,0]+360*k)*S-X0
                if x.max()<-2 or x.min()>1922: continue
                pol.append(np.round(np.stack([x,a[:,1]*S*sy-Y0],1)*16).astype(np.int32))
            if pol:
                t=np.zeros_like(img); cv2.fillPoly(t,pol,255,shift=4); img=cv2.bitwise_xor(img,t)
        pol=[np.round(np.stack([(a[:,0]+360*k)*S-X0,a[:,1]*S*sy-Y0],1)*16).astype(np.int32) for a in lagos for k in (-1,0,1)]
        cv2.fillPoly(img,pol,0,shift=4)
        dif=(img[100:800]!=tv[100:800])&(val[100:800]>0)
        return dif.sum()
    p=list(p0); cbest=cu(p); steps=[0.01*p[0],8,8,0.01]
    while steps[1]>0.1:
        imp=True
        while imp:
            imp=False
            for i in range(4):
                for s in (1,-1):
                    q=list(p); q[i]+=s*steps[i]; cq=cu(q)
                    if cq<cbest-0.5: p,cbest,imp=q,cq,True; break
        steps=[x/2 for x in steps]
    return p,cbest
for mid,(S,X0,Y0) in ((647,(12.6,2096.06,868.94)),(2285,(5.3981,26.34,133.09))):
    im=cv2.imread(c.V2+f'/mapas/{mid}.png'); tv,val=c.mascara_terra(im)
    for nome,yf in proj.items():
        terra,lg=mk(yf)
        # escala y inicial: converte unidades mercator->unidades da projeção por lat média
        p,cb=fit(terra,lg,tv,val,[S,X0,Y0,1.0])
        print(mid,nome,[round(x,4) for x in p],int(cb),flush=True)
