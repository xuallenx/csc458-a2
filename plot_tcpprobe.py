#!/usr/bin/env python3
"""
Plot TCP congestion window (cwnd) timeseries and optional histogram

This script parses tcp_probe ftrace output and generates visualizations
of TCP congestion window behavior over time.
"""

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple, DefaultDict, Optional

import matplotlib as m
import matplotlib.pyplot as plt
import numpy as np

from helper import col
import plot_defaults


@dataclass
class TCPEvent:
    """Class for storing TCP probe events with timestamp and cwnd information."""
    timestamp: float
    sport: int
    cwnd: float


def parse_tcp_probe_file(
    fname: str, 
    port: str, 
    use_sport: bool
) -> Tuple[DefaultDict[int, List[float]], DefaultDict[int, List[float]]]:
    """
    Parse a tcp_probe ftrace output file, filtering by port.
    
    Args:
        fname: Path to the tcp_probe trace file
        port: Port number to filter on
        use_sport: If True, filter on source port; otherwise filter on dest port
        
    Returns:
        Tuple of (times, cwnd_vals) as defaultdicts keyed by source port
    """
    times = defaultdict(list)
    cwnds = defaultdict(list)
    
    MSS = 1480  # Maximum Segment Size in bytes
    KB = 1024.0  # Conversion factor to kilobytes

    try:
        with open(fname, "r") as f:
            for line in f:
                if "tcp_probe:" not in line:
                    continue

                header, probe = line.strip().split("tcp_probe:", 1)
                parts = header.split()

                if len(parts) < 4:
                    continue
                    
                try:
                    timestamp = float(parts[-1].rstrip(":"))
                except ValueError:
                    continue

                # Parse key=value fields
                kv = {}
                for token in probe.strip().split():
                    if "=" in token:
                        k, v = token.split("=", 1)
                        kv[k] = v
                
                try:
                    src_parts = kv.get("src", "").split(":")
                    dst_parts = kv.get("dest", "").split(":")
                    
                    if len(src_parts) < 2 or len(dst_parts) < 2:
                        continue
                        
                    sport = int(src_parts[1])
                    dport = int(dst_parts[1])
                except (IndexError, ValueError):
                    continue

                # Apply port filter
                target_port = str(sport if use_sport else dport)
                if target_port != port:
                    continue

                # Store valid data points
                times[sport].append(timestamp)
                try:
                    # Convert cwnd to KB
                    cwnd_raw = int(kv.get("snd_cwnd", 0))
                    cwnd_kb = cwnd_raw * MSS / KB
                    cwnds[sport].append(cwnd_kb)
                except ValueError:
                    continue
    except FileNotFoundError:
        print(f"Error: File {fname} not found", file=sys.stderr)
    except PermissionError:
        print(f"Error: No permission to read {fname}", file=sys.stderr)
                
    return times, cwnds


def plot_cwnd_timeseries(
    ax: plt.Axes, 
    files: List[str], 
    port: str, 
    use_sport: bool
) -> List[TCPEvent]:
    """
    Plot per-port cwnd traces on the provided axes.
    
    Args:
        ax: Matplotlib axes to plot on
        files: List of tcp_probe trace files
        port: Port number to filter on
        use_sport: If True, filter on source port; otherwise filter on dest port
        
    Returns:
        List of TCPEvent objects sorted by timestamp
    """
    all_events = []
    all_timestamps = []
    collected_data = []
    
    # First pass: collect all timestamps and data
    for fname in files:
        time_dict, cwnd_dict = parse_tcp_probe_file(fname, port, use_sport)
        
        for sport in sorted(cwnd_dict):
            timestamps = time_dict[sport]
            cwnd_values = cwnd_dict[sport]
            
            # Skip empty data sets
            if not timestamps:
                continue
                
            all_timestamps.extend(timestamps)
            collected_data.append((sport, timestamps, cwnd_values))
    
    # Find global start time
    if not all_timestamps:
        return []  # No data found
        
    global_start_time = min(all_timestamps)
    
    # Second pass: normalize against global start time and plot
    for sport, timestamps, cwnd_values in collected_data:
        # Normalize timestamps globally
        rel_timestamps = [t - global_start_time for t in timestamps]
        
        # Create events for later total cwnd calculation
        events = [TCPEvent(t, sport, cw) for t, cw in zip(rel_timestamps, cwnd_values)]
        all_events.extend(events)
        
        # Plot individual port's cwnd
        ax.plot(rel_timestamps, cwnd_values, label=f"port {sport}")
    
    # Sort events chronologically
    all_events.sort(key=lambda e: e.timestamp)
    return all_events


