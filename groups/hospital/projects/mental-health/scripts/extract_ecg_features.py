"""Rebuild data/upstream/ecg_features.csv from the raw Kaggle ECG archive.

The raw dataset (buraktaci/psychiatry-ecg) is 2,670 MATLAB files — one
12-lead ECG segment each, foldered by disorder cohort. Raw signals stay out
of the warehouse; this script reduces each recording to summary features at
recording grain. Run it only when re-fetching upstream:

    uvx kaggle datasets download -d buraktaci/psychiatry-ecg -p <dir> --unzip
    uv run --with scipy,numpy python scripts/extract_ecg_features.py <dir>

Each .mat holds `sinyal` (n_samples x 12 float64) and `label`
(Bipolar=1, Depression=2, Schizophrenia=3).
"""

from __future__ import annotations

import csv
import glob
import hashlib
import os
import sys
from pathlib import Path

import numpy as np
from scipy.io import loadmat

OUT = Path(__file__).resolve().parents[1] / "data" / "upstream" / "ecg_features.csv"


def main(raw_dir: str) -> int:
    rows = []
    for path in sorted(glob.glob(os.path.join(raw_dir, "Psychiatry ECG", "*", "*.mat"))):
        group = Path(path).parent.name
        fname = os.path.basename(path)
        m = loadmat(path)
        sig = m["sinyal"]
        rows.append(
            {
                "recording_id": hashlib.sha1(f"{group}/{fname}".encode()).hexdigest()[:12],
                "source_file": f"{group}/{fname}",
                "disorder_group": group,
                "upstream_label": int(m["label"][0][0]),
                "n_samples": sig.shape[0],
                "n_leads": sig.shape[1],
                "signal_mean": round(float(np.mean(sig)), 6),
                "signal_std": round(float(np.std(sig)), 6),
                "signal_min": round(float(np.min(sig)), 6),
                "signal_max": round(float(np.max(sig)), 6),
                "signal_rms": round(float(np.sqrt(np.mean(sig**2))), 6),
                "lead2_mean": round(float(np.mean(sig[:, 1])), 6),
                "lead2_std": round(float(np.std(sig[:, 1])), 6),
            }
        )
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} recordings → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
