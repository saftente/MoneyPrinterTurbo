"""Original ambient underscore: D minor pad, sub pulse, sparse bell motif, gentle riser."""
import json, numpy as np, scipy.signal as sg, soundfile as sf, sys
from pathlib import Path
# Length and riser timing follow shotlist.json, so the music fits whatever voiceover it was cut to.
SHOTS={s["id"]:s for s in json.loads((Path(__file__).resolve().parents[1]/"shotlist.json").read_text(encoding="utf-8"))}
sr=44100; dur=round(SHOTS[max(SHOTS)]["end"]+1.5,2); n=int(sr*dur); t=np.arange(n)/sr
rng=np.random.default_rng(7)
def midi(m): return 440*2**((m-69)/12)
def env(length, a, r):
    e=np.ones(length); A=int(a*sr); R=int(r*sr)
    e[:A]=np.linspace(0,1,A)**2; e[-R:]=np.linspace(1,0,R)**2; return e
out=np.zeros((n,2))
# chord progression, 8 s per chord: Dm(add9) - Bbmaj7 - Gm9 - A(sus4)
chords=[[50,57,62,64,65],[46,53,57,62,65],[43,50,55,58,62],[45,52,57,62,64]]
seg=8.0
for i in range(int(np.ceil(dur/seg))+1):
    c=chords[i%4]; start=int(i*seg*sr)-int(1.5*sr); L=int((seg+3)*sr)
    s=max(start,0); e_=min(start+L,n)
    if e_<=s: continue
    tt=np.arange(e_-s)/sr
    pad=np.zeros((e_-s,2))
    for m in c:
        f=midi(m)
        for d,pan in ((-0.12,0.25),(0.0,0.5),(0.11,0.75)):
            ph=rng.uniform(0,2*np.pi)
            w=np.sin(2*np.pi*f*2**(d/12)*tt+ph)+0.3*np.sin(2*np.pi*2*f*2**(d/12)*tt+ph)
            pad[:,0]+=w*(1-pan); pad[:,1]+=w*pan
    ev=env(L,2.5,3.0)[s-start:e_-start]
    out[s:e_]+=pad*ev[:,None]*0.04
# slow filter sweep via lowpass on whole pad
b,a=sg.butter(2,1400/(sr/2)); out=sg.lfilter(b,a,out,axis=0)
# sub heartbeat pulse ~ 64 bpm, starts at 2 s, fades in
beat=60/64
for k in np.arange(2.0,dur-1,beat):
    for off,amp in ((0,1.0),(0.22,0.6)):
        s=int((k+off)*sr); L=int(0.35*sr)
        if s+L>n: continue
        tt=np.arange(L)/sr
        f=55*np.exp(-tt*6)+38
        w=np.sin(2*np.pi*np.cumsum(f)/sr)*np.exp(-tt*9)
        g=0.16*amp*min(1,(k-2)/8)
        out[s:s+L]+=(w*g)[:,None]
# sparse bell motif (D5 F5 A5 E5) with echoes
motif=[74,77,81,76]; times=[4.0,12.5,20.0,28.5,36.0,44.5,52.0]
for j,tm in enumerate(times):
    m=motif[j%4]; f=midi(m)
    for rep,(delay,g,pan) in enumerate(((0,1,0.5),(0.42,0.45,0.2),(0.84,0.25,0.8),(1.26,0.12,0.3))):
        s=int((tm+delay)*sr); L=int(3.0*sr)
        if s+L>n: continue
        tt=np.arange(L)/sr
        w=(np.sin(2*np.pi*f*tt)+0.35*np.sin(2*np.pi*f*2.76*tt)*np.exp(-tt*3))*np.exp(-tt*1.6)
        out[s:s+L,0]+=w*0.05*g*(1-pan); out[s:s+L,1]+=w*0.05*g*pan
# airy noise bed
noise=rng.standard_normal((n,2)); b,a=sg.butter(2,[2500/(sr/2),7000/(sr/2)],btype='band')
out+=sg.lfilter(b,a,noise,axis=0)*0.004
# risers ending on the twist ("Jetzt wird es seltsam", scene 18) and on the final question (scene 23)
for c1,L_ in ((SHOTS[18]["start"],3.1),(SHOTS[23]["start"],2.1)):
    c0=c1-L_
    s=int(c0*sr); L=int((c1-c0)*sr); tt=np.arange(L)/sr
    nz=rng.standard_normal(L); b,a=sg.butter(2,[800/(sr/2),5000/(sr/2)],btype='band')
    w=sg.lfilter(b,a,nz)*(tt/tt[-1])**2*0.05
    out[s:s+L]+=w[:,None]
# simple stereo reverb (comb feedback)
rev=np.zeros_like(out)
for d,g in ((0.031,0.5),(0.047,0.45),(0.071,0.4),(0.097,0.35)):
    D=int(d*sr); y=np.copy(out)
    for _ in range(5): y[D:]+=g*y[:-D]*0.5
    rev+=y
out=out*0.7+rev*0.12
# fade in/out, normalize to -16 dBFS peak region
fe=np.ones(n); fe[:int(1.5*sr)]=np.linspace(0,1,int(1.5*sr)); fe[-int(3*sr):]=np.linspace(1,0,int(3*sr))
out*=fe[:,None]; out/=np.max(np.abs(out)); out*=0.7
sf.write(sys.argv[1],out.astype(np.float32),sr)
