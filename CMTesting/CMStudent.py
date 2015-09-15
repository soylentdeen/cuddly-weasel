import MoogPy
import numpy
import scipy
import matplotlib.pyplot as pyplot
import AstroUtils
import MoogTools
import SpectralTools
import pyfits

def calculateCM(SynthObj, nominalWave, nominalSpectrum):
    solarWl = SynthObj.solarSpectrum.wave
    solarFl = SynthObj.solarSpectrum.flux
    resolution = 45000.0
    nLines = SynthObj.lineList.numLines
    nModes = 2*nLines+3

    IM = numpy.zeros((nModes, len(solarWl)))
    stroke = numpy.ones(nModes)
    target = numpy.ones(nModes) * 0.1
    factor = numpy.ones(nModes)
    factor[-1] = 0.005                  # Continuum Shift
    factor[-2] = 0.1                    # WL Shift
    factor[-3] = 0.01                # Smoothing
    for i in range(nLines):
        SynthObj.lineList.writeLineLists(i)
        wave, flux = SynthObj.run()
        stroke[i*2] = SynthObj.lineList.getGf(i)/5.0
        stroke[i*2+1] = SynthObj.lineList.getVdW(i)/30.0
        """
        while ((factor[i] < 0.9) | (factor[i] > 1.1)):
            stroke[i] *= factor[i]
            SynthObj.lineList.perturbGf(i, stroke[i])
            SynthObj.lineList.writeLineLists(i,partial=True)
            wave, plus = SynthObj.run()
            wave, plus = SpectralTools.resample(wave, plus, resolution)
            SynthObj.lineList.perturbGf(i, -2.0*stroke[i])
            SynthObj.lineList.writeLineLists(i,partial=True)
            wave, minus = SynthObj.run()
            wave, minus = SpectralTools.resample(wave, minus, resolution)
            SynthObj.lineList.perturbGf(i, stroke[i])
            factor[i] = numpy.abs(target[i]/(numpy.min(plus)-numpy.min(minus)))
            print factor[i]
            raw_input()
        #"""

    for i in range(nLines):
        #  log gf
        SynthObj.lineList.perturbGf(i, stroke[i*2])
        SynthObj.lineList.writeLineLists(i)
        wave, plus = SynthObj.run()
        newWave, plus = SpectralTools.resample(wave, plus, resolution)
        SynthObj.lineList.perturbGf(i, -2.0*stroke[i*2])
        SynthObj.lineList.writeLineLists(i)
        wave, minus = SynthObj.run()
        newWave, minus = SpectralTools.resample(wave, minus, resolution)
        SynthObj.lineList.perturbGf(i, stroke[i*2])
        IM[i*2,:] = SpectralTools.interpolate_spectrum(newWave, solarWl,
                        (plus - minus)/(2.0*stroke[i*2]), pad=0.0)

        # damping
        SynthObj.lineList.perturbVdW(i, stroke[i*2+1])
        SynthObj.lineList.writeLineLists(i)
        wave, plus = SynthObj.run()
        newWave, plus = SpectralTools.resample(wave, plus, resolution)
        SynthObj.lineList.perturbVdW(i, -2.0*stroke[i*2+1])
        SynthObj.lineList.writeLineLists(i)
        wave, minus = SynthObj.run()
        newWave, minus = SpectralTools.resample(wave, minus, resolution)
        SynthObj.lineList.perturbVdW(i, stroke[i*2+1])
        IM[i*2+1,:] = SpectralTools.interpolate_spectrum(newWave, solarWl,
                        (plus - minus)/(2.0*stroke[i*2+1]), pad=0.0)



    #Continuum Level
    stroke[-1] *= factor[-1]
    plus = nominalSpectrum + stroke[-1]
    newWave, plus = SpectralTools.resample(nominalWave, plus, resolution)
    minus = nominalSpectrum - stroke[-1]
    newWave, minus = SpectralTools.resample(nominalWave, minus, resolution)
    factor[-1] = 1.0

    IM[-1, :] = SpectralTools.interpolate_spectrum(newWave, solarWl, 
        (plus-minus)/(2.0*stroke[-1]), pad=0.0)

    #Wavelength Shift
    stroke[-2] *= factor[-2]
    plus = SpectralTools.interpolate_spectrum(wave, wave-stroke[-2], nominalSpectrum,
            pad=True)
    newWave, plus = SpectralTools.resample(wave, plus, resolution)
    minus = SpectralTools.interpolate_spectrum(wave, wave+stroke[-2], nominalSpectrum,
            pad=True)
    newWave, minus = SpectralTools.resample(wave, minus, resolution)
    factor[-2] = 1.0
    IM[-2, :] = SpectralTools.interpolate_spectrum(newWave, solarWl, 
                (plus-minus)/(2.0*stroke[-2]), pad=0.0)

    #"""
    #Instrumental Smoothing
    stroke[-3] *= factor[-3]
    wavePlus, plus = SpectralTools.resample(wave, nominalSpectrum, resolution*(1.0+stroke[-3]))
    waveMinus, minus = SpectralTools.resample(wave, nominalSpectrum, resolution*(1.0-stroke[-3]))
    diffx, diffy = SpectralTools.diff_spectra(wavePlus, plus, waveMinus, minus, pad=True)
    IM[-3,:] = SpectralTools.interpolate_spectrum(diffx, solarWl, diffy/(2.0*stroke[-3]), pad=0.0)
    #"""


    hdu = pyfits.PrimaryHDU(IM)
    hdu.writeto("InteractionMatrix.fits", clobber=True)
    #nFilt = Synth.lineList.numLines-2
    dims = IM.shape
    U,S,V = scipy.linalg.svd(IM)
    D = 1.0/S
    #D = 1.0/(S[0:-nFilt])
    #S[-nFilt:] = 0.0
    newS = numpy.zeros((dims[0], dims[1]))
    I = [i for i in range(dims[1])]
    for i in range(len(D)):
        newS[i][i] = D[i]

    S = newS.copy()
    CM = numpy.array(scipy.matrix(V.T.dot(S.T.dot(U.T)),dtype=numpy.float32)).T

    hdu = pyfits.PrimaryHDU(CM)
    hdu.writeto('CommandMatrix.fits', clobber=True)



