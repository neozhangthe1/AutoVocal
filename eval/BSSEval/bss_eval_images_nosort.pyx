#! /usr/bin/env python

# This python program is an attempt to translate the
# original BSS eval toolbox on Matlab to Python/Numpy

cimport cython
import numpy as np
cimport numpy as cnp
import scipy as scp
import scipy.signal as scpsig
import scipy.linalg as scpla

ctypedef cnp.float64_t dtype_t
## ctypedef cnp.complexFloating_t dtypeC_t

@cython.boundscheck(False)
@cython.wraparound(False)
def nextpow2(int i):
    """
    Find 2^n that is equal to or greater than.
    
    code taken from the website:
    http://www.phys.uu.nl/~haque/computing/WPark_recipes_in_python.html
    """
    cdef int n = 2
    while n < i:
        n = n * 2
    return n

def bss_eval_images_nosort(cnp.ndarray[dtype_t, ndim=3] ie,
                           cnp.ndarray[dtype_t, ndim=3] i, int delaySize=1):
    """
    % BSS_EVAL_IMAGES_NOSORT Measurement of the separation quality for
    % estimated source spatial image signals in terms of true source, spatial
    % (or filtering) distortion, interference and artifacts. The estimated
    % signals must be sorted in the same order as the true source signals.
    %
    % [SDR,ISR,SIR,SAR,perm]=bss_eval_images_nosort(ie,i)
    %
    % Inputs:
    % ie: nsrc x nsampl x nchan matrix containing estimated source images
    % i: nsrc x nsampl x nchan matrix containing true source images
    %
    % Outputs:
    % SDR: nsrc x 1 vector of Signal to Distortion Ratios
    % ISR: nsrc x 1 vector of source Image to Spatial distortion Ratios
    % SIR: nsrc x 1 vector of Source to Interference Ratios
    % SAR: nsrc x 1 vector of Sources to Artifacts Ratios
    %
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    % Copyright 2007-2008 Emmanuel Vincent
    % This software is distributed under the terms of the GNU Public License
    % version 3 (http://www.gnu.org/licenses/gpl.txt)
    % If you find it useful, please cite the following reference:
    % Emmanuel Vincent, Hiroshi Sawada, Pau Bofill, Shoji Makino and Justinian
    % P. Rosca, "First stereo audio source separation evaluation campaign:
    % data, algorithms and results," In Proc. Int. Conf. on Independent
    % Component Analysis and Blind Source Separation (ICA), pp. 552-559, 2007.
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    2010 Jean-Louis Durrieu EPFL
    
    """
    # handling errors:
    if i is None or ie is None:
        print "The input arrays should both be provided."
        raise ValueError("Not enough input arguments.")
    cdef int nsrc = ie.shape[0]
    cdef int nsampl = ie.shape[1]
    cdef int nchan = ie.shape[2]
    cdef int nsrc2 = i.shape[0]
    cdef int nsampl2 = i.shape[1]
    cdef int nchan2 = i.shape[2]
    if nsrc != nsrc2 or nsampl != nsampl2 or nchan != nchan2:
        raise ValueError("The input arrays should have the same dimensions.")
    
    SDR = np.zeros([nsrc,])
    ISR = np.zeros([nsrc,])
    SIR = np.zeros([nsrc,])
    SAR = np.zeros([nsrc,])

    cdef Py_ssize_t src
    cdef cnp.ndarray[dtype_t, ndim=2] s_true
    cdef cnp.ndarray[dtype_t, ndim=2] e_spat
    cdef cnp.ndarray[dtype_t, ndim=2] e_interf
    cdef cnp.ndarray[dtype_t, ndim=2] e_artif
    
    for src in range(nsrc):
        print "Estimating the decomposition for estimated source ", src
        s_true, e_spat, e_interf, e_artif = bss_decomp_mtifilt(ie[src,:,:],i,src,delaySize=delaySize)
        print "Computing the criteria"
        SDR[src], ISR[src], SIR[src], SAR[src] = bss_image_crit(s_true, e_spat, e_interf, e_artif)
        ##del s_true, e_spat, e_interf, e_artif
        
    return SDR, ISR, SIR, SAR

