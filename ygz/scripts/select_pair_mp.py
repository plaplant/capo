__author__ = 'yunfanzhang'

import numpy as n, multiprocessing as mp
import export_beam, quick_sort, itertools
from scipy import interpolate
import pdb

#round values to cell size
def rnd(val, cell, decimals=0):
    return n.around(val/cell,decimals=decimals) * cell

#coarsely determine crossings by griding the uv plane
#Format: d[ur_rounded] = [(bl,t,(u,v)),...]
def pair_coarse(aa, src, times, dist,redundant=False, add_tol=0.5):
    f2 = open('./redundant_bl.out', 'w')
    f2.close()
    f2 = open('./redundant_bl.out', 'a')
    ant_dict,ant_dict2,ant_dict3,repbl = {},{},{},{}
    t_ad = times[10]
    aa.set_jultime(t_ad)
    src.compute(aa)
    NU,NV = len(aa.ant_layout),len(aa.ant_layout[0])
    nants = len(aa)
    print "pair_coarse: nants, NU, NV =", nants, NU, NV
    for i in range(NU):
        for j in range(NV):
            ant_dict[aa.ant_layout[i][j]] = (i,j)  #ant_dict[random ant#]=antlayoutindex
    f2.write(str(ant_dict)+'\n')
    if nants == 128:
        ant_dict2 = {114:(100,100),116:(100,101),117:(100,102),118:(100,103),119:(100,104),120:(100,105)}
        ant_dict3 = {123:(101,100),124:(101,101),125:(101,102),126:(101,103),127:(101,104)}
        f2.write(str(ant_dict2)+'\n')
        f2.write(str(ant_dict3)+'\n')
    for i in range(nants):
        for j in range(i+1,nants):
            try: dkey = (0,ant_dict[i][0]-ant_dict[j][0],ant_dict[i][1]-ant_dict[j][1])
            except(KeyError):
                if nants == 128:
                    try: dkey = (1,ant_dict2[i][0]-ant_dict2[j][0],ant_dict2[i][1]-ant_dict2[j][1])
                    except(KeyError):
                        try: dkey = (2,ant_dict3[i][0]-ant_dict3[j][0],ant_dict3[i][1]-ant_dict3[j][1])
                        except(KeyError):
                            #pdb.set_trace()
                            uvw = aa.gen_uvw(i,j,src=src).flatten()
                            if uvw[0] < 0: uvw = -uvw
                            uvw_r = rnd(uvw, add_tol)
                            dkey = (3,uvw_r[0],uvw_r[1])
                        else:
                            if dkey[1]<0 or (dkey[1]==0 and dkey[2]<0): dkey = (dkey[0],-dkey[1],-dkey[2])
                    else:
                        if dkey[1]<0 or (dkey[1]==0 and dkey[2]<0): dkey = (dkey[0],-dkey[1],-dkey[2])
                else:
                    #pdb.set_trace()  #all 64 antennas should be in ant_layout
                    break
            else:
                if dkey[1]<0 or (dkey[1]==0 and dkey[2]<0): dkey = (dkey[0],-dkey[1],-dkey[2])
            repbl[dkey] = repbl.get(dkey,[]) + [(i,j)]
    print "pair_coarse:", len(repbl), "representative baselines, 4432 expected"
    #print repbl
  #  d = {}
  #
  #
  #  nants = len(aa)
  #  print "dist_ini = ", dist_ini
  #  for i in range(nants):
  #      for j in range(i+1,nants):
  ##          uvw = aa.gen_uvw(i,j,src=src).flatten()
   #         if uvw[0] < 0: uvw = -uvw
  # #         uvw_r = rnd(uvw, dist_ini)
  #          uv_r = (uvw_r[0],uvw_r[1])
  #          new_sample = ((i,j),t,(uvw[0],uvw[1]))
  #          d[uv_r] = d.get(uv_r,[]) + [new_sample]
    d = {}
    for t in times:
        aa.set_jultime(t)
        src.compute(aa)
        for key in repbl:
            #print key, repbl[key]
            if key[0] == 3 and len(repbl[key]) > 1:
                print "Found simultaneously redundant baseline:", key, repbl[key]
                f2.write("Found simultaneously redundant bls:"+str(key)+str(repbl[key]))
                continue
            else: bl = repbl[key][0]
            uvw = aa.gen_uvw(*bl,src=src).flatten()
            if uvw[0] < 0: uvw = -uvw
            uvw_r = rnd(uvw, dist)
            uv_r = (uvw_r[0],uvw_r[1])
            new_sample = (bl,t,(uvw[0],uvw[1]))
            try: samples = d[uv_r]
            except(KeyError): d[uv_r] = [new_sample]
            else:
                if samples[-1][0] == bl: continue # bail if repeat entry of same baseline
                #try: delet = samples[-2][0]
                #except(IndexError): print "nothing to worry about"
                #else:
                #    if delet == bl: continue
                d[uv_r].append(new_sample)
    for key in d.keys(): # remove entries with no redundancy
        if len(d[key]) < 2: del d[key]
    f2.close()
    return d

