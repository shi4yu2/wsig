__author__ = 'ShY'
__copyright__ = 'Copyright 2019, SHY'
__version__ = '1.1.0 (20190304)'
__maintainer__ = 'ShY'
__email__ = 'shi4yu2@gmail.com'
__status__ = 'Pre-release'

"""Parse SESANE RIFF / WAVE file 
* RIFF format used by Alain Ghio: http://www.lpl-aix.fr/~ghio/
* Format description: http://www.lpl-aix.fr/~ghio/Doc/TN-FormatFichierSESANE_EVA_Wsig.pdf

Usage:

Reading SESANE files (Wsig Type RIFF format) or WAVE files
    f = wsig.open(file, 'r')
where file is either the name of a file or an open file pointer.
The open file pointer must have methods read(), seek(), and close().
When the setpos() and rewind() methods are not used, the seek() methods is not necessary.

This returns an instance of a class with the following public methods:
      # Added methods for WSIG
      getduration()       -- returns duration of signal
      getparaname()       -- returns type of measure
      getunit()           -- returns unit of measure 
      getsignaldynamic()  -- returns signal dynamic (for calibration)
      getvalueatmax()     -- returns max value (for calibration)
      getzero()           -- returns calibration at zero (for calibration)
    
      # Original methods for WAVE
      getnchannels()  -- returns number of audio channels (1 for
                         mono, 2 for stereo)
      getsampwidth()  -- returns sample width in bytes
      getframerate()  -- returns sampling frequency
      getnframes()    -- returns number of audio frames
      getcomptype()   -- returns compression type ('NONE' for linear samples)
      getcompname()   -- returns human-readable version of
                         compression type ('not compressed' linear samples)
      getparams()     -- returns a namedtuple consisting of all of the
                         above in the above order
      getmarkers()    -- returns None (for compatibility with the
                         aifc module)
      getmark(id)     -- raises an error since the mark does not
                         exist (for compatibility with the aifc module)
      readframes(n)   -- returns at most n frames of audio
      rewind()        -- rewind to the beginning of the audio stream
      setpos(pos)     -- seek to the specified position
      tell()          -- return the current position
      close()         -- close the instance (make it unusable)
The position returned by tell() and the position given to setpos()
are compatible and have nothing to do with the actual position in the
file.
The close() method is called automatically when the class instance
is destroyed.
"""

import builtins

__all__ = ["read", "towave", "Error", "WsigRead"]


class Error(Exception):
    pass


WAVE_FORMAT_PCM = 0x0001
WAVE_FORMAT_IEEE_FLOAT = 0x0003
WAVE_FORMAT_EXTENSIBLE = 0xfffe
KNOWN_WAVE_FORMATS = (WAVE_FORMAT_PCM, WAVE_FORMAT_IEEE_FLOAT)

_array_fmts = None, 'b', 'h', None, 'i'

import audioop
import struct
import sys
from chunk import Chunk
from struct import *
from collections import namedtuple
import warnings

_wave_params = namedtuple('_wave_params',
                          'nchannels sampwidth framerate '
                          'nframes comptype compname '
                          'duration paraname unit signaldynamic valueatmax zero')


##############################################################################################

