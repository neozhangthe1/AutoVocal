#! /usr/env python

# a script to run BSS eval on several audio files

import numpy as np
import sys

## from bss_eval_images_nosort import *
sys.path.append('/users/jeanlouis/work/python/tools/bsseval/')
import BSSeval
import scikits.audiolab as al

if __name__ == '__main__':
    import optparse
    
    usage = "usage: %prog [options] true_music_source_filename \\\n"+\
            "                         true_vocal_source_filename \\\n"+\
            "                         estimated_music_source_filename \\\n"+\
            "                         estimated_vocal_source_filename\n\n"+\
            "The input files should be wav files (with slight\n"+\
            "modifications, one may be able to use other formats if needed.)"
    parser = optparse.OptionParser(usage)
    # Name of the output files:
    parser.add_option("-o", "--output-file",
                      dest="output_file", type="string",
                      help="name of the output file for the resulting\n"+\
                           "scores (text file)",
                      default="bsseval-results.txt")
    parser.add_option("-d", "--delay-size",
                      dest="delaySize", type="int",
                      help="integer giving the delay size in the\n"+\
                           "computation of the delayed versions",
                      default=1)
    parser.add_option("-m", "--not-music",
                      dest="isMusicProvided", action="store_false",
                      help="add this option if you provide the mix instead of the music track",
                      default=True)

    (options, args) = parser.parse_args()
    if len(args) == 0:
        parser.error("incorrect number of arguments, use option -h for help.")
    elif len(args) == 4:
        estMusFile = args[2]
        estVocFile = args[3]
        truMusFile = args[0]
        truVocFile = args[1]
    else:
        parser.error("This program does not support this number of arguments,\n"\
                     "use option -h for help.")
    ##estMusFile = '/home/durrieu/work/python/separateLeadAccompanimentStereo/estimated_music.wav'
    ##    estVocFile = '/home/durrieu/work/python/separateLeadAccompanimentStereo/estimated_solo.wav'
    ##    truMusFile = '/home/durrieu/work/BDD/separation/sisec/professionallyProducedMusicRecordings/dev1/dev1__tamy-que_pena_tanto_faz__tracks/dev1__tamy-que_pena_tanto_faz__snip_6_19__guitar.wav'
    ##    truVocFile = '/home/durrieu/work/BDD/separation/sisec/professionallyProducedMusicRecordings/dev1/dev1__tamy-que_pena_tanto_faz__tracks/dev1__tamy-que_pena_tanto_faz__snip_6_19__vocals.wav'
    
    est_mus, fs, enc = al.wavread(estMusFile)
    est_voc, fs, enc = al.wavread(estVocFile)
    if options.isMusicProvided:
        tru_mus, fs, enc = al.wavread(truMusFile)
        tru_voc, fs, enc = al.wavread(truVocFile)
    else:
        tru_mix, fs, enc = al.wavread(truMusFile)
        tru_voc, fs, enc = al.wavread(truVocFile)
        tru_mus = tru_mix - tru_voc
        del tru_mix
    
    nsampl1, nchan1 = est_mus.shape 
    nsampl0, nchan0 = tru_voc.shape
    
    nsampl = np.minimum(nsampl0, nsampl1)
    nchan = nchan0
    
    ie = np.array([est_voc[np.arange(nsampl)], est_mus[np.arange(nsampl)]])
    del est_voc, est_mus
    i  = np.array([tru_voc[np.arange(nsampl)], tru_mus[np.arange(nsampl)]])
    del tru_voc, tru_mus
    
    SDR, ISR, SIR, SAR = BSSeval.bss_eval_images_nosort(ie,
                                                        i,
                                                        delaySize=options.delaySize)
    print "Results for file"+truVocFile[:-10]+":"
    print "SDR", SDR, "ISR", ISR, "SIR", SIR, "SAR", SAR
    
    fileIO = open(options.output_file, 'a')
    # writes a line, with:
    # SDRvoc, SDRmus, ISRv, ISRm, SIRv, SIRm, SARv, SARm
    fileIO.writelines("%f\t%f\t%f\t%f\t%f\t%f\t%f\t%f\n" %(SDR[0], SDR[1],
                                                         ISR[0], ISR[1],
                                                         SIR[0], SIR[1],
                                                         SAR[0], SAR[1]))
    fileIO.close()
