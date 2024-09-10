import numpy as np
from scipy.signal import cheb1ord, cheby1, lfilter, detrend


def raydec(vert, north, east, time, fmin, fmax, fsteps, cycles, dfpar, nwind):
    # from: # https://github.com/ManuelHobiger/RayDec
    """
    RAYDEC1STATION(VERT, NORTH, EAST, TIME, FMIN, FMAX, FSTEPS, CYCLES, DFPAR, NWIND)
    calculates the ellipticity of Rayleigh waves for the
    input data VERT, NORTH, EAST and TIME for a single station
    for FSTEPS frequencies (on a logarithmic scale) between
    FMIN and FMAX, using CYCLES periods for the stacked signal
    and DFPAR as the relative bandwidth for the filtering.
    The signal is cut into NWIND different time windows and
    RayDec is applied to each of them.

    VERT, NORTH, EAST and TIME have to be arrays of equal sizes

    suggested values: CYCLES = 10
    DFPAR = 0.1
    NWIND such that the single time windows are about 10 minutes long
    """

    v1, n1, e1, t1 = vert, north, east, time

    # setting up
    K0 = v1.shape[0]
    K = np.floor(K0 / nwind).astype(int)
    tau = t1[1] - t1[0]
    DTmax = 30
    fnyq = 1 / (2 * tau)
    fstart = np.max([fmin, 1 / DTmax])
    fend = np.min([fmax, fnyq])
    flist = np.zeros(fsteps)
    constlog = (fend / fstart) ** (1 / (fsteps - 1))
    fl = fstart * constlog ** (np.cumsum(np.ones((fsteps, nwind)), axis=0) - 1)
    #fl = np.repeat([np.logspace(fstart, fend, fsteps)], nwind, axis=0).T
    el = np.zeros((fsteps, nwind))

    # loop over the time windows
    for ind1 in [0]: # range(nwind):
        print("\nwindow: ", str(ind1))
        # *** matlab detrend -> scipy
        # *** validate the indexing <3
        #print(north[:5])
        vert = detrend(v1[ind1 * K : (ind1 + 1) * K], type="constant")
        north = detrend(n1[ind1 * K : (ind1 + 1) * K], type="constant")
        east = detrend(e1[ind1 * K : (ind1 + 1) * K], type="constant")
        time = t1[ind1 * K : (ind1 + 1) * K]
        #print(np.sum(vert), np.sum(north), np.sum(east))
        #print(north[:5])

        horizontalamp = np.zeros(fsteps)
        verticalamp = np.zeros(fsteps)

        Tmax = np.max(time)
        #weird_index = int(np.ceil(Tmax * fend))
        #thetas = np.zeros((fsteps, weird_index))
        #corr = np.zeros((fsteps, weird_index))
        #ampl = np.zeros((fsteps, weird_index))
        #dvmax = np.zeros(fsteps)

        # loop over the frequencies
        for findex in range(fsteps):
            f = fl[findex, ind1]
            #print("f", f)#20

            # setting up the filter limits
            df = dfpar * f
            fmin = np.max([fstart, f - df / 2])
            fmax = np.min([fnyq, f + df / 2])
            flist[findex] = f
            DT = cycles / f
            wl = int(np.round(DT / tau))
            # int(np.ceil(Tmax * fend))


            # setting up the Chebyshev filter
            Wp = [fmin + (fmax - fmin) / 10, fmax - (fmax - fmin) / 10] / fnyq
            Ws = [fmin - (fmax - fmin) / 10, fmax + (fmax - fmin) / 10] / fnyq
            Rp = 1
            Rs = 5

            N, Wn = cheb1ord(Wp, Ws, Rp, Rs)
            b, a = cheby1(N, 0.5, Wn, btype="bandpass")
            # w, h = signal.freqz(b, a)

            #taper1 = np.linspace(0, 1, int(len(time)/100))
            
            taper_spacing = 1 / np.round(len(time)/100)
            taper1 = np.arange(0, 1 + taper_spacing, taper_spacing)
            taper2 = np.ones(len(time)- 2*len(taper1))
            taper3 = np.flip(taper1)
            taper = np.concatenate((taper1, taper2, taper3))

            #print(np.min(vert), np.max(vert)) #-0.0334, 0.032
            
            # filtering the signals
            norths = lfilter(b, a, taper*north)
            easts = lfilter(b, a, taper*east)
            verts = lfilter(b, a, taper*vert)

            #print(norths.shape, np.min(norths), np.max(norths))
            #print(easts.shape, np.min(easts), np.max(easts))
            #print(verts.shape, np.min(verts), np.max(verts))

            #print("K", K)#5804
            derive = (
                np.sign(verts[1:K]) - np.sign(verts[: K - 1])
            ) / 2  # finding the negative-positive zero crossings on the vertical component
            
            #print(np.min(verts), np.max(verts))
            #print(np.min(derive), np.max(derive))
            #print(derive.shape) #5803
            vertsum = np.zeros(wl)
            horsum = np.zeros(wl)

            # loop over all zero crossings
            # *** check bounds

            # int(np.ceil(Tmax * fend))

            # why and how is it shape wl
            # wl number of iterations needed to get total window time
            #print(len(derive)) #5803

            indices = np.arange(int(np.ceil(1 / (4 * f * tau))), len(derive) - wl)
            #print(np.min(indices), np.max(indices)) #2, 5752
            #print(easts.shape, np.min(easts), np.max(easts))
            for ind in range(len(indices)):
                # we need to subtract (1 / (4 * f * tau) from east and north components to 
                # account for the 90 degree phase shift between vertical and horizontal 
                # components. this means index needs to be at least (1 / (4 * f * tau)
                index = indices[ind]

                if derive[index] != 1:
                    continue

                vsig = verts[index : index + wl]

                einds = index - int(np.floor(1 / (4 * f * tau))) # 5748
                esig = easts[einds : einds + wl]
                a = np.arange(einds, einds + wl)

                #print(index, int(np.floor(1 / (4 * f * tau))), einds+wl) # 5749, 1, 5798
                
                #print(a.shape, np.min(a), np.max(a)) #50, 5748, 5797

                ninds = index - int(np.floor(1 / (4 * f * tau)))
                nsig = norths[ninds : ninds + wl]
                #print(np.sum(nsig))

                integral1 = np.sum(vsig * esig)
                integral2 = np.sum(vsig * nsig)

                theta = np.arctan(integral1/integral2)

                if integral2 < 0:
                    theta = theta + np.pi

                theta = (theta + np.pi) % (2 * np.pi)  # The azimuth is well estimated in this way (assuming retrograde)
                hsig = np.sin(theta) * esig + np.cos(theta) * nsig  # The horizontal signal is projected in the azimuth direction.
                #print(hsig[:5])
                #print(theta)
                #print(np.sum(hsig))

                correlation = np.sum(vsig * hsig) / np.sqrt(
                    np.sum(vsig * vsig) * np.sum(hsig * hsig)
                )  # The correlation is always negative (between -1 and 0).

                if correlation >= -1:
                    vertsum = vertsum + correlation**2 * vsig
                    horsum = horsum + correlation**2 * hsig
                    #print(vertsum[:5])

                #thetas[findex, ind] = theta
                #corr[findex, ind] = correlation
                #dvmax[findex] = ind
                #ampl[findex, ind] = np.sum(vsig**2 + hsig**2)

            klimit = int(np.round(DT / tau))
            verticalamp[findex] = np.sqrt(np.sum(vertsum[:klimit] ** 2))
            horizontalamp[findex] = np.sqrt(np.sum(horsum[:klimit] ** 2))
            #print(verticalamp[findex])

        ellist = horizontalamp / verticalamp

        fl[:, ind1] = flist
        el[:, ind1] = ellist

    V = fl
    W = el

    return V, W
