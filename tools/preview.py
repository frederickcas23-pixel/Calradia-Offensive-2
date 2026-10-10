import sys,numpy as np,json; sys.path.insert(0,'tools'); import brf
from PIL import Image, ImageDraw
def raster(img,zb,P2,Z,col):
    # P2: (3,2) pixel coords; simple bbox rasteriser
    x0,y0=np.floor(P2.min(0)).astype(int); x1,y1=np.ceil(P2.max(0)).astype(int)
    H,W=zb.shape; x0=max(x0,0); y0=max(y0,0); x1=min(x1,W-1); y1=min(y1,H-1)
    if x1<x0 or y1<y0: return
    xs,ys=np.meshgrid(np.arange(x0,x1+1),np.arange(y0,y1+1))
    a,b,c=P2
    den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
    if abs(den)<1e-9: return
    l1=((b[1]-c[1])*(xs-c[0])+(c[0]-b[0])*(ys-c[1]))/den
    l2=((c[1]-a[1])*(xs-c[0])+(a[0]-c[0])*(ys-c[1]))/den
    l3=1-l1-l2
    m=(l1>=-0.01)&(l2>=-0.01)&(l3>=-0.01)
    z=l1*Z[0]+l2*Z[1]+l3*Z[2]
    sub=zb[y0:y1+1,x0:x1+1]; m&=z>sub
    sub[m]=z[m]; img[y0:y1+1,x0:x1+1][m]=col
def render(tris,cols,ax_u,ax_v,ax_d,size=520,bounds=None,pad=0.05):
    # tris: (N,3,3) ; cols (N,3)
    U=tris@ax_u; V=tris@ax_v; D=tris@ax_d
    if bounds is None: bounds=(U.min(),U.max(),V.min(),V.max())
    u0,u1,v0,v1=bounds; s=(size*(1-2*pad))/max(u1-u0,v1-v0)
    img=np.full((size,size,3),245,np.uint8); zb=np.full((size,size),-1e9)
    for t in range(len(tris)):
        P2=np.stack([(U[t]-u0)*s+size*pad,(v1-V[t])*s+size*pad],1)
        raster(img,zb,P2,D[t],cols[t])
    return img
def mesh_tris(m,xf=None):
    P=np.array(m['pos']);
    if xf is not None: P=P@xf[0].T+xf[1]
    F=np.array(m['face']); T=P[F]
    n=np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0]); n/= (np.linalg.norm(n,axis=1,keepdims=True)+1e-12)
    return T,n
def shade(n,light,base):
    k=np.clip(n@light,0,1)*0.7+0.3
    return (np.array(base)[None,:]*k[:,None]).astype(np.uint8)
