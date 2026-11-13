"""Build sitemap-listings.xml for www.hauptrealty.com.

Crawls the site's own search pages (?pg=1,2,3...) and collects every
listing detail URL. Runs daily on GitHub Actions.
"""
import re, time, sys, datetime, urllib.request, urllib.error
from xml.sax.saxutils import escape

BASE = "https://www.hauptrealty.com"
SEEDS = [
    "/edmonton/", "/sherwood-park/", "/spruce-grove/", "/stony-plain/",
    "/leduc/", "/beaumont/", "/fort-saskatchewan/", "/devon/", "/morinville/",
    "/acreages-for-sale-edmonton/", "/land-for-sale-alberta/", "/alberta-lake-properties-for-sale/",
    "/edmonton-condos/",
]
LINK = re.compile(r'/property-search/detail/\d+/[A-Za-z0-9]+/[a-z0-9\-]+/')
UA = "HauptRealtySitemapBot/1.0 (+https://www.hauptrealty.com/)"
MAX_PAGES = 800


def get(url):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return e.code, ""
            time.sleep(10 * (attempt + 1))
        except Exception:
            time.sleep(10 * (attempt + 1))
    return 0, ""


def main():
    urls, log = set(), []
    for seed in SEEDS:
        found_seed, empty_run = 0, 0
        for pg in range(1, MAX_PAGES + 1):
            st, html = get(BASE + seed + (f"?pg={pg}" if pg > 1 else ""))
            links = set(LINK.findall(html))
            new = links - urls
            urls |= links
            found_seed += len(new)
            if not links:
                break
            empty_run = empty_run + 1 if not new else 0
            if empty_run >= 3:
                break
            time.sleep(1.2)
        log.append(f"{seed}: +{found_seed} (pages to {pg})")
        print(log[-1], flush=True)
    # first page of every content page in the site's own sitemap (towns, counties, lakes, commercial...)
    st, sm = get(BASE + "/sitemap.xml")
    pages = re.findall(r"<loc>https://www.hauptrealty.com(/[^<]*)</loc>", sm)
    for sub in [p for p in pages if p.endswith(".xml")]:
        st, sx = get(BASE + sub)
        pages += re.findall(r"<loc>https://www.hauptrealty.com(/[^<]*)</loc>", sx)
    pages = list(dict.fromkeys(pages))
    before = len(urls)
    for p in pages:
        if p.endswith(".xml") or p in SEEDS:
            continue
        st, html = get(BASE + p)
        urls |= set(LINK.findall(html))
        time.sleep(1.0)
    print(f"sitemap pages: {len(pages)} scanned, +{len(urls) - before}", flush=True)
    if len(urls) < 500:
        print("Too few listing URLs found, keeping the previous sitemap.", file=sys.stderr)
        sys.exit(1)
    today = datetime.date.today().isoformat()
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in sorted(urls):
        parts.append(f"<url><loc>{escape(BASE + u)}</loc><lastmod>{today}</lastmod></url>")
    parts.append("</urlset>")
    import os
    os.makedirs("site", exist_ok=True)
    open("site/sitemap-listings.xml", "w").write("\n".join(parts))
    open("site/index.html", "w").write(
        "<!doctype html><meta charset=utf-8><title>Haupt Realty sitemaps</title>"
        f"<p>Listing sitemap for www.hauptrealty.com: <a href=sitemap-listings.xml>sitemap-listings.xml</a> "
        f"({len(urls)} URLs, built {today}).</p>")
    # Google Search Console ownership file for this GitHub Pages site
    open("site/google2a01a90a5899b508.html", "w").write("google-site-verification: google2a01a90a5899b508.html")
    open("site/.nojekyll", "w").write("")
    print(f"TOTAL {len(urls)}")


if __name__ == "__main__":
    main()
