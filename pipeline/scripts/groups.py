import json,numpy as np
from PIL import Image
from scipy import ndimage as nd
import sys;F=sys.argv[1] if len(sys.argv)>1 else 'web/city_meta.json';m=json.load(open(F));J=m['jobs']
idx=np.array(Image.open(F.replace('meta.json','index.png')))[...,0]
G=sorted(set(j['group'] for j in J),key=lambda g:-sum(x['ws'] for x in J if x['group']==g))
A=np.array([j['label'][:2] for j in J])
yy,xx=np.mgrid[0:2400:6,0:1800:6]
block=np.zeros(yy.shape,bool)
for x,y in A: block|=(np.abs(xx-x)<190)&(np.abs(yy-y)<60)
out={};vis=np.zeros(idx.shape+(3,),np.uint8);pal=[[255,255,255],[120,120,120],[255,0,200],[255,80,80],[80,200,80],[80,120,255],[240,200,60],[200,80,240],[60,220,220]]
for g,name in enumerate(G):
  mk=np.isin(idx,[k for k,j in enumerate(J) if j['group']==name]); vis[mk]=pal[g]
  lab,n=nd.label(mk); sz=sorted(nd.sum(mk,lab,range(1,n+1)))[::-1]
  print(name,'pieces',n,[int(s) for s in sz[:3]])
  big=lab==(np.argmax(nd.sum(mk,lab,range(1,n+1)))+1)
  e=nd.distance_transform_edt(nd.gaussian_filter(big.astype(float),20)>.5)[::6,::6]
  cy,cx=nd.center_of_mass(big)
  for relax in [0,1]:
    sc=np.minimum(e,140)-0.2*np.hypot(yy-cy,xx-cx); bad=(e<50)
    if not relax: bad|=block
    sc[bad]=-1e9
    if sc.max()>-1e8: break
  i=np.unravel_index(sc.argmax(),sc.shape); out[name]=[[int(xx[i]),int(yy[i])]]
  block|=(np.abs(xx-xx[i])<220)&(np.abs(yy-yy[i])<70)
print(out);m['groups']=out;json.dump(m,open(F,'w'),ensure_ascii=False)
Image.fromarray(vis[::4,::4]).save('groups.png')
