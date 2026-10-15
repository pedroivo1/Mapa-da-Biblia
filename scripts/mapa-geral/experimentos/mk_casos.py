import sys,os,json; sys.path.insert(0,'scripts/mapa-geral')
import calibrar as c, cv2, numpy as np
V2=c.V2
anos=json.load(open(V2+'/anos.json')); cal=json.load(open(V2+'/calibracao.json'))['por_mapa']
def inv(ano,x,y):
    p=cal[str(anos[str(ano)]['mapa'])]
    lon=(x+p['X0'])/p['S']-180
    ym=c.merc(80.0)-(y+p['Y0'])/p['S']
    # inverte Miller: ym = 1.25*deg(ln tan(pi/4+0.4*lat))
    import math
    t=math.exp(math.radians(ym/1.25)); lat=math.degrees((math.atan(t)-math.pi/4)/0.4)
    return round(lon,2),round(lat,2)
# (ano, tipo_entrada, a, b, espera, nome_video, nome, cor_aprox)  tipo_entrada: 'px' ou 'll'
L=[]
def px(ano,x,y,esp,nv,nm,cor,creme=False,outra_ponta=False): L.append((ano,'px',x,y,esp,nv,nm,cor,(creme,outra_ponta)))
def ll(ano,lon,lat,esp,nv,nm,cor,creme=False,outra_ponta=False): L.append((ano,'ll',lon,lat,esp,nv,nm,cor,(creme,outra_ponta)))
# 1200 a.C.
px(1200,310,520,'estado','Egypt','Egito','#f7d95a')
px(1200,530,322,'estado','Assyria','Assíria','#3a74a3')
px(1200,560,400,'estado','Babylon','Babilônia','#ee6a5a')
px(1200,660,470,'estado','Elam','Elão','#4cb866')
px(1200,1740,400,'estado','Shang','Shang','#b03025')
px(1200,383,420,'estado','Israelites','Israelitas','#8fb9e0')
px(1200,160,285,'estado','Mycenae','Micenas','#3b6db3')
px(1200,262,306,'estado','Lydia','Lídia','#f5b45a')
px(1200,330,300,'estado','Phrygia','Frígia','#fdf8ee',True)
px(1200,500,665,'estado','Saba','Sabá','#fdf8ee',True)
px(1200,900,300,'sem-dono','','','#ffffff')
px(1200,100,350,'mar','','','#d8e1ed')
# 584 a.C.
px(584,730,460,'estado','Babylon','Babilônia','#e8685a')
px(584,880,500,'estado','Medes','Medos','#2f9e5a')
px(584,545,368,'estado','Lydia','Lídia','#f5b45a')
px(584,580,550,'estado','Egypt','Egito','#f7d95a')
px(584,580,656,'estado','Kush','Cuxe','#fef8ee',True)
px(584,1650,440,'estado','Zhou','Zhou','#a6282a')
px(584,1560,455,'estado','Chu','Chu','#2a67ab')
px(584,1150,600,'estado','Mahajanapadas','Mahajanapadas','#6aa3da')
px(584,300,290,'estado','Etruscans','Etruscos','#f4a6c6')
px(584,645,668,'estado','D\'mt','Damot','#e8897a')
px(584,486,822,'sem-dono','','','#ffffff')
px(584,400,430,'mar','','','#d8e1ed')
ll(584,52,36,'estado','Medes','Medos','#2f9e5a')
# 31 d.C. (ano -31)
px(-31,150,260,'estado','Roman Empire','Império Romano','#8a2320')
px(-31,110,350,'estado','Roman Empire','Império Romano','#8a2320')
px(-31,900,520,'estado','Parthian Empire','Império Parta','#4cb866')
px(-31,1000,430,'estado','Indo-Parthia','Indo-Pártia','#8ba4bd')
px(-31,1050,400,'estado','Kushans','Cuchanas','#fdb54a')
px(-31,1130,500,'estado','Indo-Scythia','Indo-Cítia','#efc57c')
px(-31,1170,590,'estado','Satavahana','Satavahana','#dc6e72')
px(-31,1300,592,'estado','Samatata','Samatata','#6560a8')
px(-31,1600,520,'estado','Han','Han','#b02e25')
px(-31,645,670,'estado','Axum','Axum','#e8897a')
px(-31,1795,325,'estado','Goguryeo','Goguryeo','#4a8a90')
px(-31,1000,800,'mar','','','#d8e1ed')
px(-31,1550,250,'sem-dono','','','#ffffff')
# 326 d.C. (ano -326)
px(-326,180,280,'estado','Roman Empire','Império Romano','#8a2320')
px(-326,900,520,'estado','Sasanian Empire','Império Sassânida','#4cb866')
px(-326,1590,560,'estado','Jin','Jin','#b02e25')
px(-326,1290,592,'estado','Gupta','Gupta','#4a4d8f')
px(-326,1160,600,'estado','Vakataka','Vacataca','#dc6e72')
px(-326,640,695,'estado','Axum','Axum','#e8897a')
px(-326,1790,375,'estado','Goguryeo','Goguryeo','#4a8a90')
px(-326,30,700,'estado','Ghana','Gana','#f5c27a')
px(-326,1500,740,'estado','Funan','Funan','#8a5a99')
px(-326,1167,712,'estado','Pallava','Pallava','#f07a30')
px(-326,300,700,'sem-dono','','','#ffffff')
px(-326,1000,800,'mar','','','#d8e1ed')
# 999 d.C.
ll(-999,10,50,'estado','Holy Roman Empire','Sacro Império Romano-Germânico','#4a4d57')
ll(-999,32,39,'estado','Byzantine Empire','Império Bizantino','#5c3d7a')
ll(-999,72,42,'estado','Qarakhanids','Caracânidas','#fdf8ee',True)
ll(-999,113,30,'estado','Song','Song','#b02e25',False)
px(-999,1300,325,'estado','Qocho','Qocho','#fdf8ee',True)
px(-999,1150,410,'estado','Yutian','Yutian','#fdf8ee',True)
px(-999,330,280,'estado','France','França','#3a6cb0')
px(-999,1500,320,'estado','Liao','Liao','#efc55c')
px(-999,1300,500,'estado','Tibetan Kingdoms','Reinos Tibetanos','#6a8cc4')
px(-999,960,500,'estado','Ghaznavids','Gaznévidas','#bfaea3')
px(-999,800,470,'estado','Buyids','Buídas','#4cb866')
px(-999,650,520,'estado','Fatimids','Fatímidas','#f7d95a')
px(-999,1160,725,'estado','Chola','Chola','#f07a30')
px(-999,1430,720,'estado','Khmers','Khmer','#7a4f8a')
px(-999,700,220,'estado','Kievan Rus\'','Rus de Kiev','#8ea5bf')
px(-999,1730,480,'estado','Japan','Japão','#4a505c')
px(-999,205,665,'estado','Ghana','Gana','#f5c27a')
px(-999,300,560,'sem-dono','','','#ffffff')
px(-999,200,200,'mar','','','#d8e1ed')
# 1598 d.C.
px(-1598,1130,405,'estado','Ottomans','Otomanos','#3d6e70')
px(-1598,1200,160,'estado','Russia','Rússia','#e8bb42')
px(-1598,1650,470,'estado','Ming','Ming','#b02e25')
px(-1598,1420,510,'estado','Mughals','Mogóis','#3d6a50')
px(-1598,1280,420,'estado','Safavids','Safávidas','#4cb866')
px(-1598,890,330,'estado','France','França','#3a6cb0')
px(-1598,600,740,'estado','Brazil','Brasil','#f4a23a')
px(-1598,830,470,'estado','Saadis','Saadianos','#c8412a')
px(-1598,1700,300,'estado','Northern Yuan','Yuan do Norte','#0e4a8a')
px(-1598,1020,650,'sem-dono','','','#ffffff')
px(-1598,500,300,'mar','','','#d8e1ed')
# 1799, 1914, 2022
ll(-1799,33,39,'estado','Ottomans','Otomanos','#3d6e70')
ll(-1799,90,60,'estado','Russia','Rússia','#e8bb42')
px(-1799,100,235,'estado','Russian America','América Russa','#e8bb42')
px(-1799,8,195,'estado','Russia','Rússia (Tchukotka, outra ponta do quadro)','#e8bb42',outra_ponta=True)
px(-1799,320,280,'estado','Rupert\'s Land','Terra de Rupert','#e5334f')
ll(-1799,-50,-10,'estado','Brazil','Brasil','#4ab07a')
px(-1799,393,485,'estado','New Spain','Nova Espanha','#f4a23a')
px(-1799,333,462,'estado','New Spain','Nova Espanha (Baja Califórnia)','#f4a23a')
px(-1799,504,462,'estado','New Spain','Nova Espanha (Flórida)','#f4a23a')
px(-1799,544,591,'estado','New Granada','Nova Granada','#f4a23a')
px(-1799,517,498,'estado','Cuba','Cuba','#f4a23a')
px(-1799,527,519,'estado','Jamaica','Jamaica','#e5334f')
px(-1914,1500,260,'estado','Russia','Rússia','#e8bb42')
px(-1914,250,230,'estado','Canada','Canadá','#e5334f')
px(-1914,400,400,'estado','United States','Estados Unidos','#3f51a6')
px(-1914,1670,780,'estado','Australia','Austrália','#e5334f')
px(-1914,720,100,'estado','North Greenland','Groenlândia do Norte','#9bbfe0')
px(-1914,300,880,'mar','','','#d8e1ed')
px(-2022,1500,430,'estado','China','China','#b02e25')
px(-2022,1380,500,'estado','India','Índia','#3a7fc4')
px(-2022,1100,530,'estado','Sudan','Sudão','#fdf8ee',True)
px(-2022,730,100,'estado','Greenland','Groenlândia','#9bbfe0')
px(-2022,670,690,'estado','Brazil','Brasil','#4ab07a')
px(-2022,1650,780,'estado','Australia','Austrália','#fbe36a')
px(-2022,300,880,'mar','','','#d8e1ed')
def clas(px):
    b,g,r=[int(v) for v in px]
    if abs(b-237)+abs(g-225)+abs(r-216)<=24: return 'mar'
    return 'sem-dono' if min(b,g,r)>=247 else 'estado'