def bss_decomp_mtifilt(est_source, original_sources, tgt_src, delaySize=1):
    """
    % BSS_DECOMP_MTIFILT Decomposition of an estimated source image into four
    % components representing respectively the true source image, spatial (or
    % filtering) distortion, interference and artifacts, derived from the true
    % source images using multichannel time-invariant filters.
    %
    % [s_true,e_spat,e_interf,e_artif]=bss_decomp_mtifilt(se,s,j,flen)
    %
    % Inputs:
    % se: nchan x nsampl matrix containing the estimated source image
    %     (one row per channel)
    % s: nsrc x nsampl x nchan matrix containing the true source images
    % j: source index corresponding to the estimated source image in s
    % flen: length of the multichannel time-invariant filters in samples
    %
    % Outputs:
    % s_true: nchan x nsampl matrix containing the true source image
    %         (one row per channel)
    % e_spat: nchan x nsampl matrix containing the spatial (or filtering)
    %         distortion component
    % e_interf: nchan x nsampl matrix containing the interference component
    % e_artif: nchan x nsampl matrix containing the artifacts component
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    % Copyright 2007-2008 Emmanuel Vincent
    % This software is distributed under the terms of the GNU Public License
    % version 3 (http://www.gnu.org/licenses/gpl.txt)
    % If you find it useful, please cite the following reference:
    % Emmanuel Vincent, Hiroshi Sawada, Pau Bofill, Shoji Makino and Justinian
    % P. Rosca, "First stereo audio source separation evaluation campaign:
    % data, algorithms and results," In Proc. Int. Conf. on Independent
    % Component Analysis and Blind Source Separation (ICA), pp. 552-559, 2007.
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    2010 Jean-Louis Durrieu EPFL
    """
    # handling the errors on the arguments:
    nsampl2, nchan2 = est_source.shape
    nsrc, nsampl, nchan = original_sources.shape
    if nchan2 != nchan or nsampl2 != nsampl:
        raise ValueError("Dimensions of the inputs are not matching.")
    
    # Decomposing:
    s_true = np.vstack([original_sources[tgt_src,:,:], np.zeros((delaySize - 1, nchan))]) 
    e_spat = project(est_source, np.array([original_sources[tgt_src,:,:]]), delaySize) - s_true
    e_interf = project(est_source, original_sources, delaySize) - s_true - e_spat
    e_artif = np.vstack([est_source, np.zeros((delaySize - 1, nchan))]) - s_true - e_spat - e_interf

    # for debugging only:
    if True:
        print "Writing the decomposition signals of source ", tgt_src, "to files."
        from scikits.audiolab import wavwrite
        wavwrite(data=s_true, filename="s_true_"+str(tgt_src)+".wav", fs=44100)
        wavwrite(data=e_spat, filename="e_spat_"+str(tgt_src)+".wav", fs=44100)
        wavwrite(data=e_interf, filename="e_interf_"+str(tgt_src)+".wav", fs=44100)
        wavwrite(data=e_artif, filename="e_artif_"+str(tgt_src)+".wav", fs=44100)
        
    return s_true, e_spat, e_interf, e_artif

@cython.boundscheck(False)
@cython.wraparound(False)
def project(cnp.ndarray[dtype_t, ndim=2] est_source,
            cnp.ndarray[dtype_t, ndim=3] original_sources,
            int delaySize):
    """
    orthogonal projection of est_source onto original_sources
    
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    % Copyright 2007-2008 Emmanuel Vincent
    % This software is distributed under the terms of the GNU Public License
    % version 3 (http://www.gnu.org/licenses/gpl.txt)
    % If you find it useful, please cite the following reference:
    % Emmanuel Vincent, Hiroshi Sawada, Pau Bofill, Shoji Makino and Justinian
    % P. Rosca, "First stereo audio source separation evaluation campaign:
    % data, algorithms and results," In Proc. Int. Conf. on Independent
    % Component Analysis and Blind Source Separation (ICA), pp. 552-559, 2007.
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    2010 Jean-Louis Durrieu EPFL
    """
    cdef Py_ssize_t k1, k2, k3, k, l
    cdef int nsrc = original_sources.shape[0]
    cdef int nsampl = original_sources.shape[1]
    cdef int nchan = original_sources.shape[2]
    
    original_sources = np.hstack([original_sources, np.zeros((nsrc, delaySize - 1, nchan))])
    cdef int fftlen = nextpow2(nsampl + delaySize - 1)
    sourcesFT = np.fft.fft(original_sources, axis=1, n=fftlen)
    estFT = np.fft.fft(est_source, axis=0, n=fftlen)
    # inner product between delayed versions of original sources:
    print "Computing the inner products between delayed version of the original sources."
    G = np.zeros([nchan*nsrc*delaySize, nchan*nsrc*delaySize])
    ## cdef cnp.ndarray[dtypeC_t, ndim=1] convSrcFT
    cdef cnp.ndarray[dtype_t, ndim=2] ss = np.zeros([delaySize, delaySize])
    for k1 in range(nchan):
        for k2 in range(nsrc):
            k = k1 + nchan * k2
            for l in range(k+1):
                k4 = l / nchan
                k3 = l - nchan * k4
                ## print k, " et ", k3, k4
                convSrcFT = sourcesFT[k2,:,k1] * np.conjugate(sourcesFT[k4,:,k3])
                convSrcFT = np.real(np.fft.ifft(convSrcFT))
                ss = scpla.toeplitz(convSrcFT[np.r_[0, np.arange(fftlen-1,
                                                                 fftlen-delaySize,
                                                                 -1)]],
                                    convSrcFT[0:delaySize])
                G[k*delaySize:k*delaySize+delaySize][:,l*delaySize:l*delaySize+delaySize] = ss
                G[l*delaySize:l*delaySize+delaySize][:,k*delaySize:k*delaySize+delaySize] = ss.T
                
    # inner product between estimated and delayed sources:
    print "Computing the inner products between delayed version of the estimated and original sources."
    D = np.zeros([nchan*nsrc*delaySize, nchan])
    for k1 in range(nchan):
        for k2 in range(nsrc):
            k = k1 + nchan * k2
            for k3 in range(nchan):
                convSrcFT = sourcesFT[k2,:,k1] * \
                            np.conj(estFT[:, k3])
                convSrcFT = np.real(np.fft.ifft(convSrcFT))
                D[k*delaySize:k*delaySize+delaySize, k3] = convSrcFT[np.r_[0,
                                                                           np.arange(fftlen-1,
                                                                                     fftlen-delaySize,
                                                                                     -1)]]
                 
    # computing projection
    print "Projection"
    ## print "Inversion of covariance matrix"
    ## invG = scp.linalg.inv(G)
    ## print "Matrix product"
    ## C = np.dot(invG, D)
    print "    using the solve function from scipy.linalg"
    # owing to this discussing on Nabble:
    # http://old.nabble.com/solving-linear-equations---td20348803.html
    C = scpla.solve(G,D)
    # filtering
    sproj = np.zeros([nsampl+delaySize-1, nchan])
    for k1 in range(nchan):
        for k2 in range(nsrc):
            k = k1 + nchan * k2
            for k3 in range(nchan):
                print "    projecting on source ", k2, " channel ", k1, " for channel ", k3
                sproj[:, k3] = sproj[:, k3] + scpsig.lfilter(C[k*delaySize:
                                                               k*delaySize+delaySize, k3],
                                                             1, original_sources[k2, :, k1])
                
    return sproj

