import json
from playwright.sync_api import sync_playwright

JS = r"""
() => {
    const rows = Array.from(document.querySelectorAll('tr[data-index]'));
    const idx = rows.map(r => parseInt(r.getAttribute('data-index'))).filter(n => !isNaN(n));
    let scroller = null, el = rows[0];
    while (el) {
        const s = getComputedStyle(el);
        if ((s.overflowY === 'auto' || s.overflowY === 'scroll') && el.scrollHeight > el.clientHeight) { scroller = el; break; }
        el = el.parentElement;
    }
    const headerCb = document.querySelector('th input[type=checkbox]') || document.querySelector('thead input[type=checkbox]');
    return {
        renderedRows: rows.length,
        minIndex: idx.length ? Math.min.apply(null, idx) : null,
        maxIndex: idx.length ? Math.max.apply(null, idx) : null,
        scrollerTag: scroller ? scroller.tagName : null,
        scrollerClass: scroller ? String(scroller.className) : null,
        scrollerId: scroller ? scroller.id : null,
        scrollTop: scroller ? scroller.scrollTop : null,
        scrollHeight: scroller ? scroller.scrollHeight : null,
        clientHeight: scroller ? scroller.clientHeight : null,
        headerCheckboxFound: !!headerCb,
    };
}
"""

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    page = None
    for ctx in browser.contexts:
        for pg in ctx.pages:
            if "orcascan" in pg.url:
                page = pg
                break
    if not page:
        tabs = [pg.url[:70] for ctx in browser.contexts for pg in ctx.pages]
        print("Kein OrcaScan-Tab. Offene Tabs:", tabs)
        raise SystemExit

    print("URL:", page.url)
    info = page.evaluate(JS)
    print(json.dumps(info, indent=2, ensure_ascii=False))
