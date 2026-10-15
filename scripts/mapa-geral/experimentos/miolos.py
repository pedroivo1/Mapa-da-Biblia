# Regiões pequenas cercadas por um único vizinho (sem contar pixels de letra/linha): estatísticas para a regra
# "miolo de letra" (E4e). Uso: python3 scripts/mapa-geral/experimentos/miolos.py id [id ...]
import sys,json,numpy as np,cv2
sys.path.insert(0,'scripts/mapa-geral')
import rotular as rt
V2=rt.V2
def cercadas(k, area_max=1000):
    reg=cv2.imread(V2+f'/rotulos/{k}.png',cv2.IMREAD_UNCHANGED).astype(np.int32)
    info=json.load(open(V2+f'/rotulos/{k}.json'))
    im=cv2.imread(V2+f'/mapas/{k}.png'); px=im[:,:,::-1].astype(np.int32)
    cor={r['r']:np.array(r['cor']) for r in info['regioes']}
    caixas=[c for r in info['regioes'] for c in r['texto']]
    out=[]
    k3=np.ones((3,3),np.uint8)
    for R in info['regioes']:
        if R['area_px']>=area_max: continue
        x0,y0,x1,y1=R['caixa']; x0,y0,x1,y1=max(0,x0-4),max(0,y0-4),min(1920,x1+5),min(960,y1+5)
        sub=reg[y0:y1,x0:x1]; m=(sub==R['r']).astype(np.uint8)
        anel=cv2.dilate(m,k3,iterations=2).astype(bool)&(m==0)
        viz=sub[anel]
        if (viz==0).any(): continue                  # toca o mar: ilha ou costa
        u,c=np.unique(viz,return_counts=True)
        dono=int(u[c.argmax()])
        # evidência de letra na faixa de 2 px em volta (cor de referência = vizinho dono) e por dentro da borda
        jan=px[y0:y1,x0:x1]
        let=rt.evidencia_letra(jan,np.broadcast_to(cor[dono],jan.shape))|rt.evidencia_letra(jan,np.broadcast_to(cor[R['r']],jan.shape))
        escuro=(jan.max(axis=2)<=0.6*cor[dono].max())   # contorno escuro das letras brancas
        borda_in=m.astype(bool)&~cv2.erode(m,k3).astype(bool)
        faixa=anel|borda_in
        frac_let=float((let|escuro)[faixa].mean())
        outros=[int(x) for x in u if x!=dono]
        frac_dono=float(c.max()/c.sum())
        cx,cy=(R['caixa'][0]+R['caixa'][2])//2,(R['caixa'][1]+R['caixa'][3])//2
        na_caixa=any(x<=cx<=x+w and y<=cy<=y+h for x,y,w,h in caixas)
        out.append(dict(r=R['r'],area=R['area_px'],cor=R['cor'],dono=dono,cor_dono=[int(v) for v in cor[dono]],frac_dono=round(frac_dono,2),outros=outros,letra=round(frac_let,2),caixa=na_caixa,dc=int(np.abs(cor[dono]-np.array(R['cor'])).sum())))
    return out
if __name__=='__main__':
    for k in sys.argv[1:]:
        for o in cercadas(k): print(k,o)
