#! /usr/bin/env python

import numpy as np

def framewiseEval(resTracks, groundTruthTracks):
    GTTracks = groundTruthTracks
    # aligning the tracks:
    Tref = GTTracks.shape[0]
    refTimes = GTTracks[:,0]
    estTimes = resTracks[:,0]
    reference = np.zeros([Tref, GTTracks.shape[1]-1])
    reference[:,:] = GTTracks[:,1:]
    print reference.shape
    
    nTracks = resTracks.shape[1] - 1
    newResTracks = np.zeros([Tref, nTracks])
    for i in range(Tref):
        indexMin = np.argmin(np.abs(refTimes[i] - estTimes))
        newResTracks[i,:] = resTracks[indexMin,1:]
    
    resTracks0 = np.copy(newResTracks)
    GTTracks0 = np.copy(reference)
    
    # Consider negative frequency values as 0:
    newResTracks[newResTracks < 0] = 0
    # Setting same number of tracks:
    ## nTracks = np.maximum(nTracks, reference.shape[1])

    print newResTracks.shape
    
    # setting the boundaries for tolerance of error:
    reference_low = 0.97 * reference
    reference_hig = 1.03 * reference
    
    # values for score computation
    TP = np.zeros(Tref) # True Positives
    FN = np.zeros(Tref) # False Negatives
    TN = np.zeros(Tref) # True Negatives
    
    for n in range(Tref):
        for track in range(nTracks):
            for track2 in range(reference.shape[1]):
                if reference_low[n, track2] < newResTracks[n, track] and \
                       newResTracks[n, track] < reference_hig[n, track2] and \
                       reference[n, track2] > 0:
                    TP[n] += 1
                    # inhibiting the TP match
                    newResTracks[n, track] = -1
                    reference_low[n, track2] = -1
                    reference_hig[n, track2] = -1
                    reference[n, track2] = -1
    
    FP = np.sum(newResTracks>0) # True Negatives
    # True Negatives - not sure if this quantity is right
    TN = np.minimum(np.sum(reference<=0,
                           axis=1),
                    np.sum(np.array(newResTracks==0) + \
                           np.array(newResTracks<-1),
                           axis=1))
    Ncorr = np.copy(TP) # number of correctly estimated pitches for each frames (MIREX 2007 criteria)
    TP = np.sum(TP) # total TP
    FN = np.maximum(0, np.sum(np.array(newResTracks==0) + \
                              np.array(newResTracks<-1),
                              axis=1) -\
                    np.sum(reference<=0,
                           axis=1)) # False Negatives, per frame
    TN = np.sum(TN) # total TN
    FN = np.sum(FN) # total FN

    # dictionary containing all of the desired values
    resStruct = {}
    resStruct['TP'] = TP
    resStruct['TN'] = TN
    resStruct['FP'] = FP
    resStruct['FN'] = FN
    resStruct['Precision'] = 100.0 * TP / np.double(TP+FP)
    resStruct['Recall'] = 100.0 * TP / np.double(np.sum(GTTracks0>0))# np.sum(reference!=0, dtype=np.double)
    resStruct['FMeasure'] = 2.0 * resStruct['Precision'] * resStruct['Recall'] / (resStruct['Precision'] + resStruct['Recall'])
    resStruct['Accuracy'] = 100.0 * (TP + TN) / np.double(TP + TN + FN) # recall, including silence in the classes to retrieve. 
    
    # Additional MIREX 2007 evaluation criteria:
    Nref = np.sum(GTTracks0>0, axis=1, dtype=np.double)
    Nsys = np.sum(resTracks0>0, axis=1, dtype=np.double)
    
    resStruct['AccuracyMirex07'] = 100.0 * TP / np.double(TP+FN+FP)
    
    NrefTotal = np.sum(Nref, dtype=np.double)
    resStruct['Mirex07Etot'] = 100.0 * \
                               np.sum(np.maximum(Nref,Nsys) - \
                                      Ncorr) / \
                                      NrefTotal
    resStruct['Mirex07Esub'] = 100.0 * \
                               np.sum(np.minimum(Nref,Nsys) - \
                                      Ncorr) / \
                                      NrefTotal
    resStruct['Mirex07Emis'] = 100.0 * \
                               np.sum(np.maximum(0, Nref-Nsys)) / \
                                      NrefTotal
    resStruct['Mirex07Efal'] = 100.0 * \
                               np.sum(np.maximum(0, Nsys-Nref)) / \
                                      NrefTotal
    
    return resStruct, GTTracks0, resTracks0

def framewiseMono(resTracks, groundTruthTracks):
    GTTracks = groundTruthTracks
    # aligning the tracks:
    Tref = GTTracks.shape[0]
    refTimes = GTTracks[:,0]
    estTimes = resTracks[:,0]
    reference = GTTracks[:,1]
    
    newResTracks = np.zeros(Tref)
    for i in range(Tref):
        indexMin = np.argmin(np.abs(refTimes[i] - estTimes))
        newResTracks[i] = resTracks[indexMin,1]
    
    resTracks0 = np.copy(newResTracks)
    GTTracks0 = np.copy(reference)
    
    # Consider negative frequency values as 0:
    newResTracks[newResTracks < 0] = 0
    
    errorInSemitone = np.zeros(Tref)
    for n in range(Tref):
        if reference[n] > 0 and newResTracks[n] != 0:
            errorInSemitone[n] = 12.0 * np.log2(np.abs(newResTracks[n])/np.double(reference[n]))
        
    return errorInSemitone

def compareFilesByName(fileGT, fileRes):
    GTTracks = np.loadtxt(fileGT)
    resTracks = np.loadtxt(fileRes)
    
    errorInSemitone = framewiseMono(resTracks, GTTracks)
    resStruct, GTTracks0, resTracks0 = framewiseEval(resTracks, GTTracks)
    
    return errorInSemitone, resStruct, GTTracks0, resTracks0
