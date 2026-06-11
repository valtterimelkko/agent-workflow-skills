---
name: amazon-uk-scraper
description: "Scrape Amazon UK (amazon.co.uk) product pages to check availability, Prime eligibility, delivery estimates (UK), GBP price, and full technical specifications. Use this skill whenever an agent needs to: look up Amazon UK product listings, check if a computer part or product is in stock on Amazon UK, compare product specs across multiple ASINs, find product model numbers to look up on other sites, research GPU/CPU/RAM/SSD or any hardware for compatibility, verify Prime delivery eligibility, or search Amazon UK and return structured product data. Always use this skill for any Amazon UK product research, price checking, availability verification, or parts-comparison task."
---

# Amazon UK Product Scraper

**Everything is handled by one Python script — no separate skill invocations needed.** Bot bypass, cookie consent, proxy routing, and data extraction are all built in.

Script path:
```
./skills/amazon-uk-scraper/scripts/scrape_amazon_uk.py
```

---

## How to run it

```bash
# ── RECOMMENDED: UK proxy mode — GBP prices + real UK delivery dates ─────
python3 ./skills/amazon-uk-scraper/scripts/scrape_amazon_uk.py \
  --asins B0972BP9YR B09NYMR2KJ --uk-proxy

# Search by keyword, then scrape the top N results:
python3 ./skills/amazon-uk-scraper/scripts/scrape_amazon_uk.py \
  --search "rtx 4060 graphics card" --max-results 3 --uk-proxy

# Save JSON to a file:
python3 ./skills/amazon-uk-scraper/scripts/scrape_amazon_uk.py \
  --asins B0972BP9YR --uk-proxy --out /tmp/parts.json

# ── Free mode: camofox browser (no proxy cost, prices in EUR) ────────────
python3 ./skills/amazon-uk-scraper/scripts/scrape_amazon_uk.py \
  --asins B0972BP9YR
```

---

## Two modes — choose based on what you need

| Mode | Flag | Price currency | Delivery dates | Cost |
|---|---|---|---|---|
| **UK proxy** | `--uk-proxy` | GBP ✓ | UK ✓ | Paid (IP Royal) |
| **Camofox** | *(default, no flag)* | EUR (server is in Finland) | Finland | Free |

Use `--uk-proxy` whenever GBP pricing or UK delivery accuracy matters.  
Use camofox-only when only checking specs/availability and price currency is irrelevant.

To use `--uk-proxy`, configure your own UK residential proxy or adapt the script to your own proxy setup. Do not rely on any embedded credentials.

---

## What gets extracted per product

| Field | Description |
|---|---|
| `title` | Full product name |
| `asin` | Amazon UK ASIN |
| `price` | GBP price (with `--uk-proxy`) or EUR (camofox) |
| `availability` | "In stock" / "Currently unavailable" / "Only N left in stock" |
| `prime_eligible` | `true` when FREE delivery is shown (proxy for Prime — anonymous session) |
| `delivery_estimate` | UK delivery text, e.g. "FREE delivery Wednesday, 10 June" |
| `specs` | Dict of key/value tech specs (25–30 fields in proxy mode, ~10 in camofox mode) |
| `specs_raw` | Same specs as a flat list of "Key Value" strings |

---

## What the script handles internally — nothing else needed

- **Bot protection bypass**: handled by camofox (Camoufox stealth Firefox browser). The script creates and manages the camofox session, handles any "Continue shopping" challenge page, and accepts cookie consent automatically.
- **UK pricing/delivery**: handled by the `--uk-proxy` flag, which routes HTTP requests through an IP Royal UK residential proxy. No need to invoke a separate residential-proxy skill if you already configured the script for your own proxy setup.
- **Search**: `--search` uses camofox to load the Amazon UK search results page and extract ASINs. No manual browsing needed.
- **Cleanup**: the script closes its own camofox tab on exit.

Do **not** invoke the `camofox` skill, `residential-proxy` skill, or `agent-browser` skill separately — the script already does all of this.

---

## Preflight check (camofox mode only)

Before running in camofox mode (without `--uk-proxy`), verify the browser is up:
```bash
camofox camofox-browser-health --agent
# Should show: "ok": true, "browserRunning": true
```

If it's down:
```bash
docker start camofox-browser
```

In `--uk-proxy` mode there's no preflight needed — it uses plain HTTP via the proxy.

---

## Finding ASINs

If you only have product names, use `--search`:
```bash
python3 ./skills/amazon-uk-scraper/scripts/scrape_amazon_uk.py \
  --search "AMD Ryzen 7 7800X3D" --max-results 3 --uk-proxy
```

The script searches Amazon UK, pulls ASINs from the results page, then scrapes each product.

---

## Output

The script prints three things:

1. **Per-product summary** (title, price, stock, delivery, first 3 specs) — for quick review
2. **Markdown comparison table** — columns per product, rows per field + spec
3. **JSON blob** — full structured data for programmatic use

Always parse the JSON block for downstream tasks. The table is for human display.

---

## Computer parts use case

For checking compatible parts for a specific PC build:
- `specs["Graphics Card Interface"]` or `specs["Graphics card interface"]` → PCI Express slot type
- `specs["Form Factor"]` → M.2 2280, ATX, etc.
- `specs["Hard Disk Interface"]` → NVMe, SATA
- `specs["Socket type"]` → CPU socket
- `specs["Compatible Devices"]` → Desktop, Laptop
- `specs["Model Number"]` / `specs["Manufacturer Part Number"]` → use these to search manufacturer or review sites for the full datasheet

The model name from `title` can also be passed directly to `web-search` or `camofox` to find spec sheets, benchmarks, or compatibility guides on other sites.

---

## Reporting

The script's markdown table already includes a **clickable buy link** in the header (product title links to the Amazon UK product page) and a **Buy link** row with `[amazon.co.uk](url)`. Present this table directly to the user so they can click through to purchase.

When summarising results for the user, always include the direct Amazon UK URL for each recommended product:

```
## Amazon UK Product Research

| Product | ASIN | Buy link | Price | In Stock | Prime | Delivery | Key Specs |
|---------|------|----------|-------|----------|-------|----------|-----------|
| [Title](https://www.amazon.co.uk/dp/ASIN) | ASIN | [amazon.co.uk](https://...) | £X | Yes | Yes | FREE | ... |
```

Note in the summary whether prices are GBP (proxy mode) or EUR (camofox mode).
