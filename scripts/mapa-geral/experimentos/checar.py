import sys,json,cv2
sys.path.insert(0,'scripts/mapa-geral')
V2='scripts/mapa-geral/.cache/v2/'
chk={'2053':{'HRE_oeste':(991,309),'HRE_leste':(1012,327),'Austria':(1057,352),'Hungria_y':(1081,347),'Bohemia':(1025,322),'Cuba':(517,498),'Baja':(333,462),'Florida':(504,462),'NovaEspanha':(393,485),'NovaGranada':(544,591)},
     '1637':{'M':(1496,471),'K':(1529,474),'A':(1537,488)},
     '1137':{'Qarakh':(1000,345),'Qocho':(1300,325),'Yutian':(1150,410)},
     '26':{'Elam_cima':(590,412),'Elam_baixo':(630,440)}}
for k,pts in chk.items():
    reg=cv2.imread(V2+f'rotulos/{k}.png',cv2.IMREAD_UNCHANGED); info=json.load(open(V2+f'rotulos/{k}.json'))['regioes']
    print(k,{n:(int(reg[y,x]),info[reg[y,x]-1]['area_px'] if reg[y,x] else 0) for n,(x,y) in pts.items()})