class WsigRead:
    """Variables used in this class:

    These variables are available to the user through appropriate
    methods of this class:
    # Added variables
    _metaInfo -- Metadata from recording instrument

    _paraname -- name of parameter

    _unitname -- name of unit

    _s_max -- max value of the signal

    _s_min -- min value of the signal

    _czero -- calibration at zero

    _signaldynamic -- Signal Dynamic = cmax - czero

    _valueatmax -- Value at Max = imax + fmax / 1000000.0

    # Original variables
    _file -- the open file with methods read(), close(), and seek()
             set through the __init__() method
    _nchannels -- the number of audio channels
                 available through the getnchannels() method
    _nframes -- the number of audio frames
                available through the getnframes() method
    _framerate -- the sampling frequency
                  available through the getframerate() method
    _soundpos -- the position in the audio stream
                 available through the tell() method, set through the
                 setpos() method

    These variables are used internally only:
    # Added interval variables
    _

    # Original internal variables
    _fmt_chunk_read -- 1 iff the FMT chunk has been read
    _data_seek_needed -- 1 iff positioned correctly in audio
                         file for readframes()
    _data_chunk -- instantiation of a chunk class for the DATA chunk
    _framesize -- size of one frame in the file
    """

    def initfp(self, file):
        self._convert = None
        self._soundpos = 0
        self._file = Chunk(file, False, bigendian=0)
        if self._file.getname() != b'RIFF':
            raise Error('File does not start with RIFF id')
        self._filetype = self._file.read(4)
        if not (self._filetype == b'WSIG' or self._filetype == b'WAVE'):
            raise Error('not a SESANE or WAVE file')

        # Initialise chunk fetching
        self._fmt_chunk_read = 0
        self._sdsc_chunk_read = 0
        self._adsc_chunk_read = 0
        self._list_chunk_read = 0
        self._info_chunk_read = 0
        self._data_chunk = None
        self._data_seek_needed = 1

        while 1:
            # if self._data_seek_needed == 0:
            #     break
            self._data_seek_needed = 1
            try:
                chunk = Chunk(self._file, bigendian=0)
            except EOFError:
                break
            # WAVE type
            if self._filetype == b'WAVE':
                chunkname = chunk.getname()
                if chunkname == b'fmt ':
                    self._read_fmt_chunk(chunk)
                    self._fmt_chunk_read = 1
                elif chunkname == b'data':
                    if not self._fmt_chunk_read:
                        raise Error('data chunk before fmt chunk')
                    self._data_chunk = chunk
                    self._nframes = chunk.chunksize // self._framesize
                    self._data_seek_needed = 0
                    break
                chunk.skip()

            # WSIG type
            elif self._filetype == b'WSIG':
                chunkname = chunk.getname()
                if chunkname == b'fmt ':
                    self._read_fmt_chunk(chunk)
                    self._fmt_chunk_read = 1
                elif chunkname == b'sdsc':
                    self._read_sdsc_chunk(chunk)
                    self._sdsc_chunk_read = 1
                elif chunkname == b'adsc':
                    self._read_adsc_chunk(chunk)
                    self._adsc_chunk_read = 1
                elif chunkname == b'LIST':
                    self._read_list_chunk(chunk)
                    self._list_chunk_read = 1
                elif chunkname == b'data':
                    if not (self._sdsc_chunk_read):
                        raise Error('data chunk before sdsc chunk')
                    # EVA2 version
                    self._data_chunk = chunk
                    if self._adsc_chunk_read == 0:
                        # We make assumption about sampwidth here
                        sampwidth = 16
                        self._nchannels = 1
                        self._sampwidth = (sampwidth + 7) // 8
                        self._framesize = self._nchannels * self._sampwidth
                        self._nframes = chunk.chunksize // self._framesize
                        self._comptype = 'NONE'
                        self._compname = 'not compressed'
                        self._adsc_chunk_read = 1
                    else:
                        self._nframes = chunk.chunksize // self._framesize
                    self._data_seek_needed = 0
                    break
                chunk.skip()
        if self._filetype == b'WAVE':
            if not self._fmt_chunk_read or not self._data_chunk:
                raise Error('fmt chunk and/or data chunk missing')
        elif self._filetype == b'WSIG':
            if not self._sdsc_chunk_read:
                raise Error('sdsc chunk missing')
            elif not self._adsc_chunk_read:
                raise Error('adsc chunk missing')
            elif not self._data_chunk:
                raise Error('data chunk missing')

    def __init__(self, f):
        self._i_opened_the_file = None
        if isinstance(f, str):
            f = builtins.open(f, 'rb')
            self._i_opened_the_file = f
        # else, assume it is an open file object already
        try:
            self.initfp(f)
        except:
            if self._i_opened_the_file:
                f.close()
            raise

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ==============================================================
    # User visible methods
    # ==============================================================
    def getfp(self):
        return self._file

    def rewind(self):
        self._data_seek_needed = 1
        self.soundpos = 0

    def close(self):
        self._file = None
        file = self._i_opened_the_file
        if file:
            self._i_opened_the_file
            if file:
                self._i_opened_the_file = None
                file.close()

    def tell(self):
        return self._soundpos

    def getnchannels(self):
        return self._nchannels

    def getnframes(self):
        return self._nframes

    def getsampwith(self):
        return self._sampwidth

    def getframerate(self):
        return self._framerate

    def getcomptype(self):
        return self._comptype

    def getcompname(self):
        return self._compname

    def getparaname(self):
        return self._paraname

    def getunit(self):
        return self._unitname

    def getsignaldynamic(self):
        return self._signaldynamic

    def getvalueatmax(self):
        return self._valueatmax

    def getzero(self):
        return self._czero

    def getparams(self):
        return _wave_params(self.getnchannels(), self.getsampwith(),
                            self.getframerate(), self.getnframes(),
                            self.getcomptype(), self.getcompname(),
                            self.getduration(), self.getparaname(),
                            self.getunit(), self.getsignaldynamic(),
                            self.getvalueatmax(), self.getzero())

    def getmarkers(self):
        return None

    def getmark(selfself, id):
        raise Error('no marks')

    def getduration(self):
        self._duration = self._nframes / float(self._framerate)
        return self._duration

    def setpos(self, pos):
        if pos < 0 or pos > self.nframes:
            raise Error('position not in range')
        self._soundpos = pos
        self._data_seek_needed = 1

    def readframes(self, nframes):
        if self._data_seek_needed:
            self._data_chunk.seek(0, 0)
            pos = self._soundpos * self._framesize
            if pos:
                self._data_chunk.seek(pos, 0)
            self._data_seek_needed = 0
        if nframes == 0:
            return b''
        data = self._data_chunk.read(nframes * self._framesize)
        if self._sampwidth != 1 and sys.byteorder == 'big':
            data = audioop.byteswap(data, self._sampwidth)
        if self._convert and data:
            data = self._convert(data)
        self._soundpos = self._soundpos + len(data) // (self._nchannels * self._sampwidth)
        return data

    # ==============================================================
    # Internal methods
    # ==============================================================
    def _read_fmt_chunk(self, chunk):
        try:
            wFormatTag, self._nchannels, self._framerate, dwAvgBytesPerSec, wBlockAlign = struct.unpack_from('<HHLLH',
                                                                                                             chunk.read(
                                                                                                                 14))
        except struct.error:
            raise EOFError from None
        if wFormatTag == WAVE_FORMAT_PCM:
            try:
                sampwidth = struct.unpack_from('<H', chunk.read(2))[0]
            except struct.error:
                raise EOFError from None
            self._sampwidth = (sampwidth + 7) // 8
            if not self._sampwidth:
                raise Error('bad sample width')
        else:
            raise Error('unknown format: %r' % (wFormatTag,))
        if not self._nchannels:
            raise Error('bad # of channels')
        self._framesize = self._nchannels * self._sampwidth
        self._comptype = 'NONE'
        self._compname = 'not compressed'

    def _read_sdsc_chunk(self, chunk):
        """Variables used in this methods
        s_size -- size of the structure = 128 octets
        acronym -- acronym of parameter
        paramname -- name of parameter
        unitname -- unit name of parameter
        snsamples -- number of samples in 'data
        sampfreq -- sampling rate
        s_max -- max value of the signal
        s_min -- min value of the signal
        cmax -- calibration at max
        czero -- calibration at zero
        imax -- integer part of the value at maximum
        fmax -- floating part x 10^6 of the maximum
        """
        try:
            (s_size, acronym, paraname,
             unitname, snsamples, self._framerate,
             self._s_max, self._s_min, cmax, self._czero,
             imax, fmax) = unpack(
                '<L'  # s_size 4
                'L'  # acronym 4
                '80s'  # paraname 80
                '16s'  # unitname 16
                'L'  # snsamples 4
                'L'  # _framerate 4 (Freq)
                'h'  # s_max 2
                'h'  # s_min 2
                'h'  # cmax 2
                'h'  # _czero 2
                'i'  # imax 4
                'L',  # fmax 8
                chunk.read(128)
            )
        except struct.error:
            raise EOFError from None

        # handle redundant characters
        self._paraname = paraname.replace(b'\x00', b'').decode('ascii')
        self._unitname = unitname.replace(b'\x00', b'').decode('ascii')

        # Calibration setting
        self._signaldynamic = float(cmax - self._czero)
        self._valueatmax = float(imax) + fmax / float(100000)

    def _read_adsc_chunk(self, chunk):
        """Variables used in this methods
        a_size -- size of the structure = 32 octets
        nch -- number of channels
        ansamples -- number of samples
        acquifreq -- acquisition frequency
        bps -- bits per sample
        highest --- highest value
        lowest -- lowest value
        zero -- zero
        reccode -- recording program code
        recver -- version of the acquisition program
        """
        try:
            (a_size, self._nchannels, ansamples, acquifreq,
             sampwidth, highest, lowest, zero,
             reccode, recver) = unpack(
                '<L'  # a_size 4
                'H'  # _nchannels 2 (nch)
                'L'  # ansamples 4
                'L'  # acquifreq 4
                'H'  # sampwidth 2  (bps)
                'i'  # highest 4
                'i'  # lowest 4
                'i'  # zero 4
                'H'  # reccode 2
                'H',  # recver 2
                chunk.read(32)
            )
        except struct.error:
            raise EOFError from None
        self._sampwidth = (sampwidth + 7) // 8
        if not self._sampwidth:
            raise Error('bad sample width')
        if not self._nchannels:
            raise Error('bad # of channels')
        self._framesize = self._nchannels * self._sampwidth
        self._comptype = 'NONE'
        self._compname = 'not compressed'

    def _read_list_chunk(self, chunk):
        size = chunk.getsize()
        fmt = str(size) + 's'
        (MetaInfo,) = struct.unpack(fmt, chunk.read(size))
        MetaInfo = MetaInfo.replace(b'\x00', b' ').decode('ascii')
        MetaInfo = MetaInfo.split('   ')
        self._metaInfo = MetaInfo


