import aipy as a, numpy as n, pylab as P
import sys

def get_dict_of_uv_data(filename, antstr, polstr, decimate=1, decphs=0):
    times, dat, flg = [], {}, {}
    uv = a.miriad.UV(filename)
    a.scripting.uv_selector(uv, antstr, polstr)
    if decimate > 1: uv.select('decimate', decimate, decphs)
    for (crd,t,(i,j)),d,f in uv.all(raw=True):
        if len(times) == 0 or t != times[-1]:
            times.append(t)
        bl = a.miriad.ij2bl(i,j)
        dat[bl] = dat.get(bl,[]) + [d]
        flg[bl] = flg.get(bl,[]) + [f]
    for bl in dat:
        dat[bl] = n.array(dat[bl])
        flg[bl] = n.array(flg[bl])
    return n.array(times), dat, flg

def gen_ddr_filter(shape, dw, drw, ratio=.25, invert=False):
    filter = n.ones(shape)
    x1,x2 = drw, -drw
    if x2 == 0: x2 = shape[0]
    y1,y2 = dw, -dw
    if y2 == 0: y2 = shape[1]
    filter[x1+1:x2,0] = 0
    filter[0,y1+1:y2] = 0
    filter[1:,1:] = 0
    x,y = n.indices(shape).astype(n.float)
    x -= shape[0]/2
    y -= shape[1]/2
    r2 = (x/(ratio*drw+.5))**2 + (y/(ratio*dw+.5))**2
    r2 = a.img.recenter(r2, (shape[0]/2, shape[1]/2))
    filter += n.where(r2 <= 1, 1, 0)
    filter = filter.clip(0,1)
    if invert: return n.logical_not(filter)
    else: return filter

def rms(d,wgt=None):
    if wgt == None: return n.sqrt(n.average(n.abs(d)**2))
    else: return n.sqrt(n.sum(n.abs(d)**2) / n.sum(n.abs(wgt)**2))

def waterfall(d, mode='log', mx=None, drng=None, recenter=False, **kwargs):
    if n.ma.isMaskedArray(d): d = d.filled(0)
    if recenter: d = a.img.recenter(d, n.array(d.shape)/2)
    if mode.startswith('phs'): d = n.angle(d)
    elif mode.startswith('lin'): d = n.absolute(d)
    elif mode.startswith('real'): d = d.real
    elif mode.startswith('imag'): d = d.imag
    elif mode.startswith('log'):
        d = n.absolute(d)
        d = n.ma.masked_less_equal(d, 0)
        d = n.ma.log10(d)
    else: raise ValueError('Unrecognized plot mode.')
    if mx is None: mx = d.max()
    if drng is None: drng = mx - d.min()
    mn = mx - drng
    P.imshow(d, vmax=mx, vmin=mn, aspect='auto', interpolation='nearest', **kwargs)
