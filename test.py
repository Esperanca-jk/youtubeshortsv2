import requests
import re
from datetime import datetime

def get_todays_events():
    """
    Fetch all 'On this day' events from English Wikipedia for today's UTC date.
    Returns a list of event strings (year + detail).
    """
    # Tarih -> Wikipedia sayfa formatı: Wikipedia:Selected anniversaries/Month Day
    MONTHS_EN = [
        "", "January","February","March","April","May","June",
        "July","August","September","October","November","December"
    ]
    now = datetime.utcnow()
    page_title = f"Wikipedia:Selected anniversaries/{MONTHS_EN[now.month]} {now.day}"

    # MediaWiki API çağrısı
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "parse",
        "page": page_title,
        "prop": "wikitext",
        "format": "json"
    }
    headers = {"User-Agent": "WhatHappenedTodayBot/1.0 (contact: youremail@example.com)"}
    resp = requests.get(url, params=params, headers=headers, timeout=20)
    data = resp.json()

    if "error" in data:
        return ["No notable events found."]

    wikitext = data["parse"]["wikitext"]["*"]

    # Satır satır ayır, sadece '*' ile başlayan olayları al
    events = []
    for line in wikitext.splitlines():
        if line.strip().startswith("*"):
            text = line.lstrip("* ").strip()

            # Basit wiki temizliği
            text = re.sub(r"\{\{[^{}]*\}\}", "", text)  # {{...}} şablonları
            text = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", text)  # [[Target|Label]]
            text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)            # [[Target]]
            text = re.sub(r"<ref[^>]*>.*?</ref>", "", text)            # <ref>...</ref>
            text = re.sub(r"<ref[^>]*/>", "", text)                    # <ref .../>
            text = re.sub(r"</?[^>]+>", "", text)                      # <tag>
            text = re.sub(r"\s+", " ", text).strip()

            if text:
                events.append(text)

    return events if events else ["No notable events found."]


# Örnek kullanım:
if __name__ == "__main__":
    all_events = get_todays_events()
    for e in all_events:
        print("-", e)
