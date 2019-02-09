import wsig
import argparse
import sys
import os
import re
import numpy as np


def conversion(input, output):
    nfiles = len(input)
    for i in range(nfiles):
        print("Start conversion for " + input[i] + "...")
        wave = wsig.read(input[i])
        # Read frames as numpy array
        signal = np.frombuffer(wave.readframes(-1), np.int16)
        wsig.towave(output[i], wave.getframerate(), signal)
        print("Done. (" + output[i] + ")")


if __name__ == '__main__':
    # Parse command line arguments.
    parser = argparse.ArgumentParser(description='Conversion from WSIG to WAVE', add_help=True,
        usage='%(prog)s [options]')
    parser.add_argument(
        '-i, --input', nargs=None, metavar='STR', dest='input',
        help='intput directory containing files to be converted')
    parser.add_argument(
        '-o, --output', nargs=None, metavar='STR', dest='output',
        help="output directory for files after conversion")

    if len(sys.argv) == 1:
            parser.print_help()
            sys.exit(1)
    args = parser.parse_args()

    # Output
    if not os.path.exists(args.output):
        os.makedirs(args.output)

    # Input files
    input_dir = vars(args)['input']
    inputfiles = os.listdir(input_dir)
    files_list = []
    output_list = []
    regex = re.compile(r'.+\.(int|naf|oaf|pr1|pr2)$')
    for path, subdirs, files in os.walk(input_dir):
        for name in files:
            if re.match(regex, name):
                files_list.append(os.path.join(path, name))
                output_list.append(os.path.join(args.output, name+".wav"))
            else:
                pass

    if files_list is not None:
        conversion(files_list, output_list)
