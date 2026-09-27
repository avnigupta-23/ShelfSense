"""
ShelfSense — step 5 fixture: barcodes.

A billing/scanning station identifies products by the barcode printed on the
pack (EAN-13; Indian products start with 890). Real codes come from the shop's
billing software or GS1 India. These are made-up but valid-format codes so the
scanner features can be tested.

Writes data/barcodes.json: {"<ean13>": "<sku_id>", ...}
"""

import json, random
from pathlib import Path

DATA = Path(__file__).resolve().parent
RNG = random.Random(20260920)


def ean13(first12):
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(first12))
    return first12 + str((10 - total % 10) % 10)


def main():
    catalogue = json.loads((DATA / "catalogue.json").read_text())
    codes, used = {}, set()
    for c in catalogue:
        while True:
            code = ean13("890" + "".join(str(RNG.randint(0, 9)) for _ in range(9)))
            if code not in used:
                break
        used.add(code)
        codes[code] = c["sku_id"]
    (DATA / "barcodes.json").write_text(json.dumps(codes, indent=2))
    print(f"barcodes: {len(codes)} EAN-13 codes")


if __name__ == "__main__":
    main()
