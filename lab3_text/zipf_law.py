import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt


def load_termfreq(path: Path):
    items = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            try:
                term, cnt = line.split("\t", 1)
                cnt = int(cnt)
            except Exception:
                continue
            items.append((term, cnt))
    items.sort(key=lambda x: x[1], reverse=True)
    return items


def write_csv(items, out_csv: Path):
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    k = items[0][1]
    with out_csv.open("w", encoding="utf-8", newline="") as w:
        wr = csv.writer(w)
        wr.writerow(["rank", "term", "freq", "zipf_k_over_r", "log10_rank", "log10_freq", "log10_zipf"])
        for i, (t, f0) in enumerate(items, start=1):
            z = k / i
            wr.writerow([i, t, f0, z, math.log10(i), math.log10(f0), math.log10(z)])


def plot_zipf(items, out_png: Path):
    ranks = list(range(1, len(items) + 1))
    freqs = [c for _, c in items]
    k = freqs[0] if freqs else 1
    zipf = [k / r for r in ranks]

    plt.figure(figsize=(8, 5))
    plt.xscale("log")
    plt.yscale("log")
    plt.plot(ranks, freqs, label="Corpus")
    plt.plot(ranks, zipf, label="Zipf k/r")
    plt.xlabel("Rank (log)")
    plt.ylabel("Frequency (log)")
    plt.legend()
    plt.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=200)


def run(termfreq_path: str, out_csv_path: str, out_png_path: str):
    termfreq = Path(termfreq_path)
    out_csv = Path(out_csv_path)
    out_png = Path(out_png_path)

    items = load_termfreq(termfreq)
    if not items:
        raise RuntimeError("termfreq is empty or unreadable")

    write_csv(items, out_csv)
    plot_zipf(items, out_png)

    print(f"Zipf CSV -> {out_csv}")
    print(f"Zipf plot -> {out_png}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 4:
        print("Usage: python zipf_law.py <termfreq.tsv> <out.csv> <out.png>")
        raise SystemExit(1)

    run(sys.argv[1], sys.argv[2], sys.argv[3])