def read(f, mode=None):
    if mode is None:
        if hasattr(f, 'mode'):
            mode = f.mode
        else:
            mode = 'rb'
    if mode in ('r', 'rb'):
        return WsigRead(f)
    else:
        raise Error("mode must be 'r', or, 'rb'")


def towave(filename, rate, data):
    """
    Write a numpy array as a WAV file
    Parameters
    ----------
    filename : string or open file handle
        Output wav file
    rate : int
        The sample rate (in samples/sec).
    data : ndarray
        A 1-D or 2-D numpy array of either integer or float data-type.
    Notes
    -----
    * The file can be an open file or a filename.
    * Writes a simple uncompressed WAV file.
    * The bits-per-sample will be determined by the data-type.
    * To write multiple-channels, use a 2-D array of shape
      (Nsamples, Nchannels).
    """
    if hasattr(filename, 'write'):
        fid = filename
    else:
        fid = open(filename, 'wb')

    try:
        dkind = data.dtype.kind
        if not (dkind == 'i' or dkind == 'f' or (dkind == 'u' and data.dtype.itemsize == 1)):
            raise ValueError("Unsupported data type '%s'" % data.dtype)

        fid.write(b'RIFF')
        fid.write(b'\x00\x00\x00\x00')
        fid.write(b'WAVE')
        # fmt chunk
        fid.write(b'fmt ')
        if dkind == 'f':
            comp = 3
        else:
            comp = 1
        if data.ndim == 1:
            noc = 1
        else:
            noc = data.shape[1]
        bits = data.dtype.itemsize * 8
        sbytes = rate * (bits // 8) * noc
        ba = noc * (bits // 8)
        fid.write(struct.pack('<ihHIIHH', 16, comp, noc, rate, sbytes, ba, bits))
        # data chunk
        fid.write(b'data')
        fid.write(struct.pack('<i', data.nbytes))
        if data.dtype.byteorder == '>' or (data.dtype.byteorder == '=' and sys.byteorder == 'big'):
            data = data.byteswap()
        fid.write(data.ravel().view('b').data)

        # Determine file size and place it in correct
        # position at start of the file.
        size = fid.tell()
        fid.seek(4)
        fid.write(struct.pack('<i', size - 8))

    finally:
        if not hasattr(filename, 'write'):
            fid.close()
        else:
            fid.seek(0)
