#!/usr/bin/env python3
"""Amazon UK product scraper.

Two modes:
  --uk-proxy   Use IP Royal UK residential proxy for accurate GBP price, UK delivery,
               and Prime indicator. Paid per request. Requires proxy URL.
  (default)    Use camofox stealth browser (free, runs locally). Prices in EUR from
               Finnish IP; delivery shows for Finland.

Usage:
  # ASIN lookup via UK proxy (recommended for price/delivery accuracy):
  python3 scrape_amazon_uk.py --asins B0972BP9YR B09NYMR2KJ --uk-proxy

  # Search for products (camofox finds ASINs), then fetch details via UK proxy:
  python3 scrape_amazon_uk.py --search "rtx 4060" --max-results 3 --uk-proxy

  # Camofox-only (no proxy cost, specs still accurate):
  python3 scrape_amazon_uk.py --asins B0972BP9YR

  # Save JSON output:
  python3 scrape_amazon_uk.py --asins B0972BP9YR --uk-proxy --out /tmp/parts.json

Proxy URL:
  Set a residential proxy env var (PROXYCHEAP_GB_PROXY primary, or IPROYAL_UK_PROXY /
  IPROYAL_GB_PROXY fallback) or pass --proxy-url. Any residential proxy works.
  Format: http://user:pass@host:port
"""

import subprocess
import json
import re
import time
import sys
import argparse
import os
from typing import Optional

# ── camofox session constants ──────────────────────────────────────────────
SESSION_KEY = "amz-uk-scraper"
USER_ID = "pi-agent"

# ── default UK proxy URL (can override via env or --proxy-url) ────────────
DEFAULT_PROXY_URL = (
    os.environ.get("PROXYCHEAP_GB_PROXY")
    or os.environ.get("IPROYAL_UK_PROXY")
    or os.environ.get("IPROYAL_GB_PROXY", "")
)

# ── camofox helpers ────────────────────────────────────────────────────────

def camofox(*args, timeout=60) -> dict:
    cmd = ["camofox"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"camofox failed: {result.stderr[:400]}")
    return json.loads(result.stdout)


def get_snapshot(tab_id: str) -> str:
    r = camofox("tabs", "snapshot", "get", tab_id, "--agent", "--user-id", USER_ID)
    return r.get("results", {}).get("snapshot", "")


def navigate(tab_id: str, url: str, retries: int = 2):
    for attempt in range(retries + 1):
        try:
            camofox("tabs", "navigate", "create", tab_id, "--agent", "--user-id", USER_ID, "--url", url, timeout=45)
            time.sleep(5)
            return
        except RuntimeError as e:
            if attempt < retries and ("EOF" in str(e) or "connection reset" in str(e) or "reset by peer" in str(e)):
                print(f"[warn] Navigate attempt {attempt+1} failed (transient), retrying in 3s...")
                time.sleep(3)
            else:
                raise


def click_ref(tab_id: str, ref: str):
    camofox("tabs", "click", "create", tab_id, "--agent", "--user-id", USER_ID, "--ref", ref)


def find_ref(snap: str, text: str) -> Optional[str]:
    m = re.search(rf'(?:button|link) "{re.escape(text)}" \[(e\d+)\]', snap)
    return m.group(1) if m else None


def find_ref_partial(snap: str, partial: str) -> Optional[str]:
    m = re.search(rf'(?:button|link) "[^"]*{re.escape(partial)}[^"]*" \[(e\d+)\]', snap, re.IGNORECASE)
    return m.group(1) if m else None


def handle_challenges(tab_id: str, max_attempts: int = 8) -> bool:
    for attempt in range(max_attempts):
        wait = 5 if attempt == 0 else 3
        time.sleep(wait)
        snap = get_snapshot(tab_id)

        if not snap:
            print("[warn] Empty snapshot, retrying...")
            continue

        is_challenge = (
            "Click the button below to continue shopping" in snap
            or "Select your cookie preferences" in snap
            or "An error occurred" in snap
            or "working on the problem" in snap
        )
        is_404 = "not a functioning page" in snap or "Looking for something?" in snap

        if is_404:
            return False
        if not is_challenge and "Amazon" in snap and len(snap) > 2000:
            print(f"[info] Page ready (attempt {attempt})")
            return True

        if "Click the button below to continue shopping" in snap:
            ref = find_ref(snap, "Continue shopping")
            print(f"[info] Bot challenge page (attempt {attempt}), ref={ref}")
            if ref:
                click_ref(tab_id, ref)
                time.sleep(6)
            else:
                time.sleep(5)
            continue

        if "Select your cookie preferences" in snap or ("cookie" in snap.lower() and "Accept" in snap):
            ref = find_ref(snap, "Accept")
            print(f"[info] Cookie consent (attempt {attempt}), ref={ref}")
            if ref:
                click_ref(tab_id, ref)
                time.sleep(4)
            continue

        if "An error occurred" in snap or "working on the problem" in snap:
            print(f"[warn] Amazon error page (attempt {attempt}), retrying...")
            time.sleep(5)
            continue

    return False