def bss_image_crit(s_true, e_spat, e_interf, e_artif):
    """
    % BSS_IMAGE_CRIT Measurement of the separation quality for a given source
    % image in terms of true source, spatial (or filtering) distortion,
    % interference and artifacts.
    %
    % [SDR,ISR,SIR,SAR]=bss_image_crit(s_true,e_spat,e_interf,e_artif)
    %
    % Inputs:
    % s_true: nchan x nsampl matrix containing the true source image
    %         (one row per channel)
    % e_spat: nchan x nsampl matrix containing the spatial (or filtering)
    %         distortion component
    % e_interf: nchan x nsampl matrix containing the interference component
    % e_artif: nchan x nsampl matrix containing the artifacts component
    %
    % Outputs:
    % SDR: Signal to Distortion Ratio
    % ISR: source Image to Spatial distortion Ratio
    % SIR: Source to Interference Ratio
    % SAR: Sources to Artifacts Ratio
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    % Copyright 2007-2008 Emmanuel Vincent
    % This software is distributed under the terms of the GNU Public License
    % version 3 (http://www.gnu.org/licenses/gpl.txt)
    % If you find it useful, please cite the following reference:
    % Emmanuel Vincent, Hiroshi Sawada, Pau Bofill, Shoji Makino and Justinian
    % P. Rosca, "First stereo audio source separation evaluation campaign:
    % data, algorithms and results," In Proc. Int. Conf. on Independent
    % Component Analysis and Blind Source Separation (ICA), pp. 552-559, 2007.
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    2010 Jean-Louis Durrieu EPFL
    """
    # checking the arguments in input
    nchant, nsamplt = s_true.shape
    nchans, nsampls = e_spat.shape
    nchani, nsampli = e_interf.shape
    nchana, nsampla = e_artif.shape
    if nchant != nchans or nchant != nchani or nchant != nchana:
        raise ValueError('All the components must have the same number of channels.')
    if nsamplt != nsampls or nsamplt != nsampli or nsamplt != nsampla:
        raise ValueError('All the components must have the same duration.')
    # Energy ratios
    # SDR
    SDR = 10 * np.log10(np.sum(s_true ** 2) /
                        np.sum((e_spat + e_interf + e_artif) ** 2))
    # ISR
    ISR = 10 * np.log10(np.sum(s_true ** 2) /
                        np.sum(e_spat ** 2))
    # SIR
    SIR = 10 * np.log10(np.sum((s_true + e_spat) ** 2) /
                        np.sum(e_interf ** 2))
    # SAR
    SAR = 10 * np.log10(np.sum((s_true + e_spat + e_interf) ** 2) /
                        np.sum(e_artif ** 2))
    
    return SDR, ISR, SIR, SAR

