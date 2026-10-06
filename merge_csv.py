# -*- coding: utf-8 -*-
"""Merge per-category CSV files (made by catalog_scraper.py --outdir) into one file.

Usage: python merge_csv.py <folder> -o result_all.csv
"""
import csv, glob, os, argparse


def main():
    ap = argparse.ArgumentParser(description="Merge per-category CSV files")
    ap.add_argument("folder")
    ap.add_argument("-o", "--output", default="result_all.csv")
    args = ap.parse_args()

    files = sorted(f for f in glob.glob(os.path.join(args.folder, "*.csv"))
                   if os.path.abspath(f) != os.path.abspath(args.output))
    if not files:
        print("No CSV files found in", args.folder)
        return

    fieldnames, rows_all = None, []
    for path in files:
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            fieldnames = fieldnames or reader.fieldnames
            rows = list(reader)
            rows_all.extend(rows)
            print(f"{os.path.basename(path)}: {len(rows)} products")

    with open(args.output, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        w.writeheader()
        w.writerows(rows_all)
    print(f"\nDone: {len(files)} files, {len(rows_all)} products -> {args.output}")


if __name__ == "__main__":
    main()
