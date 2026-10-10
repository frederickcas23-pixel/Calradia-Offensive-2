import re,sys,glob,os
def splitc(t):
    q=None
    for i,c in enumerate(t):
        if q:
            if c==q and t[i-1]!='\\': q=None
        elif c in '"\'': q=c
        elif c=='#': return t[:i],' '+t[i:]
    return t,''
d=sys.argv[1]
for p in glob.glob(d+'/*.py'):
    s=open(p,encoding='latin-1').read().replace('\r\n','\n')
    out=[]
    for line in s.split('\n'):
        m=re.match(r'^(\s*)print\s+(?!\()(.*)$',line) if 'print' in line else None
        m2=re.match(r'^(\s*)print\s*$',line)
        if m2: line=m2.group(1)+'print()'
        elif m and not line.strip().startswith('#'):
            body,cm=splitc(m.group(2)); body=body.rstrip()
            trail=body.endswith(',')
            if trail: body=body[:-1]
            line=f"{m.group(1)}print({body}{', end=\" \"' if trail else ''}){cm}"
        else:
            m3=re.match(r'^(\s*)(.*:\s*)print\s+(?!\()(.*)$',line)
            if m3 and not line.strip().startswith('#') and re.match(r'\s*(if|else|elif|for|while|try|except)',line):
                line=f"{m3.group(1)}{m3.group(2)}print({m3.group(3)})"
        out.append(line)
    s='\n'.join(out)
    s=re.sub(r'^import string\b',"import py2string as string",s,flags=re.M)
    s=re.sub(r'^import types\b',"import py2types as types",s,flags=re.M)
    s=s.replace('xrange(','range(').replace('.has_key(','.__contains__(')
    s=re.sub(r'\b(0x[0-9a-fA-F]+|\d+)L\b',r'\1',s)
    s=s.replace('<>','!=')
    open(p,'w',encoding='latin-1',newline='\n').write(s)
open(d+'/py2string.py','w').write('''
from string import *
def replace(s,a,b,n=-1): return s.replace(a,b,n)
def strip(s,c=None): return s.strip(c)
def lstrip(s,c=None): return s.lstrip(c)
def rstrip(s,c=None): return s.rstrip(c)
def find(s,sub,*a): return s.find(sub,*a)
def rfind(s,sub,*a): return s.rfind(sub,*a)
def lower(s): return s.lower()
def upper(s): return s.upper()
def split(s,sep=None,n=-1): return s.split(sep,n)
def join(l,sep=' '): return sep.join(l)
def atoi(s,base=10): return int(s,base)
def atof(s): return float(s)
def count(s,sub): return s.count(sub)
''')
open(d+'/py2types.py','w').write('''
ListType=list; TupleType=tuple; StringType=str; IntType=int; LongType=int; FloatType=float; DictType=dict
''')
