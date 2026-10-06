# Catalog Scraper: product catalog to clean CSV

A Python scraper that turns a large product catalog website into spreadsheet-ready CSV files. It opens every product card (not just the listing page) to collect the unique description and the labelled technical specs.

This is a sample from a real project: an industrial pump catalog on a Russian-language website. **6,153 products from 56 categories** were collected in about 35 minutes, unattended, and the product count of every category matched the site exactly.

Full write-up with the verification steps and edge cases: [Scraping_Case_Study.pdf](Scraping_Case_Study.pdf)

## What it does

- Reads each category listing and opens every product card.
- Extracts name, model, source URL, category, full description and six specs: flow, head, power, RPM, weight, dimensions.
- Writes one CSV per category, then an optional merge script combines them into one file.

## Why it is reliable

- **Parses by label, not by position.** Specs are matched by their on-page labels, so products with missing fields, extra fields or a different field order still parse correctly. A misspelled label on the source site is handled too.
- **Resumable.** One CSV is written as soon as a category finishes. If the run is interrupted, run the same command again: finished categories are skipped.
- **Fault isolation.** A failing page is logged and skipped; it never stops the whole run.
- **Polite crawling.** Requests are spaced out so the target site is not overloaded.
- **Excel-friendly output.** Semicolon-delimited, UTF-8 with BOM, so Cyrillic text and multi-line descriptions open correctly in Excel and import cleanly into a CMS.

## Usage

```bash
pip install -r requirements.txt

# Several categories, one CSV per category (resumable)
python catalog_scraper.py URL1 URL2 URL3 --outdir results

# One or two categories into a single file
python catalog_scraper.py URL1 -o result.csv

# Merge per-category files into one CSV
python merge_csv.py results -o result_all.csv
```

Requires Python 3.8+, `requests`, `beautifulsoup4`.

## How the data was verified

Before the full run, products were counted in every category from the listing pages. After the run, those counts were compared with the rows in each output file (all 56 matched). Every file was then audited for empty names, empty descriptions, products without specs and duplicate links, and sample product pages in five categories were checked by hand.

Gaps that exist on the source site itself (24 products without a description, 15 without specs) were left empty and reported to the client instead of being guessed.

## Sample output

| Model | Flow, m3/h | Head, m | Power, kW | RPM | Weight, kg | Dimensions, mm |
|---|---|---|---|---|---|---|
| 12НДСР | 1080 | 68 | 250 | 1450 | 1174 | 1358x1392x1020 |
| 2ГНОМ 10-10 | 10 | 10 | 1.1 | 2900 | 20 | 210x210x420 |
| ЦНП-100/40 | 100 | 40 | 30 | 1450 | 382 | 800x600x1100 |

Only a few sample rows are shown here. The full delivered dataset belongs to the client and is not part of this repository.

## Files

| File | Purpose |
|---|---|
| `catalog_scraper.py` | The scraper |
| `merge_csv.py` | Merges per-category CSV files into one |
| `Scraping_Case_Study.pdf` | One-page case study |
| `requirements.txt` | Dependencies |

## Contact

Dmitry Khovzun. Available for web scraping, data extraction and automation projects.