def snap(ano,x,y,esp):
    k=str(anos[str(ano)]['mapa']); im=cv2.imread(f'{V2}/mapas/{k}.png')
    best=None
    for R in range(0,18):
        for dy in range(-R,R+1):
            for dx in range(-R,R+1):
                if max(abs(dx),abs(dy))!=R: continue
                xx,yy=x+dx,y+dy
                if not(4<=xx<1916 and 4<=yy<956): continue
                w=im[yy-3:yy+4,xx-3:xx+4].reshape(-1,3).astype(int)
                if (w.max(0)-w.min(0)).max()>6: continue
                if clas(im[yy,xx])!=esp: continue
                return xx,yy
    return None
out=[]
for ano,t,a,b,esp,nv,nm,cor,creme in L:
    if t=='px':
        sn=snap(ano,a,b,esp)
        if sn is None: print('SEM PONTO UNIFORME',ano,nm,a,b); sn=(a,b)
        a,b=sn
    lon,lat=(inv(ano,a,b) if t=='px' else (a,b))
    d={"ano":ano,"lon":lon,"lat":lat,"espera":esp,"nome_video":nv,"nome":nm,"cor_aprox":cor}
    creme,op=creme
    if creme: d["creme"]=True
    if op: d["outra_ponta"]=True
    out.append(d)
json.dump({"_ajuda":"Casos de referência: ponto (lon, lat) em um ano (a.C. positivo, d.C. negativo) e o que o vídeo mostra ali. 'espera': estado | sem-dono | mar. 'creme': estado de cor creme, quase igual ao branco. Pontos escolhidos no quadro do vídeo e convertidos com a calibração da E3; confira antes de usar em novas etapas.","casos":out},open('scripts/mapa-geral/casos.json','w'),ensure_ascii=False,indent=1)
print(len(out))
