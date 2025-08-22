
def get_todays_event():
    """
    Wikipedia (EN) 'Selected anniversaries' sayfasının Events bölümünden,
    bugünün (UTC) rastgele bir olayını döndürür. Harici kütüphane gerekmez.
    """
    import re
    import requests
    from datetime import datetime, timezone


    USER_AGENT = "WhatHappenedTodayBot/1.0 (contact: you@example.com)"
    API_URL = "https://en.wikipedia.org/w/api.php"
    MONTHS_EN = ["","January","February","March","April","May","June",
                 "July","August","September","October","November","December"]

    now = datetime.now(timezone.utc)
    page_title = f"Wikipedia:Selected anniversaries/{MONTHS_EN[now.month]} {now.day}"

    def mw_get(params):
        r = requests.get(API_URL, params=params,
                         headers={"User-Agent": USER_AGENT}, timeout=20)
        r.raise_for_status()
        return r.json()

    # 1) 'Events' bölüm indexini bul
    sec = mw_get({"action":"parse","page":page_title,"prop":"sections","format":"json"})
    if "error" in sec:
        return "No notable event could be found for today."

    events_index = None
    for s in sec.get("parse", {}).get("sections", []):
        if s.get("line","").strip().lower() == "events":
            events_index = s.get("index")
            break

    # 2) Events wikitext (varsa), yoksa tüm sayfa wikitext
    if events_index is not None:
        part = mw_get({"action":"parse","page":page_title,
                       "prop":"wikitext","section":events_index,"format":"json"})
        wt = (part.get("parse", {}).get("wikitext", {}) or {}).get("*")
    else:
        whole = mw_get({"action":"parse","page":page_title,
                        "prop":"wikitext","format":"json"})
        wt = (whole.get("parse", {}).get("wikitext", {}) or {}).get("*")

    if not wt:
        # Fallback: bazen başka sayfa formatı
        alt_title = page_title.replace("Wikipedia:Selected anniversaries/", "Portal:Current events/On this day/")
        whole = mw_get({"action":"parse","page":alt_title,"prop":"wikitext","format":"json"})
        wt = (whole.get("parse", {}).get("wikitext", {}) or {}).get("*")
        if not wt:
            return "No notable event could be found for today."

    # 3) Bullet maddeleri çek
    lines = [ln.strip() for ln in wt.splitlines() if ln.strip().startswith("*")]
    if not lines:
        return "No notable event could be found for today."

    # 4) Temizlik
    def clean(text):
        # {{...}} şablonları (basit)
        for _ in range(5):
            text = re.sub(r"\{\{[^{}]*\}\}", "", text)
        # [[Hedef|Etiket]] -> Etiket; [[Hedef]] -> Hedef
        text = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", text)
        text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
        # <ref>…</ref>, <ref .../>, diğer HTML etiketleri
        text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.DOTALL)
        text = re.sub(r"<ref[^>]*/>", "", text)
        text = re.sub(r"</?[^>]+>", "", text)
        # HTML entity'ler ve boşluklar
        text = text.replace("&nbsp;"," ").replace("&amp;","&")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    bullets = [clean(ln.lstrip("* ").strip()) for ln in lines]
    bullets = [b for b in bullets if b]

    if not bullets:
        return "No notable event could be found for today."

    # 5) Rastgele bir olay döndür
    import random
    return random.choice(bullets)

print(get_todays_event())