def establish_session() -> Optional[str]:
    print("[info] Starting camofox session on Amazon UK...")
    r = camofox("tabs", "create", "--agent", "--url", "https://www.amazon.co.uk",
                "--session-key", SESSION_KEY, "--user-id", USER_ID)
    tab_id = r["data"]["tabId"]
    print(f"[info] Tab created: {tab_id}")
    time.sleep(6)
    ok = handle_challenges(tab_id)
    if not ok:
        try:
            snap = get_snapshot(tab_id)
            print(f"[debug] Final snapshot: {snap[:200]!r}")
        except Exception:
            pass
        return None
    print("[info] Session established")
    return tab_id


# ── UK proxy HTTP scraping (accurate GBP prices) ──────────────────────────

def _proxy_request(url: str, proxy_url: str, retries: int = 2) -> Optional[str]:
    """Fetch URL via residential UK proxy. Returns HTML or None on failure."""
    import urllib.request
    import urllib.error
    import urllib.parse

    proxy_handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
    opener = urllib.request.build_opener(proxy_handler)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept-Language": "en-GB,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "identity",
        },
    )
    for attempt in range(retries + 1):
        try:
            with opener.open(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            if attempt < retries:
                print(f"[warn] Proxy fetch attempt {attempt+1} failed: {e}, retrying...")
                time.sleep(3)
            else:
                print(f"[error] Proxy fetch failed: {e}")
                return None


def scrape_product_via_proxy(asin: str, proxy_url: str) -> dict:
    """Fetch Amazon UK product page through UK residential proxy and parse HTML."""
    from html.parser import HTMLParser

    url = f"https://www.amazon.co.uk/dp/{asin}"
    print(f"[info] Fetching {asin} via UK proxy...")
    html = _proxy_request(url, proxy_url)
    if not html:
        return {"asin": asin, "url": url, "error": "Proxy fetch failed"}

    # Use regex-based parsing (avoids BeautifulSoup dependency issues)
    def tag_text(pattern: str) -> Optional[str]:
        """Extract inner text from first matching HTML element."""
        m = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if not m:
            return None
        raw = m.group(1)
        # Strip HTML tags
        clean = re.sub(r'<[^>]+>', ' ', raw)
        clean = re.sub(r'\s+', ' ', clean).strip()
        # Decode common HTML entities
        for ent, char in [('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'), ('&nbsp;', ' '), ('&#39;', "'")]:
            clean = clean.replace(ent, char)
        return clean or None

    # ── title ──
    title = None
    for pat in [
        r'id="productTitle"[^>]*>\s*(.*?)\s*</span>',
        r'<title>([^<]+) ?: Amazon',
    ]:
        t = tag_text(pat)
        if t and len(t) > 10:
            title = t
            break

    # ── price (buy box) ──
    price = None
    for pat in [
        r'class="[^"]*priceToPay[^"]*"[^>]*>.*?<span[^>]*>(£[\d,]+\.?\d*)</span>',
        r'id="corePriceDisplay_desktop_feature_div"[^>]*>.*?(£[\d,]+\.?\d*)',
        r'id="corePrice_feature_div"[^>]*>.*?(£[\d,]+\.?\d*)',
        r'id="apex_offerDisplay_desktop"[^>]*>.*?(£[\d,]+\.?\d*)',
        r'id="priceblock_ourprice"[^>]*>\s*(£[\d,]+\.?\d*)',
        r'"priceAmount"\s*:\s*"?([\d.]+)"',
    ]:
        m = re.search(pat, html, re.DOTALL | re.IGNORECASE)
        if m:
            price = m.group(1).strip()
            if not price.startswith('£'):
                price = f'£{price}'
            break

    # ── availability ──
    availability = "Unknown"
    avail_raw = tag_text(r'id="availability"[^>]*>(.*?)</(?:span|div)>')
    if avail_raw:
        availability = avail_raw.strip()
    else:
        for pat in [r'In stock', r'Currently unavailable', r'Only \d+ left in stock', r'Temporarily out of stock']:
            if re.search(pat, html, re.IGNORECASE):
                availability = re.search(pat, html, re.IGNORECASE).group(0)
                break

    # ── delivery ──
    delivery = None
    delivery_raw = tag_text(r'id="mir-layout-DELIVERY_BLOCK[^"]*"[^>]*>(.*?)</div>')
    if delivery_raw:
        delivery = re.sub(r'\s+', ' ', delivery_raw).strip()
    if not delivery:
        m = re.search(r'(FREE delivery.*?(?:June|July|August|May|April|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)[^<]{0,30})', html)
        if m:
            delivery = re.sub(r'<[^>]+>', '', m.group(1)).strip()
    # Clean up trailing noise like ". Details" or "Details"
    if delivery:
        delivery = re.sub(r'\s*\.\s*Details.*$', '', delivery, flags=re.IGNORECASE).strip()
        delivery = re.sub(r'\s*Details.*$', '', delivery, flags=re.IGNORECASE).strip()

    # ── prime ──
    prime_eligible = bool(
        re.search(r'FREE delivery', html, re.IGNORECASE)
        and not re.search(r'Not\s+eligible\s+for\s+Prime', html, re.IGNORECASE)
    )

    # ── specs from productDetails_feature_div ──
    specs = {}
    specs_section = tag_text(r'id="productDetails_feature_div"[^>]*>(.*?)</(?:div|table)>\s*</div>')
    if not specs_section:
        # Try the full table
        specs_section = tag_text(r'id="productDetails_feature_div"(.*?)(?=id="[a-zA-Z])')

    # Parse <tr> rows from the tech spec table
    # Skip noisy/JS-heavy fields
    skip_keys = {"Customer Reviews", "Best Sellers Rank"}
    for row_m in re.finditer(
        r'<tr[^>]*>.*?<th[^>]*>(.*?)</th>.*?<td[^>]*>(.*?)</td>.*?</tr>',
        html, re.DOTALL | re.IGNORECASE
    ):
        key = re.sub(r'<[^>]+>', '', row_m.group(1)).strip()
        if not key or key in skip_keys or len(key) > 80:
            continue
        val = re.sub(r'<[^>]+>', ' ', row_m.group(2)).strip()
        val = re.sub(r'\s+', ' ', val)
        # Drop value if it looks like embedded JavaScript
        if 'P.when(' in val or 'function(' in val or len(val) > 300:
            continue
        if key and val:
            specs[key] = val

    # ── 404 detection ──
    if re.search(r'not a functioning page|Looking for something|Page Not Found', html, re.IGNORECASE):
        return {"asin": asin, "url": url, "error": "404 - Product not found on Amazon UK"}

    return {
        "asin": asin,
        "url": url,
        "source": "uk-proxy",
        "title": title,
        "price": price,
        "availability": availability,
        "delivery_estimate": delivery,
        "prime_eligible": prime_eligible,
        "specs": specs,
        "specs_raw": [f"{k} {v}" for k, v in specs.items()],
    }


# ── camofox-based product scraping ────────────────────────────────────────

def _extract_title(snap: str) -> Optional[str]:
    skip = {"About this item", "Product Information", "Frequently bought together",
            "Product description", "From the manufacturer"}
    for m in re.finditer(r'heading "([^"]+)" \[level=1\]', snap):
        t = m.group(1).strip()
        if t not in skip and len(t) > 10:
            return t
    return None


def _extract_price(snap: str) -> Optional[str]:
    m = re.search(r'text: ((?:£|GBP\s*|EUR\s*)[\d,]+\.?\d*)', snap)
    return m.group(1).strip() if m else None


def _extract_availability(snap: str) -> str:
    patterns = [
        r'text: (In stock)',
        r'text: (Currently unavailable)',
        r'text: (Only \d+ left in stock[^\n]*)',
        r'text: (Temporarily out of stock)',
        r'text: (Out of Stock)',
    ]
    for pat in patterns:
        m = re.search(pat, snap, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    if re.search(r'button "Add to basket"', snap):
        return "In stock"
    return "Unknown"


def _extract_delivery(snap: str) -> Optional[str]:
    buy_box_m = re.search(
        r'text: (?:£|GBP\s*|EUR\s*)[\d,]+\.?\d*\s+(.*?delivery.*?)(?:\.|$)',
        snap, re.IGNORECASE
    )
    if buy_box_m:
        return buy_box_m.group(1).strip() + "."
    date_m = re.search(
        r'text: ([^\n]*(?:FREE delivery|delivery (?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|\d))[^\n]*)',
        snap, re.IGNORECASE
    )
    return date_m.group(1).strip() if date_m else None


def _extract_prime(snap: str) -> bool:
    return any(re.search(p, snap, re.IGNORECASE) for p in [
        r'FREE delivery', r'Prime\s+delivery', r'Prime\s+eligible'
    ])


def _extract_specs(snap: str) -> list[str]:
    specs = []
    rowgroup_m = re.search(r'- rowgroup:\n((?:\s+- listitem: [^\n]+\n)+)', snap)
    if rowgroup_m:
        for m in re.finditer(r'listitem: (.+)', rowgroup_m.group(1)):
            specs.append(m.group(1).strip())
    return specs


def _parse_specs_to_dict(specs: list[str]) -> dict:
    result = {}
    known_keys = [
        "Graphics co-processor", "Graphics processor manufacturer",
        "Graphics RAM size", "Graphics RAM type", "GPU clock speed",
        "Graphics card interface", "Video output interface",
        "Compatible devices", "Included components",
        "Digital storage capacity", "Hard disk interface", "Hard disk description",
        "Hard disk form factor", "Connectivity technology", "Installation type",
        "Computer Memory Type", "Memory Speed", "Memory Clock Speed",
        "Memory Bandwidth", "Maximum Memory Size (dependent on memory type)",
        "CPU Model", "CPU Speed", "Processor Count", "Cache",
        "Number of Processors", "Socket type", "Chipset", "TDP",
        "Item model number", "Item part number", "Item Package Quantity",
        "Item Weight", "Product Dimensions", "Date First Available",
        "Country of Origin", "Manufacturer", "Batteries", "ASIN",
        "Special features", "Special feature", "Colour", "Color",
        "Form factor", "Flash Memory Size", "GPU processor", "Brand", "RAM",
    ]
    for item in specs:
        matched = False
        for key in known_keys:
            if item.lower().startswith(key.lower()):
                result[key] = item[len(key):].strip()
                matched = True
                break
        if not matched:
            m = re.match(r'^([A-Z][a-z]+(?:\s+[a-z][a-z0-9/&-]*)*)\s+(.+)$', item)
            if m:
                result[m.group(1).strip()] = m.group(2).strip()
            else:
                result[item] = ""
    return result


def scrape_product_camofox(tab_id: str, asin: str) -> dict:
    url = f"https://www.amazon.co.uk/dp/{asin}"
    print(f"[info] Scraping {asin} via camofox...")
    navigate(tab_id, url)
    snap = get_snapshot(tab_id)

    if "Click the button below to continue shopping" in snap or "Select your cookie preferences" in snap:
        handle_challenges(tab_id)
        snap = get_snapshot(tab_id)

    if "not a functioning page" in snap or "Looking for something?" in snap:
        return {"asin": asin, "url": url, "error": "404 - Product not found on Amazon UK"}

    raw_specs = _extract_specs(snap)
    return {
        "asin": asin,
        "url": url,
        "source": "camofox",
        "title": _extract_title(snap),
        "price": _extract_price(snap),
        "availability": _extract_availability(snap),
        "delivery_estimate": _extract_delivery(snap),
        "prime_eligible": _extract_prime(snap),
        "specs_raw": raw_specs,
        "specs": _parse_specs_to_dict(raw_specs),
    }


def search_amazon_uk(tab_id: str, query: str, max_results: int = 5) -> list[str]:
    search_url = f"https://www.amazon.co.uk/s?k={query.replace(' ', '+')}"
    print(f"[info] Searching: {query}")
    navigate(tab_id, search_url)
    snap = get_snapshot(tab_id)
    if "Click the button below to continue shopping" in snap:
        handle_challenges(tab_id)
        snap = get_snapshot(tab_id)
    asins = list(dict.fromkeys(re.findall(r'/dp/([A-Z0-9]{10})', snap)))
    print(f"[info] Found {len(asins)} ASINs in search results")
    return asins[:max_results]


# ── output formatting ──────────────────────────────────────────────────────

def format_markdown_table(products: list[dict]) -> str:
    lines = []
    # Make the column header a clickable link to the product page
    def col_header(p: dict) -> str:
        title = p.get("title", p["asin"])[:40]
        url = p.get("url", "")
        return f"[{title}]({url})" if url else title

    lines.append("| Field | " + " | ".join(col_header(p) for p in products) + " |")
    lines.append("|-------|" + "|".join(["--------"] * len(products)) + "|")

    fields = [
        ("Buy link", "url"),
        ("ASIN", "asin"),
        ("Source", "source"),
        ("Price (GBP)", "price"),
        ("Availability", "availability"),
        ("Prime eligible", "prime_eligible"),
        ("Delivery (UK)", "delivery_estimate"),
    ]
    for label, key in fields:
        row = f"| {label} |"
        for p in products:
            val = p.get(key, "—")
            if val is None:
                val = "—"
            # Render the Buy link row as a clickable markdown link
            if key == "url" and val and val != "—":
                cell = f"[amazon.co.uk]({val})"
            else:
                cell = str(val)[:60]
            row += f" {cell} |"
        lines.append(row)

    all_spec_keys = []
    for p in products:
        for k in p.get("specs", {}).keys():
            if k not in all_spec_keys:
                all_spec_keys.append(k)
    for key in all_spec_keys:
        row = f"| {key} |"
        for p in products:
            val = p.get("specs", {}).get(key, "—")
            row += f" {str(val)[:60]} |"
        lines.append(row)

    return "\n".join(lines)


# ── main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Scrape Amazon UK product pages")
    parser.add_argument("--asins", nargs="+", help="ASIN(s) to scrape")
    parser.add_argument("--search", help="Search term to find ASINs (uses camofox)")
    parser.add_argument("--max-results", type=int, default=5, help="Max search results (default: 5)")
    parser.add_argument("--uk-proxy", action="store_true",
                        help="Use UK residential proxy for GBP prices and UK delivery info")
    parser.add_argument("--proxy-url", help="Override proxy URL (default: IPROYAL_UK_PROXY env var)")
    parser.add_argument("--out", help="Write JSON results to file")
    parser.add_argument("--no-table", action="store_true", help="Skip markdown table")
    args = parser.parse_args()

    if not args.asins and not args.search:
        parser.print_help()
        sys.exit(1)

    proxy_url = args.proxy_url or DEFAULT_PROXY_URL
    use_proxy = args.uk_proxy

    # Always need camofox for search; also for product scraping if not using proxy
    need_camofox = bool(args.search) or not use_proxy
    tab_id = None
    if need_camofox:
        tab_id = establish_session()
        if not tab_id:
            print("[error] Failed to start camofox session")
            sys.exit(1)

    try:
        asins = list(args.asins or [])
        if args.search:
            found = search_amazon_uk(tab_id, args.search, args.max_results)
            asins = asins + [a for a in found if a not in asins]

        if not asins:
            print("[error] No ASINs found or provided")
            sys.exit(1)

        products = []
        for asin in asins:
            try:
                if use_proxy:
                    product = scrape_product_via_proxy(asin, proxy_url)
                else:
                    product = scrape_product_camofox(tab_id, asin)

                products.append(product)
                print(f"  → {product.get('title', 'N/A')[:60]}")
                print(f"     Price: {product.get('price','?')}  Stock: {product.get('availability','?')}")
                print(f"     Prime: {product.get('prime_eligible','?')}  Delivery: {product.get('delivery_estimate','?')}")
                if product.get('specs'):
                    print(f"     Specs: {list(product['specs'].items())[:3]}")
            except Exception as e:
                print(f"[warn] Failed to scrape {asin}: {e}")
                products.append({"asin": asin, "error": str(e)})
            time.sleep(1)

        if args.out:
            with open(args.out, "w") as f:
                json.dump(products, f, indent=2)
            print(f"\n[info] Results written to {args.out}")

        if not args.no_table:
            valid = [p for p in products if "error" not in p]
            if valid:
                print("\n## Amazon UK Product Comparison\n")
                print(format_markdown_table(valid))

        print("\n## JSON Results\n```json")
        print(json.dumps(products, indent=2))
        print("```")

    finally:
        if tab_id:
            try:
                camofox("tabs", "delete", tab_id, "--agent", "--user-id", USER_ID)
            except Exception:
                pass


if __name__ == "__main__":
    main()
