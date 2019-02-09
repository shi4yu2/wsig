# WSIG Handler and use 
## Overview
This repo provides wsig module for a convenient interface to the riff format of physiology measures. 

The following scripts demonstrate basic usage of this module.
* `basic_usage.py`:
  * read wsig file
  * display parameters
  * calibration
  * conversion to .wav
* `conversion.py`
  * Usage: `python conversion.py -i input_dir -o output_dir`
  * Conversion for multiple files contained in a directory
  * **Plase note that converted .wav is not calibrated** 
* `plot_simple.py`
  * plot one signal in an interactive html page
  * ![alt text](https://raw.githubusercontent.com/shi4yu2/wsig/master/img/simpleplot.png)
* `plot_multi.py`
  * plot simultaneous recording in an interactive html page 
  * ![alt text](https://raw.githubusercontent.com/shi4yu2/wsig/master/img/multiplot.png)
  
File samples are provided in "example" folder.  

## Dependencies
The following Python packages are required to run this software:
- Python 3.0 (https://www.python.org/)
- NumPy (https://github.com/numpy/numpy)
- Plotly (https://plot.ly/)


# wsig - Read and Write RIFF files
This module provides a way similar to native wave module to handle RIFF files
The wsig module defines the following function and exception:
```python
wsig.read(file, mode=None)
```
> If file is a string, open the file by that name, otherwise treat it as a file-like object. mode can be:
> * `'rb'`: Read only mode.
> 
> A *mode* of 'rb' returns a Wsig_read object, while a *mode* of 'wb' returns a Wisg_write object. If mode is omitted and a file-like object is passed as file, file.mode is used as the default value for mode.
>
> If you pass in a file-like object, the wsig object will not close it when its close() method is called; it is the caller’s responsibility to close the file object.
> 
> The `open()` function may be used in a with statement. When the with block completes, the `Wsig_read.close()` or `Wsig_write.close()` method is called.

```python
exception wsig.Error
```
> An error raised when something is impossible because it violates the RIFF specification or hits an implementation deficiency.

### List of parameters for calibration
* `Wsig_read.getzero()` (calibration_at_zero)
* `Wsig_read.getsignaldynamic()` (= calibration_at_max - calibration_at_zero)
* `Wsig_read.valueatmax()` (integer_part_of_the_value_at_max + floating_part_x_10^6_of_the_max / 1000000.0)

**Calibration algorithm**
```
double val_calib = (double)(valint16 - czero) * (m_fValueAtMax / m_fSignalDynamic)
```

**Calibration in python**
```python
signal = np.frombuffer(wsig.read(file).readframes(-1), np.int16)
calibratedSignal = (signal - wave.getzero()) * (wave.getvalueatmax() / wave.getsignaldynamic())
```

## Wisg_read Objects
Wsig_read objects, as returned by `read()`, have the following methods:

* `Wsig_read.close()`
Close the stream if it was opened by `wsig`, and make the instance unusable. This is called automatically on object collection.

* `Wsig_read.getnchannels()`
Returns number of audio channels (`1` for mono, `2` for stereo).

* `Wsig_read.getsampwidth()`
Returns sample width in bytes.

* `Wsig_read.getframerate()`
Returns sampling frequency.

* `Wsig_read.getnframes()`
Returns number of audio frames.

* `Wsig_read.getcomptype()`
Returns compression type (`'NONE'` is the only supported type).

* `Wsig_read.getcompname()`
Human-readable version of `getcomptype()`. Usually `'not compressed'` parallels `'NONE'`.

* `Wsig_read.getparams()`
Returns a `namedtuple()` `(nchannels, sampwidth, framerate, nframes, comptype, compname, duration, paraname, unit, signaldynamic, valueatmax, zero )`, equivalent to output of the `get*()` methods.

* `Wsig_read.getparaname()` 
Returns measure type (intensity, oral air flow, etc.).

* `Wsig_read.getunit()` 
Returns the unit of measure (e.g. hPa)

* `Wsig_read.getsignaldynamic()`
Returns signal dynamic (for calibration)

* `Wsig_read.getvalueatmax()`
Returns value at max (for calibration)

* `Wsig_read.getzero()`
Returns zero of calibration (for calibration)

* `Wsig_read.getduration()`
Returns the durataion of signal (duration = nframe / framerate)

* `Wsig_read.readframes(n)`
Reads and returns at most *n* frames of audio, as a *bytes* object.

* `Wsig_read.rewind()`
Rewind the file pointer to the beginning of the audio stream.

The following two methods are defined for compatibility with the aifc module, and don’t do anything interesting.

* `Wsig_read.getmarkers()`
Returns `None`.

* `Wsig_read.getmark(id)`
Raise an error.

The following two methods define a term “position” which is compatible between them, and is otherwise implementation dependent.

* `Wsig_read.setpos(pos)`
Set the file pointer to the specified position.

* `Wsig_read.tell()`
Return current file pointer position.

## Conversion to .wav
```python
import wsig
wsig.towave(filename, rate, date)
```
Write a numpy array as a WAV file

Example of use is provided in `basic_usage.py` (Please note that converted .wav is not calibrated)
