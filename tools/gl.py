import json,numpy as np,os,re
CT={5120:np.int8,5121:np.uint8,5122:np.int16,5123:np.uint16,5125:np.uint32,5126:np.float32}
NC={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
class G:
    def __init__(s,path):
        s.g=json.load(open(path)); s.dir=os.path.dirname(path)
        s.bufs=[open(os.path.join(s.dir,b['uri']),'rb').read() for b in s.g['buffers']]
    def acc(s,i):
        a=s.g['accessors'][i]; bv=s.g['bufferViews'][a['bufferView']]
        dt=np.dtype(CT[a['componentType']]); n=NC[a['type']]
        off=bv.get('byteOffset',0)+a.get('byteOffset',0); stride=bv.get('byteStride',0)
        buf=s.bufs[bv['buffer']]
        if stride and stride!=dt.itemsize*n:
            arr=np.array([np.frombuffer(buf,dt,n,off+k*stride) for k in range(a['count'])])
        else: arr=np.frombuffer(buf,dt,a['count']*n,off).reshape(a['count'],n)
        if a.get('normalized'):
            arr=arr.astype(np.float32)/np.iinfo(dt).max
        return arr
    def prims(s):
        for mi,m in enumerate(s.g['meshes']):
            for pr in m['primitives']:
                d={'mesh':m['name'].split('.')[-1]}
                for k,v in pr['attributes'].items(): d[k]=s.acc(v)
                d['idx']=s.acc(pr['indices']).reshape(-1,3)
                mat=s.g['materials'][pr['material']] if 'material' in pr else None
                d['mat']=mat['name'].split('/')[-1].replace('.vmat','') if mat else None; d['tex']=None
                if mat:
                    bc=mat.get('pbrMetallicRoughness',{}).get('baseColorTexture')
                    if bc: d['tex']=s.g['images'][s.g['textures'][bc['index']]['source']]['uri']
                yield d
def kv_array(txt,key):
    m=re.search(r'\b'+key+r' =\s*\[',txt); i=m.end(); depth=1; j=i
    while depth:
        c=txt[j]
        if c=='[': depth+=1
        elif c==']': depth-=1
        j+=1
    body=txt[i:j-1]
    if '"' in body: return re.findall(r'"([^"]*)"',body)
    if '[' in body: return [[float(x) for x in r.split(',') if x.strip()] for r in re.findall(r'\[([^\]]*)\]',body)]
    return [float(x) for x in body.replace('\n',' ').split(',') if x.strip()]
def qrot(q):
    x,y,z,w=q
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
def skeleton(txt):
    sk=txt[txt.index('m_modelSkeleton'):]
    names=kv_array(sk,'m_boneName'); par=[int(v) for v in kv_array(sk,'m_nParent')]
    pos=kv_array(sk,'m_bonePosParent'); rot=kv_array(sk,'m_boneRotParent')
    Wp=[None]*len(names); Wr=[None]*len(names)
    for i in range(len(names)):
        R=qrot(rot[i]); t=np.array(pos[i])
        if par[i]<0: Wr[i]=R; Wp[i]=t
        else: p=par[i]; Wp[i]=Wp[p]+Wr[p]@t; Wr[i]=Wr[p]@R
    return names,par,np.array(Wp),Wr
S2W=np.array([[0,-1,0],[1,0,0],[0,0,1]])*0.0254   # source -> warband
G2W=np.array([[-1,0,0],[0,0,1],[0,1,0]])          # gltf -> warband
