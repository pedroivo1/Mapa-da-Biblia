import sys,os,json; sys.path.insert(0,'scripts/mapa-geral')
import cv2, numpy as np
V2='scripts/mapa-geral/.cache/v2/'
T='/tmp/claude-1000/-data-Documents-Programing-Mapa-da-Biblia/ed6218b9-c80c-4986-8a8a-3f15c2c0664b/scratchpad/'
anos=json.load(open(V2+'anos.json'))
def run(ano,thr=8):
    k=anos[str(ano)]['mapa']; im=cv2.imread(f'{V2}mapas/{k}.png')
    f=im.astype(np.int16)
    gx=np.abs(f[:,1:]-f[:,:-1]).max(2); gy=np.abs(f[1:,:]-f[:-1,:]).max(2)
    edge=np.zeros(im.shape[:2],bool)
    edge[:,1:]|=gx>thr; edge[:,:-1]|=gx>thr; edge[1:,:]|=gy>thr; edge[:-1,:]|=gy>thr
    flat=(~edge).astype(np.uint8)
    n,lab,st,_=cv2.connectedComponentsWithStats(flat,connectivity=4)
    big=[i for i in range(1,n) if st[i,cv2.CC_STAT_AREA]>=400]
    print(ano,'componentes',n,'>=400px',len(big))
    rng=np.random.RandomState(1); pal=rng.randint(40,255,(n+1,3)).astype(np.uint8)
    out=pal[lab]; out[edge]=0
    for i in range(1,n):
        if st[i,cv2.CC_STAT_AREA]<400: out[lab==i]=0
    cv2.imwrite(T+f'flat{ano}.png',np.hstack([im,out])[:, :])
for a in (584,-999): run(a)
