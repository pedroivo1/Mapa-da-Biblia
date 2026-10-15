import sys,os,json; sys.path.insert(0,'scripts/mapa-geral')
import calibrar as c, cv2, numpy as np
cal=json.load(open(c.V2+'/calibracao.json'))['por_mapa']
terra,lagos=c.carregar_mundo()
def render(S,X0,Y0,R):
    # mesma transformação, mas y escalado por R
    img=np.zeros((960,1920),np.uint8)
    for k in (-1,0,1):
        pol=[]
        for a in terra:
            x=(a[:,0]+360*k)*S-X0
            if x.max()<-2 or x.min()>1922: continue
            pol.append(np.round(np.stack([x,a[:,1]*S*R-Y0],1)*16).astype(np.int32))
        if pol:
            t=np.zeros_like(img); cv2.fillPoly(t,pol,255,shift=4); img=cv2.bitwise_xor(img,t)
    pol=[np.round(np.stack([(a[:,0]+360*k)*S-X0,a[:,1]*S*R-Y0],1)*16).astype(np.int32) for a in lagos for k in (-1,0,1)]
    cv2.fillPoly(img,pol,0,shift=4)
    return img
for k in sys.argv[1:]:
    p=cal[k]; im=cv2.imread(f'{c.V2}/mapas/{k}.png'); tv,val=c.mascara_terra(im)
    def cu(q):
        r=render(*q); y0,y1=100,860
        return int(((r[y0:y1]!=tv[y0:y1])&(val[y0:y1]>0)).sum())
    q=[p['S'],p['X0'],p['Y0'],1.0]; cb=cu(q); st=[0.003*q[0],2.0,2.0,0.002]
    while st[1]>0.05:
        imp=True
        while imp:
            imp=False
            for i in range(4):
                for s in (1,-1):
                    z=list(q); z[i]+=s*st[i]; cz=cu(z)
                    if cz<cb: q,cb,imp=z,cz,True; break
        st=[x/2 for x in st]
    print(k,'iso',cu([p['S'],p['X0'],p['Y0'],1.0]),'aniso',cb,[round(x,4) for x in q])
