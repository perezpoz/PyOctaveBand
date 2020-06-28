#  Copyright (c) 2020. Jose M. Requena-Plens
"""
Octave-Band and Fractional Octave-Band filter.
"""

import numpy as np
from scipy import signal
import matplotlib.pyplot as plt

# Public methods
__all__ = ['octaveFilter', 'getANSIFrequencies', 'normalizedFreq']


def octaveFilter(x, fs, fraction=1, order=6, limits=None, show=0):
    """
    Filter a signal with octave or fractional octave filter bank. This method uses a Butterworth filter with
    Second-Order Sections coefficients. To obtain the correct coefficients, a subsampling is applied to the signal in
    each filtered band.

    :param x: Signal
    :param fs: Sample rate
    :param fraction: Bandwidth 'b'. Examples: 1/3-octave b=3, 1-octave b=1, 2/3-octave b = 3/2. [Optional] Default: 1.
    :param order: Order of Butterworth filter. [Optional] Default: 6.
    :param limits: Lower and upper limit frequencies. [Optional] Default [12,20000]
    :param show: Boolean for plot o not the filter response.
    :returns: Sound Pressure Level and Frequency array
    """

    if limits is None:
        limits = [12, 20000]

    # List type for signal var
    x = _typesignal(x)

    # Generate frequency array
    freq, freq_d, freq_u = _genfreqs(limits, fraction, fs)

    # Calculate the downsampling factor (array of integers with size [freq])
    factor = _downsamplingfactor(freq_u, fs)

    # Get SOS filter coefficients (3D - matrix with size: [freq,order,6])
    sos = _butterSOSfilter(freq, freq_d, freq_u, fs, order, factor, show)

    # Create array with SPL for each frequency band
    spl = np.zeros([len(freq)])
    for jj in range(len(freq)):
        print('\r', 'Processing: {:.1f} Hz'.format(freq[jj]), end='')
        sd = signal.decimate(x, int(factor[jj]))
        y = signal.sosfilt(sos[jj], sd)
        spl[jj] = 20 * np.log10(np.std(y) / 2e-5)
    print('\rDone!')
    return spl.tolist(), freq


def _typesignal(x):
    if type(x) is list:
        return x
    elif type(x) is np.ndarray:
        return x.tolist()
    elif type(x) is tuple:
        return list(x)


def _butterSOSfilter(freq, freq_d, freq_u, fs, order, factor, show=0):
    # Initialize coefficients matrix
    sos = [[[]] for i in range(len(freq))]
    # Generate coefficients for each frequency band
    for idx, (lower, upper) in enumerate(zip(freq_d, freq_u)):
        # Downsampling to improve filter coefficients
        Fsd = fs / factor[idx]  # New sampling rate
        # Butterworth Filter with SOS coefficients
        sos[idx] = signal.butter(
            N=order,
            Wn=np.array([lower, upper]) / (Fsd / 2),
            btype='bandpass',
            analog=False,
            output='sos')

    if show:
        _showfilter(sos, freq, freq_u, freq_d, fs, factor)

    return sos


def _showfilter(sos, freq, freq_u, freq_d, fs, factor):
    N = 8192
    w = np.zeros([N, len(freq)])
    h = np.zeros([N, len(freq)], dtype=np.complex_)

    for idx in range(len(freq)):
        Fsd = fs / factor[idx]  # New sampling rate
        w[:, idx], h[:, idx] = signal.sosfreqz(
            sos[idx],
            worN=N,
            whole=False,
            fs=Fsd)

    fig, ax = plt.subplots()
    ax.semilogx(w, 20 * np.log10(abs(h) + np.finfo(float).eps), 'b')
    ax.grid(which='major')
    ax.grid(which='minor', linestyle=':')
    ax.set_xlabel(r'Frequency [Hz]')
    ax.set_ylabel('Amplitude [dB]')
    ax.set_title('Second-Order Sections - Butterworth Filter')
    plt.xlim(freq_d[0] * 0.8, freq_u[-1] * 1.2)
    plt.ylim(-4, 1)
    ax.set_xticks([16, 31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000])
    ax.set_xticklabels(['16', '31.5', '63', '125', '250', '500', '1k', '2k', '4k', '8k', '16k'])
    plt.show()


