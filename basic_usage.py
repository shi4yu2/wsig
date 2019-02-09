import wsig
import numpy as np

# Read files
wave = wsig.read("example/example.pr1")

# Inspect parameters
print("Type of measure: " + str(wave.getparaname()))  # type of measure
print(wave.getparams())

# Read frames as numpy array
signal = np.frombuffer(wave.readframes(-1), np.int16)

# Calibration
# =============
# double val_calib = (double)(valint16 - czero) * (m_fValueAtMax / m_fSignalDynamic)
# =============
if wave._filetype == b'WSIG':
    calibratedSignal = (signal - wave.getzero()) * (wave.getvalueatmax() / wave.getsignaldynamic())
else:
    print("Not WSIG File, no calibration needed")


# Convert signal to .wav (WITHOUT calibration)
output = "output.wav"
wsig.towave(output, wave.getframerate(), signal)
