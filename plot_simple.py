import wsig
import numpy as np
import plotly
from plotly.graph_objs import Scatter, Layout

file = "example/example.pr1"
# Read files
wave = wsig.read(file)
# Read frames as numpy array
signal = np.frombuffer(wave.readframes(-1), np.int16)

# Calibration
if wave._filetype == b'WSIG':
    calibratedSignal = (signal - wave.getzero()) * (wave.getvalueatmax() / wave.getsignaldynamic())
else:
    calibratedSignal = signal  # if .wav file

# Get signal duration
length = len(signal)
framerate = wave.getframerate()
time = np.linspace(0, length / framerate, num=length)

# Simple Plot =============================================
plotly.offline.plot({
    "data": [
        Scatter(x=time, y=calibratedSignal, name=wave.getparaname())
    ],
    "layout": Layout(
        title=wave.getparaname()
    )
},
filename=file+"_plot.html")