def _genfreqs(limits, fraction, fs):
    # Generate frequencies
    freq, freq_d, freq_u = getANSIFrequencies(fraction, limits)

    # Remove outer frequency to prevent filter error (fs/2 < freq)
    freq, freq_d, freq_u = _deleteOuters(freq, freq_d, freq_u, fs)

    return freq, freq_d, freq_u


def normalizedFreq(fraction):
    """
    Normalized frequencies for one-octave and third-octave band. [IEC 61260-1-2014]

    :param fraction: Octave type, for one octave fraction=1, for third-octave fraction=3
    :type fraction: int
    :returns: frequencies array
    :rtype: list
    """
    predefined = {1: _oneOctave(),
                  3: _thirdOctave(),
                  }
    return predefined[fraction]


def _thirdOctave():
    # IEC 61260 - 1 - 2014 (added 12.5, 16, 20 Hz)
    return [12.5, 16, 20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600,
            2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000]


def _oneOctave():
    # IEC 61260 - 1 - 2014 (added 16 Hz)
    return [16, 31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]


def _deleteOuters(freq, freq_d, freq_u, fs):
    idx = np.asarray(np.where(np.array(freq_u) > fs / 2))
    if any(idx[0]):
        _printwarn('Low sampling rate, frequencies above fs/2 will be removed')
        freq = np.delete(freq, idx).tolist()
        freq_d = np.delete(freq_d, idx).tolist()
        freq_u = np.delete(freq_u, idx).tolist()
    return freq, freq_d, freq_u


def getANSIFrequencies(fraction, limits=None):
    """ ANSI s1.11-2004 && IEC 61260-1-2014
    Array of frequencies and its edges according to the ANSI and IEC standard.

    :param fraction: Bandwidth 'b'. Examples: 1/3-octave b=3, 1-octave b=1, 2/3-octave b = 3/2
    :param limits: It is a list with the minimum and maximum frequency that the array should have. Example: [12,20000]
    :returns: Frequency array, lower edge array and upper edge array
    :rtype: list, list, list
    """

    if limits is None:
        limits = [12, 20000]

    # Octave ratio G (ANSI s1.11, 3.2, pg. 2)
    G = 10 ** (3 / 10)  # Or G = 2
    # Reference frequency (ANSI s1.11, 3.4, pg. 2)
    fr = 1000

    # Get starting index 'x' and first center frequency
    x = _initindex(limits[0], fr, G, fraction)
    freq = _ratio(G, x, fraction) * fr

    # Get each frequency until reach maximum frequency
    freq_x = 0
    while freq_x * _bandedge(G, fraction) < limits[1]:
        # Increase index
        x = x + 1
        # New frequency
        freq_x = _ratio(G, x, fraction) * fr
        # Store new frequency
        freq = np.append(freq, freq_x)

    # Get band-edges
    freq_d = freq / _bandedge(G, fraction)
    freq_u = freq * _bandedge(G, fraction)

    return freq.tolist(), freq_d.tolist(), freq_u.tolist()


def _initindex(f, fr, G, b):
    if b % 2:  # ODD ('x' solve from ANSI s1.11, eq. 3)
        return np.round((b * np.log(f / fr) + 30 * np.log(G)) / np.log(G))
    else:  # EVEN ('x' solve from ANSI s1.11, eq. 4)
        return np.round((2 * b * np.log(f / fr) + 59 * np.log(G)) / (2 * np.log(G)))


def _ratio(G, x, b):
    if b % 2:  # ODD (ANSI s1.11, eq. 3)
        return G ** ((x - 30) / b)
    else:  # EVEN (ANSI s1.11, eq. 4)
        return G ** ((2 * x - 59) / (2 * b))


def _bandedge(G, b):
    # Band-edge ratio (ANSI s1.11, 3.7, pg. 3)
    return G ** (1 / (2 * b))


def _printwarn(msg):
    print('*********\n' + msg + '\n*********')


def _downsamplingfactor(freq, fs):
    factor = ((fs / 2) / np.array(freq)).astype('int')
    for ii in range(len(factor)):
        factor[ii] = max(min(factor[ii], 50), 1)  # Factor between 1<factor<50
    return factor