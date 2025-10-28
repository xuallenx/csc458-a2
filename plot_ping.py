"""
Plot ping RTTs over time
"""

import argparse
import sys

import matplotlib as m
from matplotlib.ticker import MaxNLocator
from pylab import figure

from helper import col
import plot_defaults


def parse_ping(fname):
    """
    Parse ping output file for RTTs.
    Returns list of [sequence_number, rtt_ms].
    """
    results = []
    seq = 0
    with open(fname, "r") as f:
        for line in f:
            if "bytes from" not in line:
                continue
            parts = line.strip().split()
            # Expect format: ... time=XYZ ms
            for token in parts:
                if token.startswith("time="):
                    try:
                        rtt = float(token.split("=")[1])
                        results.append([seq, rtt])
                        seq += 1
                    except ValueError:
                        pass
                    break
    return results


def main():
    parser = argparse.ArgumentParser(description="Plot ping RTTs over time")
    parser.add_argument(
        "--files",
        "-f",
        help="Ping output files to plot",
        required=True,
        nargs="+",
        dest="files",
    )
    parser.add_argument(
        "--freq",
        help="Frequency of pings (per second)",
        type=int,
        default=10,
        dest="freq",
    )
    parser.add_argument(
        "--out",
        "-o",
        help="Output png file for the plot (if omitted, displays interactively).",
        default=None,
        dest="out",
    )
    args = parser.parse_args()

    # Configure figure size and backend
    m.rc("figure", figsize=(16, 6))
    fig = figure()
    ax = fig.add_subplot(111)

    for fname in args.files:
        data = parse_ping(fname)
        if not data:
            print(f"{sys.argv[0]}: error: no ping data in {fname}", file=sys.stderr)
            sys.exit(1)

        xseq = [float(x) for x in col(0, data)]
        # Normalize by frequency to get seconds
        start = xseq[0]
        times = [(x - start) / args.freq for x in xseq]

        rtts = [float(y) for y in col(1, data)]

        ax.plot(times, rtts, lw=2, label=fname)
        ax.xaxis.set_major_locator(MaxNLocator(4))

    ax.set_ylabel("RTT (ms)")
    ax.set_xlabel("Seconds")
    ax.grid(True)
    ax.legend()

    if args.out:
        print(f"saving to {args.out}")
        fig.savefig(args.out)
    else:
        fig.show()


if __name__ == "__main__":
    main()
