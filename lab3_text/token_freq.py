import argparse
import csv
import math
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

import orjson
import matplotlib.pyplot as plt
from tqdm import tqdm


DEFAULT_TOKENS = "tokens.txt"
DEFAULT_CSV = "freq.csv"
DEFAULT_PLOT = "zipf_plot.png"
DEFAULT_REPORT = "token_stats.json"


def read_tokens(path: str) -> List[str]:
    tokens: List[str] = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in tqdm(f, desc=f"read {Path(path).name}"):
            token = line.strip()
            if token:
                tokens.append(token)
    return tokens


def fit_zipf(ranks: List[int], freqs: List[int], fit_top: int) -> Tuple[float, float]:
    n = min(len(ranks), fit_top)
    if n < 2:
        return 1.0, 1.0
    x = [math.log10(float(r)) for r in ranks[:n]]
    y = [math.log10(float(f)) for f in freqs[:n]]
    sx = sum(x)
    sy = sum(y)
    sxx = sum(v * v for v in x)
    sxy = sum(a * b for a, b in zip(x, y))
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-12:
        return 1.0, 1.0
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    s = -slope
    K = 10 ** intercept
    return s, K


def export_csv(data: List[Tuple[int, str, int, float]], path: str):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "term", "freq", "zipf_pred"])
        for rank, term, freq, pred in data:
            writer.writerow([rank, term, freq, f"{pred:.6f}"])


def plot_distribution(ranks: List[int], freqs: List[int], preds: List[float], path: str, top: int, dpi: int = 150):
    top = min(top, len(ranks))
    log_rank = [math.log10(float(r)) for r in ranks[:top]]
    log_freq = [math.log10(float(f)) for f in freqs[:top]]
    plt.figure(figsize=(8, 6))
    plt.scatter(log_rank, log_freq, s=6, alpha=0.6, label="Corpus")
    if preds:
        log_pred = [math.log10(max(p, 1e-9)) for p in preds[:top]]
        plt.plot(log_rank, log_pred, linewidth=2, label="Zipf fit")
    plt.xlabel("log10(rank)")
    plt.ylabel("log10(freq)")
    plt.title("Term frequency distribution (log-log)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=dpi)


def main():
    ap = argparse.ArgumentParser(description="Frequency stats and Zipf plot from tokens.")
    ap.add_argument("--tokens", default=DEFAULT_TOKENS, help="Input tokens file (one per line).")
    ap.add_argument("--csv", default=DEFAULT_CSV, help="Where to write frequency table.")
    ap.add_argument("--plot", default=DEFAULT_PLOT, help="Where to save log-log plot.")
    ap.add_argument("--report", default=DEFAULT_REPORT, help="Write JSON report with stats.")
    ap.add_argument("--top", type=int, default=100000, help="Top terms to keep in CSV/plot.")
    ap.add_argument("--fit-top", type=int, default=50000, help="Ranks to use for Zipf fit.")
    args = ap.parse_args()

    tokens = read_tokens(args.tokens)
    total_tokens = len(tokens)
    avg_len = sum(len(t) for t in tokens) / total_tokens if total_tokens else 0.0

    counter = Counter(tokens)
    most_common = counter.most_common(args.top)
    ranks = []
    freqs = []
    terms = []
    for idx, (term, freq) in enumerate(most_common, start=1):
        ranks.append(idx)
        freqs.append(freq)
        terms.append(term)

    s, K = fit_zipf(ranks, freqs, args.fit_top)
    preds = [K / (r ** s) for r in ranks]

    export_data = [(r, t, f, p) for r, t, f, p in zip(ranks, terms, freqs, preds)]
    export_csv(export_data, args.csv)
    plot_distribution(ranks, freqs, preds, args.plot, args.top)

    report = {
        "tokens_file": args.tokens,
        "total_tokens": total_tokens,
        "unique_tokens": len(counter),
        "average_length": avg_len,
        "zipf_s": s,
        "zipf_K": K,
        "csv": args.csv,
        "plot": args.plot,
    }
    with open(args.report, "wb") as out:
        out.write(orjson.dumps(report, option=orjson.OPT_INDENT_2))

    print(f"Tokens: {total_tokens}, unique: {len(counter)}, avg len: {avg_len:.2f}")
    print(f"Zipf fit: s={s:.4f}, K={K:.4f}")
    print(f"CSV -> {args.csv}, plot -> {args.plot}, report -> {args.report}")


if __name__ == "__main__":
    main()
