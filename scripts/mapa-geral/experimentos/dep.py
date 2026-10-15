import sys,json,numpy as np,cv2,os
sys.path.insert(0,'scripts/mapa-geral')
import rotular as r
src=open('scripts/mapa-geral/rotular.py').read()
src=src.replace("    # marcadores do watershed: 0 = desconhecido; 1 = mar; 2.. = sementes\n    marc =","    DEP['grupos']=grupos; DEP['classe']=classe.copy(); DEP['lab']=lab; DEP['peq']=peq; DEP['cores']=cores\n    # marcadores do watershed: 0 = desconhecido; 1 = mar; 2.. = sementes\n    marc =",1)
src=src.replace("    mar = ws == 1\n","    DEP['ws']=ws.copy(); DEP['nova']=nova\n    mar = ws == 1\n",1)
g={'__name__':'dep','DEP':{},'__file__':os.path.abspath('scripts/mapa-geral/rotular.py')}
exec(compile(src,'rot','exec'),g)
def rodar(k):
    im=cv2.imread(r.V2+f'/mapas/{k}.png')
    out=g['rotular_mapa'](im,None)
    return g['DEP'],out
