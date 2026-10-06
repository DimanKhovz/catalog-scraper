# -*- coding: utf-8 -*-
"""
Catalog scraper: category pages -> product cards -> CSV (one file per category).

Sample from a real project: an industrial pump catalog (Russian-language site).
The scraper opens every product card (not just the listing page) to collect the
unique description and the labelled technical specs.

Usage
-----
Several categories, one CSV per category (resumable):
    python catalog_scraper.py URL1 URL2 URL3 --outdir results

Re-run the same command after an interruption: categories that already have a
CSV are skipped, so the run continues where it stopped.

One or two categories into a single file:
    python catalog_scraper.py URL1 -o result.csv

Merge per-category files into one CSV:
    python merge_csv.py results -o result_all.csv

Requires: Python 3.8+, requests, beautifulsoup4
    pip install requests beautifulsoup4
"""

import os
import re
import sys
import csv
import time
import argparse

from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}
DELAY_BETWEEN_PRODUCTS = 0.3  # seconds; polite crawling, avoids hammering the site

# Output columns. The CSV is semicolon-delimited, UTF-8 with BOM, so it opens
# correctly in Excel (also with Russian/European regional settings).
FIELDNAMES = [
    "Name", "Model", "Code", "Category (source)", "Description",
    "Image URL", "Source URL",
    "Flow", "Head", "Power", "RPM", "Weight", "Dimensions",
]

# Spec labels on the source site (Russian) -> output column.
# The site misspells one label ("Оброты" instead of "Обороты"), so both are mapped.
LABEL_TO_FIELD = {
    "подача": "Flow",
    "напор": "Head",
    "мощность": "Power",
    "обороты": "RPM",
    "оброты": "RPM",
    "масса": "Weight",
    "габариты": "Dimensions",
}


def get_soup(url, session):
    resp = session.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return BeautifulSoup(resp.text, "html.parser")


def get_product_links(category_url, session):
    """Collect product-card links from a category listing page."""
    soup = get_soup(category_url, session)
    main = soup.select_one("main")
    if main is None:
        raise RuntimeError(f"<main> not found on {category_url} - the site layout may have changed")

    links, seen = [], set()
    for h2 in main.select("h2"):
        a = h2.find("a", href=True)
        if a is None:
            continue
        href = a["href"]
        if not re.search(r"/[a-z]{2}[\w-]*\.html$", href) or href in seen:
            continue
        seen.add(href)
        links.append(urljoin(category_url, href))  # works for /relative and absolute links
    return links


def parse_product(url, session):
    """Open one product card and extract title, labelled specs and description."""
    soup = get_soup(url, session)
    main = soup.select_one("main")
    if main is None:
        raise RuntimeError(f"<main> not found on {url}")

    h1 = main.select_one("h1")
    title = h1.get_text(strip=True) if h1 else ""
    title = re.sub(r"\s*\*\s*$", "", title).strip()
    title = re.sub(r"^Насос\s+", "", title)  # drop the generic word "Pump" prefix

    row = {name: "" for name in FIELDNAMES}
    row["Source URL"] = url
    row["Code"] = re.sub(r"^.*/|\.html$", "", url)
    row["Name"] = title
    row["Model"] = title

    spec_div = main.select_one('div[class="space-y-2 text-xl pl-4"]') or main.select_one("div.pl-4")
    if spec_div is not None:
        for p in spec_div.find_all("p", recursive=False):
            text = p.get_text(" ", strip=True)
            if ":" not in text:
                continue
            label, _, value = text.partition(":")
            label, value = label.strip().lower(), value.strip()
            if label == "группа":  # "Group: XX (Category name)"
                m = re.match(r"^\S+\s*\((.+)\)\s*$", value)
                row["Category (source)"] = m.group(1).strip() if m else value
            elif label in LABEL_TO_FIELD:
                row[LABEL_TO_FIELD[label]] = value

    # Description: the <p> that follows the <b>Описание</b> heading
    for b in main.find_all("b"):
        if b.get_text(strip=True) == "Описание":
            p = b.find_next_sibling("p")
            if p is not None:
                for br in p.find_all("br"):
                    br.replace_with("\n")
                lines = [re.sub(r"\s+", " ", ln).strip() for ln in p.get_text().split("\n")]
                row["Description"] = "\n".join(ln for ln in lines if ln)
            break

    return row


def category_slug(url):
    return re.sub(r"^.*/|\.html$", "", url.rstrip("/"))


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def parse_one_category(cat_url, session):
    print(f"Category: {cat_url}")
    links = get_product_links(cat_url, session)
    print(f"  Products found: {len(links)}. Opening each card...")
    rows = []
    for i, link in enumerate(links, 1):
        try:
            row = parse_product(link, session)
            rows.append(row)
            print(f"  [{i}/{len(links)}] {row['Name']}")
        except Exception as e:  # one bad card must not stop the whole run
            print(f"  [{i}/{len(links)}] Error on {link}: {e}")
        time.sleep(DELAY_BETWEEN_PRODUCTS)
    return rows


def main():
    parser = argparse.ArgumentParser(description="Catalog scraper -> CSV")
    parser.add_argument("urls", nargs="+", help="One or more category page URLs")
    parser.add_argument("-o", "--output", default="result.csv", help="Output file (without --outdir)")
    parser.add_argument("--outdir", help="Write one CSV per category here; finished categories are skipped on re-run")
    args = parser.parse_args()

    session = requests.Session()

    if args.outdir:
        os.makedirs(args.outdir, exist_ok=True)
        for i, cat_url in enumerate(args.urls, 1):
            out_path = os.path.join(args.outdir, category_slug(cat_url) + ".csv")
            print(f"\n=== Category {i}/{len(args.urls)} ===")
            if os.path.exists(out_path):
                print(f"  {out_path} already exists - skipping (resume mode)")
                continue
            try:
                rows = parse_one_category(cat_url, session)
            except Exception as e:
                print(f"  Could not open category: {e} (re-run later, it will be picked up)")
                continue
            if rows:
                write_csv(out_path, rows)
                print(f"  Saved: {out_path} ({len(rows)} products)")
        print("\nDone. To merge: python merge_csv.py", args.outdir, "-o result_all.csv")
        return

    all_rows = []
    for cat_url in args.urls:
        try:
            all_rows.extend(parse_one_category(cat_url, session))
        except Exception as e:
            print(f"  Could not open category: {e}")
    if not all_rows:
        print("Nothing found, no file written.")
        sys.exit(1)
    write_csv(args.output, all_rows)
    print(f"\nDone. {len(all_rows)} products -> {args.output}")


if __name__ == "__main__":
    main()
