"""
Plot queue occupancy over time
"""

import argparse
import sys

import matplotlib as m
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from pylab import figure

from helper import read_list, col
import plot_defaults


def get_style(i):
    if i == 0:
        return {"color": "red"}
    else:
        return {"color": "black", "ls": "-."}


def main():
    parser = argparse.ArgumentParser(description="Plot queue occupancy over time")
    parser.add_argument(
        "--files",
        "-f",
        help="Queue timeseries output to one plot",
        required=True,
        nargs="+",
        dest="files",
    )
    parser.add_argument(
        "--legend",
        "-l",
        help="Legend to use if there are multiple plots. File names used as default.",
        nargs="+",
        default=None,
        dest="legend",
    )
    parser.add_argument(
        "--out",
        "-o",
        help="Output png file for the plot (if omitted, shows interactively).",
        default=None,
        dest="out",
    )
    parser.add_argument(
        "--labels",
        help="Labels for x-axis if summarising; defaults to file names",
        nargs="+",
        default=[],
        dest="labels",
    )
    parser.add_argument(
        "--every",
        help="Downsample factor: plot one of every EVERY (x,y) point (default 1).",
        type=int,
        default=1,
        dest="every",
    )

    args = parser.parse_args()

    # Default legend to file names
    if args.legend is None:
        args.legend = list(args.files)

    # Set up figure
    m.rc("figure", figsize=(16, 6))
    fig = figure()
    ax = fig.add_subplot(111)

    for i, f in enumerate(args.files):
        data = read_list(f)

        if not data:
            print(f"{sys.argv[0]}: error: no queue length data", file=sys.stderr)
            sys.exit(1)

        x_raw = [float(x) for x in col(0, data)]
        start_time = x_raw[0]
        xaxis = [x - start_time for x in x_raw]

        qlens = [float(y) for y in col(1, data)]

        # Downsample
        xaxis = xaxis[:: args.every]
        qlens = qlens[:: args.every]

        ax.plot(xaxis, qlens, label=args.legend[i], **get_style(i))
        ax.xaxis.set_major_locator(MaxNLocator(4))

    ax.set_ylabel("Packets")
    ax.set_xlabel("Seconds")
    ax.grid(True)

    if args.out:
        print(f"saving to {args.out}")
        plt.savefig(args.out)
    else:
        plt.show()


if __name__ == "__main__":
    main()
