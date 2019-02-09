import wsig
import numpy as np
import plotly
from plotly.graph_objs import Scatter, Layout

"""
All files are assumed to have the same duration (simultaneous recording)
"""

f_int = "example/example.int"
f_oaf = "example/example.oaf"
f_naf = "example/example.naf"
f_pr1 = "example/example.pr1"
f_pr2 = "example/example.pr2"
file_list = [f_int, f_oaf, f_naf, f_pr1, f_pr2]

nfiles = len(file_list)

# Read files
buffer_list = []
data = []
typeMeasure = []

for i in range(nfiles):
    buffer_list.append(wsig.read(file_list[i]))
    typeMeasure.append(buffer_list[i].getparaname())
    data.append(np.frombuffer(buffer_list[i].readframes(-1), np.int16))
    # Calibration
    if buffer_list[i]._filetype == b'WSIG':
        data[i] = (data[i] - buffer_list[i].getzero()) * (buffer_list[i].getvalueatmax() / buffer_list[i].getsignaldynamic())
    else:
        data[i] = data[i]  # if .wav file

# Get signal duration
length = len(data[0])
framerate = buffer_list[0].getframerate()
time = np.linspace(0, length / framerate, num=length)

# Multiplot =============================================
fig = plotly.tools.make_subplots(rows=5, cols=1,
                                 subplot_titles=(typeMeasure[:]))

trace = []
for i in range(nfiles):
    trace.append(Scatter(x=time, y=data[i], name=typeMeasure[i]))
    fig.append_trace(trace[i], i+1, 1)

fig['layout'].update(title="Example Multiplot")

plotly.offline.plot(fig, filename="multiplot.html")