def calculate_total_cwnd(events: List[TCPEvent]) -> Tuple[List[float], List[float]]:
    """
    Calculate the total cwnd across all ports at each timestamp.
    
    Args:
        events: List of TCPEvent objects sorted by timestamp
        
    Returns:
        Tuple of (timestamps, total_cwnd_values)
    """
    if not events:
        return [], []
        
    total_cwnd = 0.0
    latest_cwnd_by_port = {}
    timestamps = []
    total_values = []
    
    for event in events:
        # Subtract old cwnd value for this port (if any)
        if event.sport in latest_cwnd_by_port:
            total_cwnd -= latest_cwnd_by_port[event.sport]
            
        # Add new cwnd value
        total_cwnd += event.cwnd
        latest_cwnd_by_port[event.sport] = event.cwnd
        
        # Record the timestamp and new total
        timestamps.append(event.timestamp)
        total_values.append(total_cwnd)
        
    return timestamps, total_values


def plot_cwnd_histogram(ax: plt.Axes, total_cwnd_values: List[float]) -> None:
    """Plot histogram of total cwnd values."""
    if not total_cwnd_values:
        ax.text(0.5, 0.5, "No data to display", 
                ha='center', va='center', transform=ax.transAxes)
        return
        
    ax.hist(total_cwnd_values, bins=50, density=True, alpha=0.75)
    ax.set_xlabel("cwnd sum (KB)")
    ax.set_ylabel("Density")
    ax.set_title("Histogram of total cwnd")
    
    # Add mean and median lines
    mean_val = np.mean(total_cwnd_values)
    median_val = np.median(total_cwnd_values)
    
    # Plot vertical lines for mean and median
    ax.axvline(mean_val, color='r', linestyle='-', linewidth=1, 
               label=f'Mean: {mean_val:.2f}')
    ax.axvline(median_val, color='g', linestyle='--', linewidth=1, 
               label=f'Median: {median_val:.2f}')
    
    ax.legend()


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Plot TCP congestion window (cwnd) timeseries and histogram",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-f", "--files",
        dest="files",
        nargs="+",
        required=True,
        help="TCP probe ftrace output files"
    )
    parser.add_argument(
        "-p", "--port",
        dest="port",
        default="5001",
        help="Port to filter on"
    )
    parser.add_argument(
        "--sport", "-s",
        action="store_true",
        dest="sport",
        help="Filter on source port (default: filter on destination port)"
    )
    parser.add_argument(
        "-H", "--histogram",
        action="store_true",
        dest="histogram",
        help="Also plot histogram of total cwnd"
    )
    parser.add_argument(
        "-o", "--out",
        dest="out",
        default=None,
        help="Output PNG file (if omitted, displays interactively)"
    )
    args = parser.parse_args()

    # Set up the figure and axes
    m.rc("figure", figsize=(16, 6))
    fig = plt.figure()
    cols = 2 if args.histogram else 1
    ax_timeseries = fig.add_subplot(1, cols, 1)
    
    # Plot cwnd timeseries with global time normalization
    events = plot_cwnd_timeseries(ax_timeseries, args.files, args.port, args.sport)
    
    if not events:
        print("No matching TCP events found in the provided files.", file=sys.stderr)
        ax_timeseries.text(0.5, 0.5, "No data to display", 
                          ha='center', va='center', transform=ax_timeseries.transAxes)
    else:
        # Calculate and plot total cwnd
        timestamps, total_cwnd_values = calculate_total_cwnd(events)
        ax_timeseries.plot(timestamps, total_cwnd_values, 
                          lw=2, label="sum cwnd")
        
        # Configure time series plot
        ax_timeseries.set_xlabel("seconds")
        ax_timeseries.set_ylabel("cwnd (KB)")
        ax_timeseries.set_title("TCP congestion window timeseries")
        ax_timeseries.grid(True)
        ax_timeseries.legend()
        
        # Plot histogram if requested
        if args.histogram:
            ax_histogram = fig.add_subplot(1, 2, 2)
            plot_cwnd_histogram(ax_histogram, total_cwnd_values)
    
    # Adjust layout and save/show
    if args.out:
        print(f"saving to {args.out}")
        plt.savefig(args.out)
    else:
        plt.show()


if __name__ == "__main__":
    main()
    