#sorts the given dictionary of crossings in order of decreasing correlations
#Format: sorted = [(val,(bl1,t1),(bl2,t2),(u1,v1)),...] (u1v1 used for test plots only)
def pair_sort(pairings, freq, fbmamp, cutoff=0.):
    sorted = []
    for key in pairings:
        L = len(pairings[key])
        for i in range(L):  # get the points pairwise
            for j in range(i+1,L):
                pt1,pt2 = pairings[key][i],pairings[key][j]
                duv = tuple(x - y for x,y in zip(pt1[2], pt2[2]))
                val = export_beam.get_overlap(freq,fbmamp,*duv)
                if abs(val) > cutoff:
                    sorted.append((val,(pt1[0],pt1[1]),(pt2[0],pt2[1]),pt1[2]))
    quick_sort.quick_sort(sorted,0,len(sorted)-1)
    return sorted

#get dictionary of closest approach points, works when each two tracks only cross once (satisfied in this case)
#format: clos_app[bl1,bl2] = (val, t1, t2, (u1,v1))
def get_closest(pairs_sorted):
    clos_app = {}
    for k in n.arange(len(pairs_sorted)):
        ckey = (pairs_sorted[k][1][0],pairs_sorted[k][2][0])
        count = clos_app.get(ckey,[])
        if count == []:
            clos_app[ckey] = (pairs_sorted[k][0],pairs_sorted[k][1][1],pairs_sorted[k][2][1],pairs_sorted[k][3])
    return clos_app

def alter_clos_p1(ev, que,freq,fbmamp,clos_app):
    while not ev.is_set():
        try: arr = que.get(block=True, timeout=1)
        except(mp.queues.Empty): continue
        L = len(arr)
        print L
        for i in range(L):  # get the points pairwise
            for j in range(i+1,L):
                pt1,pt2 = arr[i],arr[j]
                if pt1[0] == pt2[0]:
                    #print "alter_clos: ignore self-correlating baseline: ", pt1[0]
                    continue
                duv = tuple(x - y for x,y in zip(pt1[2], pt2[2]))
                val = export_beam.get_overlap(freq,fbmamp,*duv)
                blkey = (pt1[0],pt2[0])
                #if blkey==((92,112),(0,91)) or blkey==((0,91),(92,112)): print blkey,val, duv
                clos_app[blkey] = clos_app.get(blkey,[])+[(val,pt1[1],pt2[1],pt1[2])]
    #print "exiting parallel 1"
    #if que.empty(): print "queue is empty"
    return

#Alternative way to pair_sort + get_closest, usually faster (~n vs ~nlog(n))
#format: clos_app[bl1,bl2] = (val, t1, t2, (u1,v1))
def alter_clos(pairings, freq, fbmamp, cutoff=0., nproc=1):
    if __name__ == 'select_pair':
        manager = mp.Manager()
        que = manager.Queue(nproc)
        clos_app = manager.dict()
        ev = mp.Event()
        print "alter_clos: len(pairings)=", len(pairings)
        pool = []
        for i in xrange(nproc):
            p = mp.Process(target=alter_clos_p1, args=(ev, que,freq,fbmamp,clos_app))
            p.start()
            pool.append(p)
        iters = itertools.chain(pairings.keys(), (None,)*nproc)
        for key in iters:
            if key != None: que.put(pairings[key])
        while all answers, then ev.set()

        for p in pool: p.join()
        for blkey in clos_app.keys():
            N = len(clos_app[blkey])
            #if N > 10:
            #    print "Found simultaneously redundant baseline:", blkey
            #    del clos_app[blkey]
            #    continue
            max,max_val = 0,0.
            for i in range(N):
                if max_val < abs(clos_app[blkey][i][0]):
                    max,max_val = i, abs(clos_app[blkey][i][0])
            clos_app[blkey] = clos_app[blkey][max]
        return clos_app
    else: print "name is", __name__

#computes correlations of baselines bl1, bl2 at times t1, t2
def get_corr(aa, src, freq,fbmamp, t1,t2, bl1, bl2):
    aa.set_jultime(t1)
    src.compute(aa)
    if src.alt>0:
        uvw1 = aa.gen_uvw(*bl1,src=src).flatten()
        if uvw1[0] < 0: uvw1 = -uvw1
    else: return 0  #if src below horizon, will break out of while loop
    aa.set_jultime(t2)
    src.compute(aa)
    if src.alt>0:
        uvw2 = aa.gen_uvw(*bl2,src=src).flatten()
        if uvw2[0] < 0: uvw2 = -uvw2
        duv = (uvw1[0]-uvw2[0],uvw1[1]-uvw2[1])
    else: return 0
    #print n.sqrt(duv[0]*duv[0]+duv[1]*duv[1])
    return export_beam.get_overlap(freq,fbmamp,*duv), (uvw1,uvw2)

