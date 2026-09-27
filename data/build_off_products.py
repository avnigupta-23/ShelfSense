"""
ShelfSense — product list for India from Open Food Facts.

Open Food Facts (openfoodfacts.org) is an open, crowd-sourced product database.
Its data is under the Open Database License (ODbL): anyone may use it, but the app
must credit Open Food Facts, and a list derived from it must stay under the ODbL.
(Blinkit and similar apps don't allow copying their listings, so we don't use them.)

Input  data/open_food_facts/india_products.tsv
         code, name, brand, quantity, categories — products tagged as sold in India,
         most-scanned first. Made on 17 Sep 2026 with the Open Food Facts search service
         (search.openfoodfacts.org, 80 pages x 100). To refresh it:
           python3 data/build_off_products.py --refresh     (streams the nightly export,
           about 1 GB, and keeps only products sold in India)
Output data/open_food_facts/india_products.json   [[barcode, name, brand, size, type], ...]
         used by engine/build_screen.py for "Add a product without scanning".
"""
import argparse, csv, gzip, io, json, re, sys, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent / "open_food_facts"
TSV, OUT = HERE / "india_products.tsv", HERE / "india_products.json"
EXPORT = "https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz"

RULES = [  # first match wins; same order as the app's online lookup
    ("Dairy", r"\bmilks?\b|dairies|dairy|yogurt|curd|paneer|cheese|butter|ghee|dahi|lassi|buttermilk"),
    ("Beverages", r"beverage|drink|water|juice|\btea|coffee|soda|cola|squash|syrup"),
    ("Biscuits", r"biscuit|cookie|cracker|rusk|wafer"),
    ("Noodles", r"noodle|pasta|vermicelli|macaroni"),
    ("Confection", r"chocolate|cand(y|ies)|confection|sweets|chewing|toffee|lollipop|mithai"),
    ("Snacks", r"snack|chips|crisps|namkeen|bhujia|popcorn|puffed"),
    ("Oil", r"\boils?\b|vanaspati"),
    ("Staples", r"flour|atta|rice|cereal|grain|pulse|lentil|\bdals?\b|sugar|legume|oats|flakes|muesli|besan|semolina|suji|poha|bread"),
    ("Spices", r"spice|masala|condiment|\bsalts?\b|pickle|seasoning"),
    ("Spreads", r"spread|jam|sauce|ketchup|honey|chutney|mayonnaise"),
    ("Personal", r"soap|shampoo|toothpaste|cosmetic|hygiene|deodorant|cream|lotion"),
    ("Home Care", r"detergent|cleaning|dishwash|cleaner|disinfect"),
]


def category(tags, name=""):
    text = (tags.replace("foods-and-beverages", "foods") + " " + name).lower().replace("-", " ")
    for kind, rx in RULES:
        if re.search(rx, text):
            return kind
    return "Other"


def valid_ean(code):
    if not re.fullmatch(r"\d{8}|\d{12,13}", code):
        return False
    d = [int(x) for x in code.zfill(13)]
    return (10 - sum(x * (3 if i % 2 else 1) for i, x in enumerate(d[:12])) % 10) % 10 == d[12]


def tidy(name):
    name = re.sub(r"\s+", " ", name).strip(" -,.")
    return name[:1].upper() + name[1:] if name.islower() else name


def refresh():
    """Stream the nightly export and keep products sold in India (needs about 1 GB of download)."""
    rows = []
    with urllib.request.urlopen(urllib.request.Request(EXPORT, headers={"User-Agent": "ShelfSense/0.9 (hackathon)"})) as r:
        text = io.TextIOWrapper(gzip.GzipFile(fileobj=r), encoding="utf-8", errors="replace")
        csv.field_size_limit(sys.maxsize)
        for row in csv.DictReader(text, delimiter="\t"):
            if "en:india" not in (row.get("countries_tags") or ""):
                continue
            name = row.get("product_name_en") or row.get("product_name") or ""
            tags = " ".join(t[3:] for t in (row.get("categories_tags") or "").split(",") if t.startswith("en:"))
            rows.append((int(row.get("unique_scans_n") or 0), [row["code"], name, (row.get("brands") or "").split(",")[0],
                                                                 row.get("quantity") or "", tags]))
    rows.sort(key=lambda x: -x[0])
    with open(TSV, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["code", "name", "brand", "quantity", "categories"])
        for _, r in rows:
            w.writerow([str(x).replace("\t", " ").replace("\n", " ") for x in r])
    print(f"refreshed {TSV.name}: {len(rows)} products")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="download the latest Open Food Facts export first")
    args = ap.parse_args()
    if args.refresh:
        refresh()
    root = HERE.parent
    built_in = set(json.loads((root / "barcodes.json").read_text()))
    out, seen = [], set()
    with open(TSV, newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            code = r["code"].strip()
            name = tidy(r["name"] or "")
            if code in seen or code in built_in or not valid_ean(code) or code.startswith("2"):
                continue
            if len(name) < 2 or not re.search(r"[A-Za-z]", name) or re.search(r"alcohol|pet-food", r["categories"] or ""):
                continue
            if not code.startswith("890") and not (r["brand"] or "").strip():
                continue                                  # imported items without a brand are mostly noise
            seen.add(code)
            out.append([code, name[:70], (r["brand"] or "").strip()[:30], (r["quantity"] or "").strip()[:20],
                        category(r["categories"] or "", name)])
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    by = {}
    for p in out:
        by[p[4]] = by.get(p[4], 0) + 1
    print(f"wrote {OUT.relative_to(root.parent)}: {len(out)} products "
          f"({sum(p[0].startswith('890') for p in out)} with Indian barcodes) — " +
          ", ".join(f"{k} {v}" for k, v in sorted(by.items(), key=lambda x: -x[1])))


if __name__ == "__main__":
    main()
