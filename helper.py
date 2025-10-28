"""
Helper module for the plot scripts.
"""

import itertools
import os
import math

import matplotlib as m

# select matplotlib backend early
if os.uname()[0] == "Darwin":
    m.use("MacOSX")
else:
    m.use("Agg")
import matplotlib.pyplot as plt


def read_list(fname, delim=","):
    """
    Read a delimited file into a list of rows, cleaning empty entries.
    """
    ret = []
    with open(fname, "r") as f:
        for line in f:
            tokens = line.strip().split(delim)
            cleaned = ["0" if tok.strip() in ("", "ms", "s") else tok for tok in tokens]
            ret.append(cleaned)
    return ret


def ewma(alpha, values):
    """
    Exponentially Weighted Moving Average.
    """
    if alpha == 0:
        return list(values)
    ret = []
    prev = 0.0
    for v in values:
        prev = alpha * prev + (1 - alpha) * v
        ret.append(prev)
    return ret


def col(n, obj=None, clean=lambda e: e):
    """
    A versatile column extractor.

    col(n)(item)         -> clean(item[n])
    col(n, row_list)     -> [clean(row[n]) for row in row_list]
    col(key, dict_obj)   -> clean(dict_obj.get(key))
    """
    if obj is None:

        def f(item):
            return clean(item[n])

        return f

    if isinstance(obj, dict):
        return clean(obj.get(n))

    if isinstance(obj, list):
        # list of rows
        if obj and isinstance(obj[0], (list, dict)):
            return [col(n, clean=clean)(item) for item in obj]
        # single flat list
        try:
            return clean(obj[n])
        except (IndexError, KeyError):
            return None

    return None


def transpose(matrix):
    """
    Transpose a list of sequences.
    """
    return list(zip(*matrix))


def avg(lst):
    """
    Average of a list of numbers or numeric strings.
    """
    nums = [float(x) for x in lst]
    return sum(nums) / len(nums) if nums else 0.0


def stdev(lst):
    """
    Standard deviation of a list of numbers.
    """
    nums = [float(x) for x in lst]
    if not nums:
        return 0.0
    mean = avg(nums)
    var = sum((x - mean) ** 2 for x in nums) / len(nums)
    return math.sqrt(var)


def xaxis(values, limit):
    """
    Generate x-axis points scaled to a given limit.
    """
    length = len(values)
    return [(i * limit / length, y) for i, y in enumerate(values)]


def grouper(n, iterable, fillvalue=None):
    """
    Collect data into fixed-length chunks or blocks.
    """
    return itertools.zip_longest(*[iter(iterable)] * n, fillvalue=fillvalue)


def cdf(values):
    """
    Compute the empirical CDF of a list of numbers.
    """
    sorted_vals = sorted(values)
    l = len(sorted_vals)
    x, y = [], []
    for idx, v in enumerate(sorted_vals, start=1):
        x.append(v)
        y.append(idx / l)
    return x, y


def parse_cpu_usage(fname, nprocessors=8):
    """
    Returns aggregated CPU usage tuples (user, system, nice, iowait, hirq, sirq, steal)
    aggregated over all processors. DOES NOT RETURN IDLE times.
    """
    with open(fname, "r") as f:
        lines = f.readlines()

    data_groups = grouper(nprocessors, lines)
    ret = []

    for group in data_groups:
        totals = [0.0] * 8
        for line in group:
            if line is None:
                continue
            parts = line.split(":", 1)
            if len(parts) < 2:
                continue
            usages = parts[1].split(",")
            for i, usage in enumerate(usages):
                num_str = usage.strip().split("%")[0]
                try:
                    totals[i] += float(num_str)
                except ValueError:
                    pass
        # average over processors
        averages = [t / nprocessors for t in totals]
        # Skip idle time (index 3)
        ret.append(averages[0:3] + averages[4:])
    return ret


def pc95(lst):
    """
    95th percentile.
    """
    if not lst:
        return None
    sorted_lst = sorted(lst)
    idx = int(0.95 * len(sorted_lst))
    return sorted_lst[idx]


def pc99(lst):
    """
    99th percentile.
    """
    if not lst:
        return None
    sorted_lst = sorted(lst)
    idx = int(0.99 * len(sorted_lst))
    return sorted_lst[idx]


def coeff_variation(lst):
    """
    Coefficient of variation: stdev / mean.
    """
    if not lst:
        return 0.0
    return stdev(lst) / avg(lst)
