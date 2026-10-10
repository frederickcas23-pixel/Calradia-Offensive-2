import struct
class R:
    def __init__(s,d): s.d=d; s.o=0
    def i(s): v=struct.unpack_from('<i',s.d,s.o)[0]; s.o+=4; return v
    def u(s): v=struct.unpack_from('<I',s.d,s.o)[0]; s.o+=4; return v
    def f(s): v=struct.unpack_from('<f',s.d,s.o)[0]; s.o+=4; return v
    def b(s): v=s.d[s.o]; s.o+=1; return v
    def s_(s): n=s.i(); v=s.d[s.o:s.o+n].decode('latin-1'); s.o+=n; return v
    def p3(s): v=struct.unpack_from('<3f',s.d,s.o); s.o+=12; return v
    def p2(s): v=struct.unpack_from('<2f',s.d,s.o); s.o+=8; return v
def load(path):
    r=R(open(path,'rb').read()); out={'mesh':[],'skeleton':[],'material':[],'texture':[],'other':[]}
    ver=0
    while r.o<len(r.d):
        tok=r.s_()
        if tok=='end': break
        if tok=='rfver ': ver=r.i(); continue
        n=r.i()
        if tok=='mesh':
            for _ in range(n):
                m={'name':r.s_(),'flags':r.u(),'material':r.s_()}
                tang=bool(m['flags']&(1<<16))
                m['pos']=[r.p3() for _ in range(r.i())]
                rig=[]
                for _ in range(r.i()):
                    bi=r.i(); pairs=[(r.i(),r.f()) for _ in range(r.i())]; rig.append((bi,pairs))
                m['rig']=rig
                fr=[]
                for _ in range(r.i()):
                    t=r.i(); p=[r.p3() for _ in range(r.i())]; nn=[r.p3() for _ in range(r.i())]; fr.append((t,p,nn))
                m['frames']=fr
                vs=[]
                for _ in range(r.i()):
                    idx=r.i(); col=r.u(); nrm=r.p3()
                    if ver and tang: tg=r.p3(); ti=r.b()
                    uv=r.p2()
                    if not ver: uv2=r.p2()
                    vs.append((idx,col,nrm,uv))
                m['vert']=vs
                m['face']=[(r.i(),r.i(),r.i()) for _ in range(r.i())]
                out['mesh'].append(m)
        elif tok=='skeleton':
            for _ in range(n):
                sk={'name':r.s_(),'bones':[]}
                for _ in range(r.i()):
                    att=r.i(); nm=r.s_(); b=r.i(); x=r.p3(); z=r.p3(); y=r.p3(); t=r.p3()
                    sk['bones'].append({'parent':att,'name':nm,'x':x,'y':y,'z':z,'t':t})
                out['skeleton'].append(sk)
        elif tok=='material':
            for _ in range(n):
                out['material'].append({'name':r.s_(),'flags':r.u(),'shader':r.s_(),'diffuseA':r.s_(),'diffuseB':r.s_(),'bump':r.s_(),'enviro':r.s_(),'spec':r.s_(),'specular':r.f(),'rgb':(r.f(),r.f(),r.f())})
        elif tok=='texture':
            for _ in range(n): out['texture'].append({'name':r.s_(),'flags':r.u()})
        else:
            out['other'].append((tok,n,r.o)); break
    out['ver']=ver
    return out
