#! /usr/bin/env python
import aipy as a
import capo
import numpy as np
import matplotlib.pylab as pl
import sys

data_dir = '/data2/home/kkundert/capo/kmk/data/'
data_file = 'zen.2456895.51490.xx.uvcRRE'
uv = a.miriad.UV(data_dir + data_file)
N = uv.__getitem__('nchan')

# NOTE: optimal baseline length formula given in Presley et al 2015 eq. 9
# fill sky map with flat temperature across whole sky (DC signal)
h = a.healpix.HealpixMap(nside=512)
h.map = np.ones(shape = h.map.shape)
print "h size = " + str(h.map.shape)
h.map = h.map*4*np.pi/h.npix() # convert to Jy to make summable
x, y, z = xyz = h.px2crd(np.arange(h.npix())) #topocentric

temps = np.ones(1) # temperature of sky signal

# rest frequency: 150 MHz
freq = np.array([.120, .150])
c = 3e10 # in cm/s
wvlen = c / freq # observed wavelength

# import array parameters
aa = a.cal.get_aa('psa6622_v001', uv['sdf'], uv['sfreq'], uv['nchan'])
# select freq = 150 MHz
aa.select_chans([0, N/2])
beam = aa[0].bm_response(xyz, pol='x')**2
print beam.shape
print "array parameters imported"

# fill sky map with GSM
# create array of GSM files for simulation of multiple frequencies
gsm_dir = '/data2/home/kkundert/capo/kmk/gsm/gsm_raw/gsm'
gsm_files = [1001, 1002, 1003, 1004, 1005]
gsm = a.healpix.HealpixMap(nside=512)
print "gsm size = " + str(gsm.map.shape)
d = np.loadtxt(gsm_dir + str(gsm_files[0]) + '.dat')
print "d size = " + str(d.shape)
gsm.map = d
gsm.map = gsm.map*4*np.pi/gsm.npix() # convert to Jy to make summable
# convert to topocentric coordinates
ga2eq = a.coord.convert_m('eq', 'ga', oepoch=aa.epoch) #conversion matrix
eq2top = a.coord.eq2top_m(aa.sidereal_time(),aa.lat) #conversion matrix
ga2eq2top = np.dot(eq2top, ga2eq)
i, j, k = ijk = np.dot(ga2eq2top,gsm.px2crd(np.arange(gsm.npix()))) #topocentric

# create arrays for visibilities for each baseline
# single timestep, single polarization
# final index is frequency (to be implemented in the future)

# define our observation equation in the Tegmark 1997 form
# Y = AX + N
# Y = observed visibility
# A = theoretical visibility
# X = constant temperature value for global signal
# N = noise

ants = '(64,10,65,9,72,22,80,20,88,43,96,53,104,31)_(64,10,65,9,72,22,80,20,88,43,96,53,104,31)'

time = []
f = {} # dictionary of flags
d = {} # dictionary of spectra information
a.scripting.uv_selector(uv, ants, 'xx')
print "antennae selected"
for (uvw, t, (m, n)), data, flag in uv.all(raw='True'):
    # get visibility information for rest frequency
    bl = a.miriad.ij2bl(m, n)
    if not bl in d.keys(): f[bl] = []; d[bl] = []
    f[bl].append(flag)
    d[bl].append(data)
    time.append(t)
print "data collected"

# simulate visibilities for each baseline
response = {}
vis = {}
for bl in d.keys():
    n, m = a.miriad.bl2ij(bl)
    bx, by, bz = aa.get_baseline(n, m)
    for l in range(len(freq)):
        # attenuate sky signal and visibility by primary beam
        ant_res = beam[l] * h.map
        obs_sky = beam[l] * gsm.map
        phs = np.exp(-2j*np.pi*freq[l]*(bx*x + by*y + bz*z))
        if not bl in response.keys(): response[bl] = []; vis[bl] = []
        response[bl].append(np.sum(np.where(z>0, ant_res*phs, 0)))
        vis[bl].append(np.sum(np.where(z>0, obs_sky*phs, 0)))
        i += 1
print "visibilities simulated"

X = []
for i in range(len(freq)):
	A = np.array([response[bl][i] for bl in response.keys()])
	A.shape = (A.size,1)

	# GSM
	#Y = np.array([vis[bl][i] for bl in vis.keys()])
	#Y.shape = (Y.size,1)

	# simulated data + complex noise
	#Y = A*temps[0] + np.random.normal(size=A.shape) + 1j*np.random.normal(size=A.shape) 

	# PAPER data
	f = 41 
	if i != 0:
	    f = N/2-1 
	Y = np.array([d[bl][0][f] for bl in d.keys()])
	Y.shape = (Y.size,1)
	# find value of X from cleverly factoring out A in a way which properly weights 
	# the measurements
	transjugateA = np.conjugate(np.transpose(A))
	normalization = np.linalg.inv(np.dot(transjugateA, A))
	invA = normalization*transjugateA

	X.append(np.dot(invA,Y))

# print the estimate of the global signal for each frequency
print X
