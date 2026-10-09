"""Tests mobiles automatiques : débordement, textes trop petits, cibles tactiles.

Usage : pip install playwright && playwright install chromium
        python3 tools/test_mobile.py "$PWD"
"""
import asyncio
import sys

from playwright.async_api import async_playwright

ROOT = sys.argv[1]
PAGES = ["index", "tarifs", "reglementation"]
WIDTHS = [320, 360, 390, 414, 768]

CHECK_JS = """() => {
  const vw = document.documentElement.clientWidth;
  const out = {overflow: [], smallText: [], smallTap: []};
  const visible = e => { const s = getComputedStyle(e); const r = e.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0; };
  const label = e => (e.tagName + '.' + (e.className || '') + ' "' + (e.innerText || '').trim().slice(0, 30) + '"');
  for (const e of document.querySelectorAll('body *')) {
    if (!visible(e) || e.closest('.bg-layer') || e.closest('svg')) continue;
    const r = e.getBoundingClientRect();
    if (r.right > vw + 1 || r.left < -1) out.overflow.push(label(e) + ' ' + Math.round(r.left) + '→' + Math.round(r.right));
    const own = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (own && parseFloat(getComputedStyle(e).fontSize) < 11.5) out.smallText.push(label(e) + ' ' + getComputedStyle(e).fontSize);
  }
  for (const a of document.querySelectorAll('a, button')) {
    if (!visible(a)) continue;
    const r = a.getBoundingClientRect();
    if (r.height < 32 && !a.closest('p') && !a.closest('footer') && !a.closest('.page-footer')) out.smallTap.push(label(a) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height));
  }
  return out;
}"""


async def main():
    failures = 0
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for w in WIDTHS:
            ctx = await browser.new_context(viewport={"width": w, "height": 800}, is_mobile=True, has_touch=True)
            page = await ctx.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            for name in PAGES:
                await page.goto(f"file://{ROOT}/{name}.html")
                await page.add_style_tag(content=".reveal{opacity:1!important;transform:none!important}")
                await page.wait_for_timeout(300)
                sw = await page.evaluate("document.documentElement.scrollWidth")
                res = await page.evaluate(CHECK_JS)
                bad = sw > w or res["overflow"] or res["smallTap"] or errors
                failures += bool(bad)
                print(f"[{'KO' if bad else 'OK'}] {name} @{w}px scrollWidth={sw}")
                for k in ("overflow", "smallTap", "smallText"):
                    for item in res[k][:6]:
                        print(f"      {k}: {item}")
                for e in errors:
                    print("      js:", e)
                errors.clear()
            await ctx.close()
        await browser.close()
    print("ÉCHECS:", failures)


asyncio.run(main())
