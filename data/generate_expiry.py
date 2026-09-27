"""
ShelfSense — expiry fixture: batches behind the 17 Sep shelf count.

The shelf count says how many pieces are on the shelf; this says when they
expire. In a real shop the shopkeeper would note dates for fresh and slow items
during the count (or accept the estimates).

To make the reminder worth testing, a few slow sellers get batches that expire
soon, and one batch has already expired.

Writes data/stock_lots.json: {"count_date", "lots": {sku: [{qty, exp, est}]}}
"""

import json, random, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))
from shelf import shelf_days, add_days  # noqa: E402

DATA = Path(__file__).resolve().parent
OUT = DATA.parent / "out"
RNG = random.Random(20260922)


def main():
    count = json.loads((DATA / "stock_count.json").read_text())
    d0 = count["count_date"]
    rates = {r["sku_id"]: r["est_daily_rate_recent"] for r in json.loads((OUT / "ledger.json").read_text())}
    have = {c["sku_id"]: c["on_hand"] for c in count["counts"] if c["on_hand"] > 0}

    # slow sellers holding several days of stock: the ones that can go stale
    slow = sorted((s for s, q in have.items() if q >= 2 and shelf_days(s) > 5),
                  key=lambda s: have[s] / max(rates.get(s, 0.1), 0.1), reverse=True)
    soon = {s: RNG.randint(3, 9) for s in slow[:5]}
    expired = slow[5] if len(slow) > 5 else None

    lots = {}
    for sku, q in have.items():
        life = shelf_days(sku)
        if life <= 5:                                    # fresh: today's or yesterday's stock
            lots[sku] = [{"qty": q, "exp": add_days(d0, RNG.randint(1, life)), "est": False}]
            continue
        if sku in soon:
            old = max(1, q // 2)
            lots[sku] = [{"qty": old, "exp": add_days(d0, soon[sku]), "est": False}]
            if q - old:
                lots[sku].append({"qty": q - old, "exp": add_days(d0, int(life * 0.8)), "est": True})
            continue
        if sku == expired:
            lots[sku] = [{"qty": 1, "exp": add_days(d0, -2), "est": False}]
            if q - 1:
                lots[sku].append({"qty": q - 1, "exp": add_days(d0, int(life * 0.7)), "est": True})
            continue
        lots[sku] = [{"qty": q, "exp": add_days(d0, int(life * RNG.uniform(0.3, 0.9))), "est": True}]

    (DATA / "stock_lots.json").write_text(json.dumps({"count_date": d0, "lots": lots}, indent=1))
    print(f"stock batches for {len(lots)} products; expiring soon: {', '.join(soon)}; "
          f"already expired: {expired}")


if __name__ == "__main__":
    main()
