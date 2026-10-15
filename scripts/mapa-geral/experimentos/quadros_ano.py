# Para um intervalo de quadros: discordância de terra de cada quadro com a calibração de cada trecho longo, e
# mudança em relação ao quadro anterior. Uso: python3 .../quadros_ano.py i0 i1
import sys,os,json,subprocess,glob,numpy as np,cv2
sys.path.insert(0,'scripts/mapa-geral')
import calibrar as c
V2=c.V2
i0,i1=int(sys.argv[1]),int(sys.argv[2])
cal=json.load(open(V2+'/calibracao.json'))
longos=[t for t in cal['trechos'] if t['n']>=20]
terra,lagos=c.carregar_mundo()
rend={t['S']:c.renderizar(terra,lagos,t['S'],t['X0'],t['Y0'])>0 for t in longos}
video=glob.glob('vídeos/*hzWwp9JM7Hw*.webm')[0]
fps=30000/1001
b=subprocess.run(['ffmpeg','-v','error','-ss',f'{(i0-0.5)/fps:.4f}','-i',video,'-frames:v',str(i1-i0+1),'-f','rawvideo','-pix_fmt','bgr24','-'],capture_output=True).stdout
n=len(b)//(960*1920*3); prev=None
for j in range(n):
    f=np.frombuffer(b[j*960*1920*3:(j+1)*960*1920*3],np.uint8).reshape(960,1920,3)
    tv,val=c.mascara_terra(f)
    res={}
    for S,r in rend.items():
        y0,y1=c.regiao_valida(S,[t for t in longos if t['S']==S][0]['Y0'])
        res[S]=round(float(((r[y0:y1]!=(tv[y0:y1]>0))&(val[y0:y1]>0)).mean()),4)
    best=min(res,key=res.get)
    d=int((np.abs(f.astype(int)-prev).max(2)>12).sum()) if prev is not None else -1
    print(i0+j,'melhor trecho S',best,res[best],'mudança',d)
    prev=f.astype(int)