def get_ovlp(aa,t1,t2,rbm2interp):
    aa.set_jultime(t1)
    ra1 = aa.radec_of(0,n.pi/2)[0]
    aa.set_jultime(t2)
    dra = aa.radec_of(0,n.pi/2)[0]-ra1
    dl = n.sin(dra)
    return rbm2interp(dl,0)

def get_weight(aa,bl1,bl2,uvw,multweight,noiseweight, ovlp=1.):
    weight = ovlp
    ant_dict = {}
    NU,NV = len(aa.ant_layout),len(aa.ant_layout[0])
    for i in range(NU):
        for j in range(NV):
            ant_dict[aa.ant_layout[i][j]] = (i,j)  #ant_dict[random ant#]=antlayoutindex
    try: multfactor = (NU-abs(ant_dict[bl1][0]-ant_dict[bl2][0]))*(NV-abs(ant_dict[bl1][1]-ant_dict[bl2][1]))
    except(KeyError): multfactor = 1
    if multweight: weight = weight*multfactor
    noisefactor = (uvw[0]*uvw[0]+uvw[1]*uvw[1]+uvw[2]*uvw[2])**(-1.5)
    if noiseweight: weight = weight*noisefactor
    return weight

# Outputs the final array of sorted pairs of points in uv space,
# spaced in time to avoid over computing information already extracted from fringe rate filtering
# format pair_fin = [(val,(bl1,t1),(bl2,t2))...]
def pair_fin(clos_app,dt, aa, src, freq,fbmamp,multweight=True,noiseweight=True,ovlpweight=True,cutoff=6000.):
    final = []
    cnt, N = 0,len(clos_app)
    if ovlpweight:
        fbm2 = n.multiply(fbmamp,fbmamp)   #element wise square for power beam
        rbm2 = n.fft.fft2(fbm2)
        freqlm = n.fft.fftfreq(len(freq),d=(freq[1]-freq[0]))
        rbm2 = n.fft.fftshift(rbm2)
        freqlm = n.fft.fftshift(freqlm)
        rbm2interp = interpolate.interp2d(freqlm, freqlm, rbm2, kind='cubic')
    for key in clos_app:
        cnt = cnt+1
        if (cnt/200)*200 == cnt:
            print 'Calculating baseline pair %d out of %d:' % (cnt,N)
        bl1,bl2 = key[0],key[1]
        t1,t2 = clos_app[key][1],clos_app[key][2]
        correlation,(uvw1,uvw2) = get_corr(aa, src, freq,fbmamp, t1,t2, bl1, bl2)
        if correlation == 0: continue
        if ovlpweight: ovlp = get_ovlp(aa,t1,t2,rbm2interp)
        else: ovlp = 1.
        weight = get_weight(aa,bl1,bl2,uvw1,multweight,noiseweight,ovlp)
        while correlation > cutoff:
            final.append((weight*correlation,correlation,(bl1,t1,uvw1),(bl2,t2,uvw2)))
            t1,t2 = t1+dt,t2+dt
            try: correlation,(uvw1,uvw2)  = get_corr(aa, src,freq,fbmamp, t1,t2, bl1, bl2)
            except(TypeError): correlation  = 0.
            else:
                if ovlpweight: ovlp = get_ovlp(aa,t1,t2,rbm2interp)
                else: ovlp = 1.
                weight = get_weight(aa,bl1,bl2,uvw1,multweight,noiseweight,ovlp)
        if ovlpweight: ovlp = get_ovlp(aa,t1,t2,rbm2interp)
        else: ovlp = 1.
        weight = get_weight(aa,bl1,bl2,uvw1,multweight,noiseweight,ovlp)
        while correlation > cutoff:
            final.append((weight*correlation,correlation,(bl1,t1,uvw1),(bl2,t2,uvw2)))
            t1,t2 = t1-dt,t2-dt
            try: correlation,(uvw1,uvw2)  = get_corr(aa, src,freq,fbmamp, t1,t2, bl1, bl2)
            except(TypeError): correlation  = 0.
            else:
                if ovlpweight: ovlp = get_ovlp(aa,t1,t2,rbm2interp)
                else: ovlp = 1.
                weight = get_weight(aa,bl1,bl2,uvw1,multweight,noiseweight,ovlp)
    quick_sort.quick_sort(final,0,len(final)-1)
    return final

#create a test sample to plot the pairs of points
def test_sample(pairs_final,cutoff=3000.):
    pairs = []
    print len(pairs_final)
    print pairs_final[0]
    bl1,bl2 = pairs_final[0][2][0],pairs_final[0][3][0]
    for entry in pairs_final:
        if (entry[2][0],entry[3][0]) != (bl1,bl2): continue
        uvw1,uvw2 = entry[2][2],entry[3][2]
        pairs.append(((uvw1[0],uvw1[1]),(uvw2[0],uvw2[1])))
    return pairs