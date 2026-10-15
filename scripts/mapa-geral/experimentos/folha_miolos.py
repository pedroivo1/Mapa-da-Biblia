# Folha: regiões absorvidas como miolo de letra (uniões tipo "miolo") e enclaves que ficaram, numa amostra.
# Uso: python3 scripts/mapa-geral/experimentos/folha_miolos.py rapida|media
import sys,json,numpy as np,cv2
V2='scripts/mapa-geral/.cache/v2/'
am=sys.argv[1]
ids=json.load(open('scripts/mapa-geral/amostras.json'))[am]['ids']
def cel(k,caixa,pasta,r,txt,dono=None):
    im=cv2.imread(V2+f'mapas/{k}.png'); reg=cv2.imread(V2+f'{pasta}/{k}.png',cv2.IMREAD_UNCHANGED)
    x0,y0,x1,y1=caixa; cx,cy=(x0+x1)//2,(y0+y1)//2; h=max(22,(x1-x0)//2+10,(y1-y0)//2+10)
    xa,ya,xb,yb=max(0,cx-h),max(0,cy-h),min(1920,cx+h),min(960,cy+h)
    c=im[ya:yb,xa:xb].copy()
    if r: 
        m=(reg[ya:yb,xa:xb]==r).astype(np.uint8)
        e=m.astype(bool)&~cv2.erode(m,np.ones((3,3),np.uint8)).astype(bool); c[e]=(0,255,0)
    else:
        cv2.rectangle(c,(x0-xa-1,y0-ya-1),(x1-xa+1,y1-ya+1),(255,0,255),1)
    if dono:
        rd=cv2.imread(V2+f'{dono[1]}/{k}.png',cv2.IMREAD_UNCHANGED)
        md=(rd[ya:yb,xa:xb]==dono[0]).astype(np.uint8)
        ed=md.astype(bool)&~cv2.erode(md,np.ones((3,3),np.uint8)).astype(bool); c[ed]=(255,0,255)
        if r:
            m=(cv2.imread(V2+f'{pasta}/{k}.png',cv2.IMREAD_UNCHANGED)[ya:yb,xa:xb]==r).astype(np.uint8)
            e=m.astype(bool)&~cv2.erode(m,np.ones((3,3),np.uint8)).astype(bool); c[e]=(0,255,0)
    c=cv2.resize(c,(140,140),interpolation=cv2.INTER_NEAREST)
    cv2.putText(c,txt,(2,12),cv2.FONT_HERSHEY_SIMPLEX,0.38,(0,0,255),1); return c
abs_,enc=[],[]
for k in ids:
    j=json.load(open(V2+f'rotulos/{k}.json'))
    for u in j['unioes']:
        if u['tipo']=='miolo':
            # verde = a região absorvida (rótulo de antes, no ponto interior); magenta = o dono (rótulo final)
            ra=int(cv2.imread(V2+f'antes-miolo/{k}.png',cv2.IMREAD_UNCHANGED)[u['ponto'][1],u['ponto'][0]])
            c=cel(k,u['caixa_menor'],'antes-miolo',ra,f"{k} {u['motivo'][0]} L{u['fracao_letra']} l{u['fracao_linha']} c{u['dif_cor']}",dono=(u['r'],'rotulos'))
            abs_.append(c)
    for e in j.get('enclaves',[]):
        enc.append(cel(k,e['caixa'],'rotulos',e['r'],f"{k} L{e['fracao_letra']} c{e['dif_cor']}"))
def folha(cs,nome):
    if not cs: return
    lin=[]
    for i in range(0,len(cs),10):
        f=cs[i:i+10]
        while len(f)<10: f.append(np.full_like(cs[0],255))
        lin.append(np.hstack(f))
    for n,i in enumerate(range(0,len(lin),8)):
        cv2.imwrite(V2+f'revisao/{nome}-{n+1}.png',np.vstack(lin[i:i+8]))
folha(abs_,f'miolos-absorvidos-{am}'); folha(enc,f'enclaves-{am}')
print('absorvidos',len(abs_),'enclaves',len(enc))
