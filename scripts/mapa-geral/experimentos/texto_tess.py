import sys,json,numpy as np,cv2,subprocess,tempfile,os,time
V2='scripts/mapa-geral/.cache/v2/'
def camada(im):
    g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
    k=cv2.getStructuringElement(cv2.MORPH_RECT,(15,15))
    bh=cv2.morphologyEx(g,cv2.MORPH_BLACKHAT,k); th=cv2.morphologyEx(g,cv2.MORPH_TOPHAT,k)
    tinta=np.zeros(g.shape,np.uint8)
    for m,cond in ((bh,g<=125),(th,g>=195)):
        b=((m>40)&cond).astype(np.uint8)
        n,lab,st,_=cv2.connectedComponentsWithStats(b,connectivity=8)
        keep=np.zeros(n,bool)
        for i in range(1,n):
            x,y,w,h,a=st[i]
            if 3<=h<=40 and w<=60 and a>=4 and a<=0.9*w*h+5: keep[i]=True
        # intensidade proporcional ao contraste (antialias preservada)
        tinta=np.maximum(tinta,np.where(keep[lab],np.clip(m.astype(int)*2,0,255),0).astype(np.uint8))
    return 255-tinta
def ocr(img,psm=11):
    with tempfile.TemporaryDirectory() as d:
        p=os.path.join(d,'t.png'); cv2.imwrite(p,img)
        r=subprocess.run(['tesseract',p,'-','--psm',str(psm),'-l','eng','tsv'],capture_output=True,text=True).stdout
    out=[]
    for l in r.splitlines()[1:]:
        f=l.split('\t')
        if len(f)==12 and f[11].strip() and float(f[10])>=0: out.append((int(f[6]),int(f[7]),int(f[8]),int(f[9]),float(f[10]),f[11]))
    return out
if __name__=='__main__':
    k=sys.argv[1]; im=cv2.imread(V2+f'mapas/{k}.png')
    c=camada(im); E=2
    t=time.time(); ws=ocr(cv2.resize(c,None,fx=E,fy=E,interpolation=cv2.INTER_CUBIC)); print('ocr',time.time()-t,len(ws))
    o=im.copy()
    for x,y,w,h,conf,tx in ws:
        x,y,w,h=x//E,y//E,w//E,h//E
        cor=(0,0,255) if conf>=60 else (200,200,0)
        cv2.rectangle(o,(x,y),(x+w,y+h),cor,1)
    cv2.imwrite(f'/tmp/claude-1000/-data-Documents-Programing-Mapa-da-Biblia/ed6218b9-c80c-4986-8a8a-3f15c2c0664b/scratchpad/tess{k}.png',o)
    cv2.imwrite(f'/tmp/claude-1000/-data-Documents-Programing-Mapa-da-Biblia/ed6218b9-c80c-4986-8a8a-3f15c2c0664b/scratchpad/camada{k}.png',c)
    print(sorted([(tx,round(conf)) for x,y,w,h,conf,tx in ws if conf>=60])[:200])