configFile = 'CMStudent.cfg'

diffplot = True

Synth = MoogTools.Moog(configFile)
Synth.lineList.writeLineLists()
Synth.parameterFile.writeParFile()

solarWave = Synth.solarSpectrum.wave#+0.2
solarFlux = Synth.solarSpectrum.flux#+0.004

continuum = 0.0
wlOffset = 0.0
resolution = 45000


nominalWavelength, nominalSpectrum = Synth.run()
wave, spectrum = SpectralTools.resample(nominalWavelength, nominalSpectrum, resolution)

if True:
    calculateCM(Synth, nominalWavelength, nominalSpectrum)

CM = pyfits.getdata("CommandMatrix.fits")

f1 = pyplot.figure(0)
f1.clear()
ax1 = f1.add_axes([0.1, 0.1, 0.8, 0.8])

cb = ax1.matshow(CM, aspect='auto')
blah = pyplot.colorbar(cb)
f1.show()

Spectra = [spectrum]
Wavelengths = [wave]

Gain = 0.35

f2 = pyplot.figure(1)
f2.clear()
ax2 = f2.add_axes([0.1, 0.1, 0.8, 0.8])

while True:
    x, difference = SpectralTools.diff_spectra(solarWave, solarFlux, 
            Wavelengths[-1], Spectra[-1], pad=True)
    difference[Spectra[-1] == 0] = 0.0
    command = Gain*(CM.dot(difference))
    #command[[i*2+1 for i in range(Synth.lineList.numLines)]] = 0.0
    
    Synth.lineList.applyCorrection(command[:-2])
    continuum = continuum+command[-1]
    wlOffset = wlOffset+command[-2]
    resolution = resolution*(1.0+command[-3])
    wave, flux = Synth.run()
    #Spectra.append(wave)
    wavelength, spectrum = SpectralTools.resample(wave, flux, resolution)
    Spectra.append(spectrum+continuum)
    Wavelengths.append(wavelength+wlOffset)

    ax2.clear()
    if diffplot:
        x, difference = SpectralTools.diff_spectra(solarWave, solarFlux, 
            Wavelengths[-1], Spectra[-1], pad=True)
        difference[Spectra[-1] == 0] = 0.0
        ax2.plot(x, difference)
    else:
        ax2.plot(solarWave, solarFlux)
        for w, spec in zip(Wavelengths, Spectra):
            ax2.plot(w, spec)
    f2.show()
    print numpy.log10(Synth.lineList.getGf(0)), numpy.log10(Synth.lineList.getVdW(0))
    print numpy.log10(Synth.lineList.getGf(1)), numpy.log10(Synth.lineList.getVdW(1))
    print numpy.log10(Synth.lineList.getGf(2)), numpy.log10(Synth.lineList.getVdW(2))
    print numpy.log10(Synth.lineList.getGf(3)), numpy.log10(Synth.lineList.getVdW(3))
    print numpy.log10(Synth.lineList.getGf(4)), numpy.log10(Synth.lineList.getVdW(4))
    print command[1], command[3], command[5], command[7], command[9]
    print continuum, wlOffset, resolution
    print command[-1], command[-2], command[-3]
    raw_input()


