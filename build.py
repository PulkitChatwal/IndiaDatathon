#!/usr/bin/env python3
"""Build site/index.html from content/event.json and src/index.template.html.

Usage:  python3 build.py          rebuild the page
        python3 build.py --og     also rebuild the share image (needs Google Chrome)

Only the Python standard library is used. Everything a visitor sees that can
change (dates, registration state, agenda, faculty, FAQs, sponsors, contacts,
form questions) lives in content/event.json. Section prose lives in
src/index.template.html.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
ART = SITE / "assets" / "artwork"


def e(value) -> str:
    return escape(str(value), quote=True)


# --------------------------------------------------------------------------
# Icons (24 x 24, stroke only)
# --------------------------------------------------------------------------
ICONS = {
    "calendar": '<rect x="3" y="4.5" width="18" height="16" rx="2"/><path d="M3 9.5h18M8 2.5v4M16 2.5v4"/>',
    "pin": '<path d="M12 21s-7-6.1-7-11.5a7 7 0 0 1 14 0C19 14.9 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6M16 4.6a3.5 3.5 0 0 1 0 6.8M18 14.3c2.2 .7 3.5 2.6 3.5 5.7"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    "laptop": '<rect x="4" y="5" width="16" height="11" rx="1.5"/><path d="M2 19.5h20"/>',
    "meal": '<path d="M7 3v18M4 3v5a3 3 0 0 0 6 0V3M17 21v-8M17 13c-2 0-3-2.2-3-5s1.2-5 3-5z"/>',
    "suitcase": '<rect x="3.5" y="7.5" width="17" height="12" rx="2"/><path d="M9 7.5v-2A1.5 1.5 0 0 1 10.5 4h3A1.5 1.5 0 0 1 15 5.5v2M3.5 13h17"/>',
    "pulse": '<rect x="3" y="3" width="18" height="18" rx="4"/><path d="M6.5 12h3l1.5-3.5 2.5 7 1.5-3.5h2.5"/>',
    "code": '<path d="M8.5 7.5 4 12l4.5 4.5M15.5 7.5 20 12l-4.5 4.5M13.5 5l-3 14"/>',
    "arrow-right": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "arrow-down": '<path d="M12 5v14M6 13l6 6 6-6"/>',
    "arrow-up": '<path d="M12 19V5M6 11l6-6 6 6"/>',
    "arrow-left": '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    "external": '<path d="M8 16 17 7M9 7h8v8"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    "lock": '<rect x="5" y="10.5" width="14" height="10" rx="2"/><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3.5 7.5 8.5 6 8.5-6"/>',
    "present": '<path d="M3 4.5h18M5 4.5V15h14V4.5M12 15v3.5M8.5 20.5l3.5-2 3.5 2"/>',
    "award": '<circle cx="12" cy="9" r="5.5"/><path d="M8.5 13.5 7 21l5-2.5 5 2.5-1.5-7.5"/>',
    "database": '<ellipse cx="12" cy="6" rx="7.5" ry="3"/><path d="M4.5 6v6c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3V6M4.5 12v6c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3v-6"/>',
    "route": '<circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="6" r="2.5"/><path d="M8.5 18H14a3.5 3.5 0 0 0 0-7h-4a3.5 3.5 0 0 1 0-7h5.5"/>',
    "sparkle": '<path d="m12 3.5 1.8 4.7 4.7 1.8-4.7 1.8L12 16.5l-1.8-4.7L5.5 10l4.7-1.8zM18.5 15.5v4M16.5 17.5h4"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
}


def icon(name: str) -> str:
    body = ICONS[name]
    return (
        '<svg class="icon" viewBox="0 0 24 24" width="24" height="24" fill="none" '
        'stroke="currentColor" stroke-width="1.75" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true" focusable="false">{body}</svg>'
    )


# --------------------------------------------------------------------------
# Artwork
# --------------------------------------------------------------------------
def inline_svg(filename: str, css_class: str) -> str:
    """Inline an artwork file so its colours follow the page stylesheet."""
    svg = (ART / filename).read_text(encoding="utf-8")
    fills = svg.count('class="id-architecture-fill"')
    svg = re.sub(r"<style>.*?</style>", "", svg, flags=re.S)
    svg = re.sub(r"<title>.*?</title>", "", svg, flags=re.S)
    svg = svg.replace('class="id-architecture-fill"', 'class="art-fill"')
    svg = svg.replace('class="id-banner-sun"', 'class="art-sun"')
    assert svg.count('class="art-fill"') == fills
    svg = re.sub(
        r"<svg\b[^>]*?(viewBox=\"[^\"]+\")[^>]*>",
        lambda m: f'<svg class="{css_class}" {m.group(1)} preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false">',
        svg,
        count=1,
    )
    return re.sub(r"\n\s*", "", svg).strip()


# --------------------------------------------------------------------------
# Blocks
# --------------------------------------------------------------------------
def build_blocks(c: dict) -> dict:
    ev, reg, sign, site, contacts = c["event"], c["registration"], c["signup"], c["site"], c["contacts"]
    state = reg["state"]
    signup_on = sign["mode"] in ("demo", "live")
    warnings: list[str] = []
    b: dict[str, str] = {}

    if state not in ("upcoming", "open", "waitlist", "closed"):
        sys.exit(f"registration.state must be upcoming, open, waitlist or closed (got {state!r})")
    if sign["mode"] not in ("off", "demo", "live"):
        sys.exit(f"signup.mode must be off, demo or live (got {sign['mode']!r})")
    if sign["mode"] == "live" and not sign["endpoint"]:
        sys.exit("signup.mode is 'live' but signup.endpoint is empty. Emails would be lost.")
    if sign["mode"] == "live" and not sign["privacyUrl"]:
        warnings.append("signup is live without a privacyUrl. The brief requires an approved privacy notice link.")
    if sign["mode"] == "demo" and not site["preview"]:
        sys.exit("signup.mode is 'demo' on a non-preview build. A public form that discards emails is not allowed; use 'off' or 'live'.")
    if sign["mode"] == "demo":
        warnings.append("signup.mode is 'demo': the email form saves nothing. Set it to 'live' (with an endpoint) or 'off' before launch.")
    form_live = state in ("open", "waitlist") and bool(reg["formEndpoint"]) and not reg["formUrl"]
    form_external = state in ("open", "waitlist") and bool(reg["formUrl"])
    if reg["formUrl"] and not reg["formUrl"].startswith("https://"):
        sys.exit("registration.formUrl must be a full https:// link.")
    if reg["formUrl"] and reg.get("formEmbed") and not re.match(r"https://docs\.google\.com/forms/d/e/[A-Za-z0-9_-]+/viewform", reg["formUrl"]):
        warnings.append("registration.formUrl is not a docs.google.com/forms/d/e/…/viewform link, so the form cannot be shown inside the page; a button is used instead.")
    if state in ("open", "waitlist") and not (form_live or form_external):
        sys.exit("registration.state is open/waitlist but neither formUrl nor formEndpoint is set.")
    if site["preview"]:
        warnings.append("site.preview is true: the page shows the 'Design preview' bar and is hidden from search engines.")

    # ---- head ------------------------------------------------------------
    b["robots"] = '<meta name="robots" content="noindex,nofollow">' if site["preview"] else ""
    if site["url"]:
        base = site["url"].rstrip("/") + "/"
        b["og_urls"] = (
            f'<link rel="canonical" href="{e(base)}">\n  '
            f'<meta property="og:url" content="{e(base)}">\n  '
            f'<meta property="og:image" content="{e(base)}assets/og-image.png">\n  '
            '<meta property="og:image:width" content="1200">\n  '
            '<meta property="og:image:height" content="630">'
        )
    else:
        b["og_urls"] = "<!-- Set site.url in content/event.json to add the canonical link and share image. -->"
        warnings.append("site.url is empty: no canonical link or share image (WhatsApp/LinkedIn preview) is emitted.")

    address = {
        "@type": "PostalAddress",
        "streetAddress": ev["addressLines"][0],
        "addressLocality": "New Delhi",
        "addressRegion": "Delhi",
        "postalCode": "110076",
        "addressCountry": "IN",
    }
    event_ld = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": ev["name"],
        "description": ev["intro"],
        "startDate": ev["startISO"],
        "endDate": ev["endISO"],
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "eventStatus": "https://schema.org/EventScheduled",
        "location": {"@type": "Place", "name": f'{ev["venueRoom"]}, {ev["venueName"]}', "address": address},
    }
    faq_ld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": item.get(f"q_{state}", item["q"]), "acceptedAnswer": {"@type": "Answer", "text": item.get(f"a_{state}", item["a"])}}
            for group in c["faqs"]
            for item in group["items"]
        ],
    }
    b["jsonld"] = "\n  ".join(
        '<script type="application/ld+json">' + json.dumps(x, ensure_ascii=False).replace("</", "<\\/") + "</script>"
        for x in (event_ld, faq_ld)
    )

    # ---- top bar ---------------------------------------------------------
    if site["preview"]:
        detail = (
            "Proposed content · registration is not open · forms save nothing"
            if state == "upcoming"
            else "Proposed content · not yet approved for publication"
        )
        bar = f"<strong>Design preview</strong><span>{detail}</span>"
        cls = "topbar topbar-preview"
    elif state == "upcoming":
        link = ' <a href="#signup">Get notified</a>' if signup_on else ""
        bar, cls = f'<span>{e(reg["opensText"])}</span>{link}', "topbar"
    elif state == "open":
        bar, cls = '<span>Registration is open.</span> <a href="#apply">Go to the participation form</a>', "topbar"
    elif state == "waitlist":
        bar, cls = '<span>Places are full. The waitlist is open.</span> <a href="#apply">Join the waitlist</a>', "topbar"
    else:
        bar, cls = "<span>Registration is closed.</span>", "topbar"
    b["topbar"] = f'<div class="{cls}"><p class="wrap">{bar}</p></div>'

    # ---- navigation ------------------------------------------------------
    soon = '<span class="soon">Soon</span>'
    has_sponsors = bool(c["sponsors"]["items"])
    links = [
        ("about", "About", ""),
        ("program", "Program", ""),
        ("faculty", "Faculty", ""),
        ("participate", "Participate", ""),
        ("apply", "Form", soon if state == "upcoming" else ""),
        ("sponsors", "Sponsors", "" if has_sponsors else soon),
        ("visit", "Venue", ""),
        ("faq", "FAQ", ""),
    ]
    items = "".join(f'<li><a href="#{i}">{label}{extra}</a></li>' for i, label, extra in links)
    if state == "upcoming" and signup_on:
        cta = ("#signup", "Get notified")
    elif state == "open":
        cta = ("#apply", "Apply now")
    elif state == "waitlist":
        cta = ("#apply", "Join the waitlist")
    else:
        cta = ("#program", "See the program")
    b["nav"] = f'<ul>{items}</ul><a class="btn btn-primary btn-small nav-cta" href="{cta[0]}">{cta[1]}</a>'

    # ---- hero ------------------------------------------------------------
    arrow = icon("arrow-right")
    if state == "upcoming" and signup_on:
        actions = (
            f'<a class="btn btn-primary" href="#signup">Email me when registration opens {arrow}</a>'
            f'<a class="btn btn-ghost" href="#program">Explore the program</a>'
        )
        text_link = '<a class="link-arrow" href="#participate">How to participate ' + arrow + "</a>"
    elif state in ("open", "waitlist"):
        label = "Apply now" if state == "open" else "Join the waitlist"
        actions = (
            f'<a class="btn btn-primary" href="#apply">{label} {arrow}</a>'
            f'<a class="btn btn-ghost" href="#program">Explore the program</a>'
        )
        text_link = '<a class="link-arrow" href="#participate">How to participate ' + arrow + "</a>"
    else:
        actions = (
            f'<a class="btn btn-primary" href="#program">Explore the program {arrow}</a>'
            f'<a class="btn btn-ghost" href="#participate">How to participate</a>'
        )
        text_link = ""
    b["hero_actions"] = f'<div class="hero-actions">{actions}</div>' + (f'<p class="hero-more">{text_link}</p>' if text_link else "")

    pill = {
        "upcoming": ("pill-soon", "Registration opens soon"),
        "open": ("pill-open", "Registration open"),
        "waitlist": ("pill-soon", "Waitlist open"),
        "closed": ("pill-closed", "Registration closed"),
    }[state]
    b["status_pill"] = f'<span class="pill {pill[0]}"><span class="pill-dot" aria-hidden="true"></span>{pill[1]}</span>'
    b["countdown"] = (
        '<p class="countdown" data-countdown hidden><strong data-countdown-value></strong> <span data-countdown-label></span></p>'
        if site.get("showCountdown")
        else ""
    )
    b["registration_line"] = {
        "upcoming": "<strong>Opens in the second half of December 2026</strong><span>Join the email list to hear when. Joining does not reserve a place.</span>",
        "open": '<strong>Open now</strong><span><a href="#apply">Go to the participation form</a></span>',
        "waitlist": '<strong>Waitlist open</strong><span><a href="#apply">Join the waitlist</a></span>',
        "closed": "<strong>Closed</strong><span>Thank you for your interest</span>",
    }[state]

    # ---- host logo -------------------------------------------------------
    def host_logo(key: str, css: str) -> str:
        path = ev.get(key) or ""
        if not path:
            return ""
        if not (SITE / path).exists():
            sys.exit(f"Host logo file missing: site/{path}")
        return f'<img class="{css}" src="{e(path)}" alt="{e(ev["host"])}" width="72" height="53" decoding="async">'

    logo = host_logo("hostLogo", "host-logo")
    b["hero_host"] = (
        f'<p class="hero-host hero-host-logo"><span>Hosted by</span>{logo}</p>'
        if logo
        else f'<p class="hero-host">Hosted by <strong>{e(ev["host"])}</strong></p>'
    )
    b["venue_logo"] = host_logo("hostLogo", "host-logo venue-logo")
    b["footer_logo"] = host_logo("hostLogoOnDark", "host-logo footer-logo")

    b["skyline_desktop"] = inline_svg("delhi-skyline-desktop.svg", "skyline-art skyline-desktop")
    b["skyline_mobile"] = inline_svg("delhi-skyline-mobile.svg", "skyline-art skyline-mobile")
    if ev.get("mapEmbedUrl"):
        if not ev["mapEmbedUrl"].startswith("https://www.google.com/maps"):
            sys.exit("event.mapEmbedUrl must be a https://www.google.com/maps address.")
        b["venue_mode"] = "venue-has-map"
        b["venue_art"] = (
            f'<iframe class="map-frame" src="{e(ev["mapEmbedUrl"])}" '
            f'title="Google Map showing {e(ev["venueName"])}, {e(ev["city"])}" '
            'loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe>'
        )
    else:
        b["venue_mode"] = ""
        b["venue_art"] = inline_svg("gate.svg", "venue-gate")

    # ---- how it works ---------------------------------------------------
    steps = {
        "upcoming": [
            ("Get notified", "Registration opens in the second half of December 2026. Joining the email list does not reserve a place."),
            ("Apply individually", "Students and professionals apply on their own, not as a ready-made team."),
        ],
        "open": [
            ("Fill in the participation form", 'Registration is open. Apply individually, not as a ready-made team. <a href="#apply">Go to the form</a>.'),
        ],
        "waitlist": [
            ("Join the waitlist", 'Places are full. Leave your details individually on the <a href="#apply">waitlist form</a>.'),
        ],
        "closed": [
            ("Registration is closed", "Applications were made individually, not as ready-made teams."),
        ],
    }[state] + [
        ("Join a balanced team", "Organizers will form teams with a balanced mix of clinical knowledge and technical skills."),
        ("Build and present in Delhi", "Two days in person, ending with a five-minute team presentation."),
    ]
    b["how_steps"] = '<ol class="steps">' + "".join(
        f'<li><span class="step-num" aria-hidden="true">{n}</span><div><h4>{title}</h4><p>{text}</p></div></li>'
        for n, (title, text) in enumerate(steps, 1)
    ) + "</ol>"

    # ---- stats -----------------------------------------------------------
    b["stats"] = "".join(
        f'<li><strong>{e(s["value"])}</strong><span class="stat-label">{e(s["label"])}</span>'
        f'<span class="stat-detail">{e(s["detail"])}</span></li>'
        for s in c["stats"]
    )

    # ---- program ---------------------------------------------------------
    tabs, panels = [], []
    for n, day in enumerate(c["schedule"]):
        selected = n == 0
        tabs.append(
            f'<button class="day-tab" type="button" role="tab" id="day{day["id"]}-tab" '
            f'aria-controls="day{day["id"]}-panel" aria-selected="{"true" if selected else "false"}" '
            f'tabindex="{"0" if selected else "-1"}">'
            f'<span class="day-tab-label">{e(day["label"])}</span>'
            f'<span class="day-tab-date">{e(day["weekday"])}, {e(day["date"])}</span></button>'
        )
        rows = []
        for slot in day["slots"]:
            tag = f'<span class="slot-tag">{e(slot["tag"])}</span>' if slot.get("tag") else ""
            rows.append(
                f'<li class="slot slot-{e(slot["type"])}"><time>{e(slot["time"])}</time>'
                f'<div class="slot-body">{tag}<p>{e(slot["title"])}</p></div></li>'
            )
        panels.append(
            f'<div class="day-panel" role="tabpanel" id="day{day["id"]}-panel" aria-labelledby="day{day["id"]}-tab" tabindex="0" data-day-panel>'
            f'<div class="day-intro"><div><h3>{e(day["theme"])}</h3><p>{e(day["summary"])}</p></div>'
            f'<p class="day-date">{e(day["label"])} · {e(day["weekday"])}, {e(day["date"])} 2027</p></div>'
            f'<ol class="timeline">{"".join(rows)}</ol></div>'
        )
    b["day_tabs"] = "".join(tabs)
    b["day_panels"] = "\n          ".join(panels)

    # ---- faculty ---------------------------------------------------------
    cards = []
    for person in c["faculty"]:
        name = e(person["name"])
        link = person.get("linkedin") or ""
        if link and not re.fullmatch(r"https://www\.linkedin\.com/in/[A-Za-z0-9-]+/?", link):
            sys.exit(f"Faculty LinkedIn link for {person['name']} is not a linkedin.com/in/ address: {link}")
        photo = ""
        if person.get("portrait"):
            if not (SITE / person["portrait"]).exists():
                sys.exit(f"Portrait file missing for {person['name']}: site/{person['portrait']}")
            photo = (
                f'<img class="person-photo" src="{e(person["portrait"])}" alt="Illustrated portrait of {name}" '
                'width="320" height="320" loading="lazy" decoding="async">'
            )
        profile = person.get("profile") or ""
        if profile and not profile.startswith("https://"):
            sys.exit(f"Faculty profile link for {person['name']} must start with https://")
        if not photo:
            initials = "".join(part[0] for part in person["name"].split()[:2]).upper()
            photo = f'<span class="person-initials" aria-hidden="true">{e(initials)}</span>'
        if link or profile:
            where = "on LinkedIn" if link else "profile page"
            label = (
                f'<a href="{e(link or profile)}" target="_blank" rel="noopener noreferrer" '
                f'aria-label="{name} {where} (opens in a new tab)">{name}{icon("external")}</a>'
            )
        else:
            label = name
        cards.append(
            f'<article class="person"><div class="person-top">{photo}'
            f'<div class="person-id"><h3 class="person-name">{label}</h3><p class="person-org">{e(person["affiliation"])}</p></div></div>'
            f'<details class="person-bio"><summary aria-label="Read biography of {name}"><span>Read bio</span>'
            f'<span class="toggle" aria-hidden="true"></span></summary><p>{e(person["bio"])}</p></details></article>'
        )
    b["faculty"] = "\n        ".join(cards)

    # ---- participation form ---------------------------------------------
    b.update(build_apply(c, state, signup_on, form_live, form_external))

    # ---- sponsors --------------------------------------------------------
    sp = c["sponsors"]
    if contacts["sponsorshipEmail"]:
        who = e(contacts["sponsorshipName"]) or "the organizing team"
        contact_html = (
            f'<h3>Interested in supporting {e(ev["name"])}?</h3>'
            '<p>The event brings together about 80 students and professionals from medical and data science/engineering '
            'backgrounds for two days of hands-on work on clinical questions.</p>'
            f'<p>Contact {who} for sponsorship.</p>'
            f'<a class="btn btn-primary" href="mailto:{e(contacts["sponsorshipEmail"])}?subject=India%20Datathon%20sponsorship">'
            f'Email about sponsorship {icon("mail")}</a>'
        )
    else:
        contact_html = (
            f'<h3>Interested in supporting {e(ev["name"])}?</h3>'
            '<p>The event brings together about 80 students and professionals from medical and data science/engineering '
            'backgrounds for two days of hands-on work on clinical questions.</p>'
            f'<p class="soft-note">{icon("mail")}<span>Sponsorship contact details will be added once confirmed.</span></p>'
        )
    host_tile = (
        f'<li class="logo-tile logo-tile-host{" logo-tile-host-light" if logo else ""}"><span class="tile-label">Host</span>'
        + (host_logo("hostLogo", "host-logo tile-logo") or f'<span class="tile-name">{e(ev["host"])}</span>')
        + "</li>"
    )
    if has_sponsors:
        groups: dict[str, list] = {}
        for item in sp["items"]:
            groups.setdefault(item.get("group", "Sponsors"), []).append(item)
        tiles = []
        for group, members in groups.items():
            for m in members:
                inner = (
                    f'<img src="{e(m["logo"])}" alt="{e(m["name"])}" loading="lazy">' if m.get("logo") else f'<span class="tile-name">{e(m["name"])}</span>'
                )
                if m.get("url"):
                    inner = f'<a href="{e(m["url"])}" target="_blank" rel="noopener">{inner}</a>'
                tiles.append(f'<li class="logo-tile"><span class="tile-label">{e(group)}</span>{inner}</li>')
        b["sponsors_lede"] = f"With thanks to the organizations supporting {e(ev['name'])}."
        b["sponsors_badge"] = ""
        grid = host_tile + "".join(tiles)
    else:
        b["sponsors_lede"] = "Sponsor and partner announcements are on the way."
        b["sponsors_badge"] = '<span class="badge-soon">Coming soon</span>'
        grid = host_tile + "".join(
            '<li class="logo-tile logo-tile-empty" aria-hidden="true"><span class="tile-label">Sponsor</span>'
            '<span class="tile-soon">Announcing soon</span></li>'
            for _ in range(sp.get("placeholderSlots", 6) - 1)
        )
    b["sponsors_body"] = (
        '<div class="sponsor-grid reveal">'
        f'<div class="sponsor-cta">{contact_html}</div>'
        f'<ul class="logo-wall">{grid}</ul>'
        "</div>"
    )

    # ---- venue -----------------------------------------------------------
    b["address"] = "<br>".join(e(line) for line in ev["addressLines"])

    # ---- FAQ -------------------------------------------------------------
    def faq_text(item: dict, key: str) -> str:
        return item.get(f"{key}_{state}", item[key])

    cols = []
    for group in c["faqs"]:
        qs = "".join(
            f'<details class="faq"><summary><span>{e(faq_text(i, "q"))}</span><span class="toggle" aria-hidden="true"></span></summary>'
            f'<p>{e(faq_text(i, "a"))}</p></details>'
            for i in group["items"]
        )
        cols.append(f'<div class="faq-group"><h3>{e(group["group"])}</h3>{qs}</div>')
    b["faqs"] = "\n        ".join(cols)
    b["faq_contact"] = (
        f'<p class="faq-contact">Still have a question? <a href="mailto:{e(contacts["generalEmail"])}">Email the organizing team</a>.</p>'
        if contacts["generalEmail"]
        else ""
    )

    # ---- signup ----------------------------------------------------------
    b["signup"] = build_signup(c, state, signup_on)

    # ---- footer ----------------------------------------------------------
    rows = []
    if contacts["generalEmail"]:
        rows.append(f'<li><a href="mailto:{e(contacts["generalEmail"])}">Contact</a></li>')
    if contacts["sponsorshipEmail"]:
        rows.append(f'<li><a href="mailto:{e(contacts["sponsorshipEmail"])}">Sponsorship</a></li>')
    if sign["privacyUrl"]:
        rows.append(f'<li><a href="{e(sign["privacyUrl"])}">Privacy notice</a></li>')
    if not rows:
        rows.append('<li class="footer-muted">Contact details and the privacy notice will be published here once confirmed.</li>')
    b["footer_contact"] = f'<div><h2>Contact</h2><ul>{"".join(rows)}</ul></div>'
    note = "Event details subject to final confirmation."
    b["footer_note"] = ("Design preview · " + note) if site["preview"] else note

    # ---- dedicated form page (site/form.html) ---------------------------------
    google = re.fullmatch(r"(https://docs\.google\.com/forms/d/e/[A-Za-z0-9_-]+/viewform)(?:\?.*)?", reg["formUrl"] or "")
    b["_form_page"] = "yes" if google else ""
    if google:
        b["form_embed_src"] = e(google.group(1)) + "?embedded=true"
        b["form_page_title"], b["form_page_lede"], b["form_page_badge"] = {
            "upcoming": (
                "The form opens soon.",
                e(reg["opensText"]) + " The form below will start accepting answers then.",
                '<span class="badge-soon">Coming soon</span>',
            ),
            "open": (
                "Apply to take part.",
                "Apply individually. Organizers will form teams with a balanced mix of clinical knowledge and technical skills.",
                '<span class="badge-soon badge-open">Open</span>',
            ),
            "waitlist": (
                "Join the waitlist.",
                "Places are full. Leave your details and we will contact you if a place becomes available.",
                '<span class="badge-soon badge-open">Waitlist</span>',
            ),
            "closed": (
                "Registration is closed.",
                "Thank you to everyone who applied. Information for participants will be shared by email.",
                '<span class="badge-soon badge-closed">Closed</span>',
            ),
        }[state]

    b["_warnings"] = "\n".join(warnings)
    return b


def field_html(f: dict) -> str:
    name, label, kind = f["name"], f["label"], f["type"]
    required = f.get("required", False)
    fid = "pf-" + name.replace("_", "-")
    req_mark = '&nbsp;<span class="req" aria-hidden="true">*</span>' if required else ' <span class="opt">(optional)</span>'
    req_attr = " required" if required else ""
    hint = f.get("hint")
    hint_html = f'<span class="hint" id="{fid}-hint">{e(hint)}</span>' if hint else ""
    described = f' aria-describedby="{fid}-hint"' if hint else ""
    auto = f' autocomplete="{e(f["autocomplete"])}"' if f.get("autocomplete") else ""
    wide = " field-wide" if f.get("wide") else ""

    if kind in ("text", "email", "tel"):
        extra = {
            "email": ' inputmode="email" autocapitalize="none" spellcheck="false"',
            "tel": ' inputmode="tel"',
            "text": "",
        }[kind]
        return (
            f'<div class="field{wide}"><label for="{fid}">{e(label)}{req_mark}</label>'
            f'<input id="{fid}" name="{e(name)}" type="{kind}"{extra}{auto}{req_attr}{described}>{hint_html}</div>'
        )
    if kind == "textarea":
        return (
            f'<div class="field{wide}"><label for="{fid}">{e(label)}{req_mark}</label>'
            f'<textarea id="{fid}" name="{e(name)}" rows="4"{req_attr}{described}></textarea>{hint_html}</div>'
        )
    if kind == "select":
        options = '<option value="">Select…</option>' + "".join(f"<option>{e(o)}</option>" for o in f["options"])
        return (
            f'<div class="field{wide}"><label for="{fid}">{e(label)}{req_mark}</label>'
            f'<select id="{fid}" name="{e(name)}"{req_attr}{described}>{options}</select>{hint_html}</div>'
        )
    if kind in ("radio", "checks"):
        input_type = "radio" if kind == "radio" else "checkbox"
        group_req = ' data-require-one="true"' if required and kind == "checks" else ""
        choices = "".join(
            f'<label class="choice"><input type="{input_type}" name="{e(name)}" value="{e(o)}"'
            f'{req_attr if kind == "radio" else ""}><span>{e(o)}</span></label>'
            for o in f["options"]
        )
        return (
            f'<fieldset class="field field-choices{wide}"{group_req}><legend>{e(label)}{req_mark}</legend>'
            f'<div class="choices">{choices}</div>{hint_html}</fieldset>'
        )
    if kind == "confirm":
        return (
            f'<div class="field field-confirm{wide}"><label class="choice choice-confirm">'
            f'<input type="checkbox" name="{e(name)}" value="yes"{req_attr}><span>{e(label)}{req_mark}</span></label></div>'
        )
    sys.exit(f"Unknown form field type: {kind!r} ({name})")


def build_apply(c: dict, state: str, signup_on: bool, form_live: bool, form_external: bool) -> dict:
    reg, sign, form = c["registration"], c["signup"], c["form"]
    out: dict[str, str] = {}
    locked = state == "upcoming"
    total = sum(len(s["fields"]) for s in form["sections"])
    required = sum(1 for s in form["sections"] for f in s["fields"] if f.get("required"))

    if state == "closed":
        out["apply_title"] = "Registration is closed."
        out["apply_lede"] = "Thank you to everyone who applied. Information for participants will be shared by email."
        out["apply_badge"] = '<span class="badge-soon badge-closed">Closed</span>'
        out["apply_body"] = ""
        return out

    if form_external:
        label = "Open the participation form" if state == "open" else "Join the waitlist"
        out["apply_title"] = "Apply to take part." if state == "open" else "Join the waitlist."
        out["apply_lede"] = "Apply individually. Organizers will form teams with a balanced mix of clinical knowledge and technical skills."
        out["apply_badge"] = '<span class="badge-soon badge-open">Open</span>'
        link = (
            f'<a class="btn btn-primary btn-large" href="{e(reg["formUrl"])}" target="_blank" rel="noopener">{label} {icon("external")}'
            '<span class="sr-only"> (opens in a new tab)</span></a>'
        )
        google = re.fullmatch(r"(https://docs\.google\.com/forms/d/e/[A-Za-z0-9_-]+/viewform)(?:\?.*)?", reg["formUrl"])
        if reg.get("formEmbed") and google:
            out["apply_body"] = (
                '<div class="apply-embed reveal">'
                '<div class="apply-embed-bar"><p>Prefer a full page? <a href="form.html">Open the form page</a>, or use the button for a new tab.</p>'
                f'{link}</div>'
                f'<iframe class="form-embed" src="{e(google.group(1))}?embedded=true" title="{e(c["event"]["name"])} participation form" '
                'loading="lazy">Loading the form…</iframe></div>'
            )
        else:
            out["apply_body"] = f'<div class="apply-open reveal"><p>The participation form opens in a new tab.</p>{link}</div>'
        return out

    sections = []
    for n, section in enumerate(form["sections"], 1):
        fields = "".join(field_html(f) for f in section["fields"])
        sections.append(
            f'<section class="form-section"><h3><span class="form-step" aria-hidden="true">{n}</span>{e(section["title"])}</h3>'
            f'<div class="field-grid">{fields}</div></section>'
        )
    privacy = (
        f' <a href="{e(sign["privacyUrl"])}" target="_blank" rel="noopener">Privacy notice</a>'
        if sign["privacyUrl"]
        else ' <span class="hint-inline">The privacy notice will be linked here before the form opens.</span>'
    )
    consent = (
        '<div class="field field-confirm field-wide"><label class="choice choice-confirm">'
        f'<input type="checkbox" name="consent" value="yes" required><span>{e(form["consent"])}&nbsp;'
        f'<span class="req" aria-hidden="true">*</span>{privacy}</span></label></div>'
    )

    if locked:
        out["apply_title"] = "The form opens soon."
        out["apply_lede"] = (
            "Apply individually when registration opens. Below is a preview of what the form will ask, "
            "so you can have your details ready."
        )
        out["apply_badge"] = '<span class="badge-soon">Coming soon</span>'
        notify = (
            f'<a class="btn btn-primary" href="#signup">Email me when it opens {icon("arrow-right")}</a>'
            if signup_on
            else ""
        )
        if re.match(r"https://docs\.google\.com/forms/d/e/[A-Za-z0-9_-]+/viewform", reg["formUrl"] or ""):
            notify += f'<a class="btn btn-ghost" href="form.html">Go to the form page {icon("arrow-right")}</a>'  
        aside = (
            '<aside class="apply-aside reveal">'
            f'<div class="lock-card">{icon("lock")}<h3>Not open yet</h3>'
            f'<p>{e(reg["opensText"])} The form cannot be submitted until then.</p>{notify}</div>'
            '<ul class="tick-list">'
            f'<li>{icon("check")}<span>Apply individually. Organizers form balanced teams.</span></li>'
            f'<li>{icon("check")}<span>Medical participants do not need to code.</span></li>'
            f'<li>{icon("check")}<span>Technical participants should know Python (preferred), R or SQL.</span></li>'
            f'<li>{icon("check")}<span>The fee amount will be announced.</span></li>'
            "</ul>"
            f'<p class="fine">{total} questions, {required} required. Questions may change before the form opens.</p>'
            "</aside>"
        )
        banner = (
            f'<p class="form-banner" id="apply-locked-note">{icon("lock")}<span><strong>Preview only.</strong> '
            "This form is not accepting responses yet.</span></p>"
        )
        form_attrs = 'class="p-form is-locked reveal" aria-describedby="apply-locked-note" data-participation-form="locked"'
        fs_open, submit = "<fieldset disabled>", f'<button class="btn btn-primary btn-large" type="submit" disabled>{icon("lock")} Opens soon</button>'
    else:
        out["apply_title"] = "Apply to take part." if state == "open" else "Join the waitlist."
        out["apply_lede"] = "Apply individually. Organizers will form teams with a balanced mix of clinical knowledge and technical skills."
        out["apply_badge"] = '<span class="badge-soon badge-open">Open</span>'
        aside = (
            '<aside class="apply-aside reveal"><ul class="tick-list">'
            f'<li>{icon("check")}<span>Apply individually. Organizers form balanced teams.</span></li>'
            f'<li>{icon("check")}<span>Medical participants do not need to code.</span></li>'
            f'<li>{icon("check")}<span>Technical participants should know Python (preferred), R or SQL.</span></li>'
            "</ul></aside>"
        )
        banner = ""
        form_attrs = (
            f'class="p-form reveal" action="{e(reg["formEndpoint"])}" method="post" novalidate data-participation-form="live"'
        )
        label = "Submit" if state == "open" else "Join the waitlist"
        fs_open, submit = "<fieldset>", f'<button class="btn btn-primary btn-large" type="submit">{label} {icon("arrow-right")}</button>'

    out["apply_body"] = (
        '<div class="apply-grid">'
        f"{aside}"
        f"<form {form_attrs}>{banner}{fs_open}"
        '<legend class="sr-only">Participation form</legend>'
        '<p class="req-note"><span class="req" aria-hidden="true">*</span> Required</p>'
        f'{"".join(sections)}'
        f'<section class="form-section form-section-last"><div class="field-grid">{consent}</div>'
        f'<div class="form-actions">{submit}<p class="form-result" role="status" aria-live="polite" data-form-result></p></div></section>'
        "</fieldset></form></div>"
    )
    return out


def build_signup(c: dict, state: str, signup_on: bool) -> str:
    reg, sign = c["registration"], c["signup"]
    if state != "upcoming":
        return ""
    head = (
        '<p class="kicker">Stay in the loop</p>'
        '<h2 id="signup-title">Be there when it begins.</h2>'
        f'<p class="lede">{e(reg["opensText"])}'
    )
    if not signup_on:
        return (
            '<section class="section section-sand signup" id="signup" aria-labelledby="signup-title"><div class="wrap signup-grid">'
            f'<div>{head} Details will be posted on this page.</p></div></div></section>'
        )
    privacy = (
        f'<a href="{e(sign["privacyUrl"])}" target="_blank" rel="noopener">Privacy notice</a>'
        if sign["privacyUrl"]
        else ""
    )
    demo = sign["mode"] == "demo"
    note = (
        '<p class="form-note" id="signup-note"><strong>Preview only:</strong> this form demonstrates the experience. '
        "No email is saved or sent. The live signup will include an approved privacy notice.</p>"
        if demo
        else f'<p class="form-note" id="signup-note">We will only email you about registration for India Datathon. {privacy}</p>'
    )
    action = "" if demo else f' action="{e(sign["endpoint"])}" method="post"'
    return (
        '<section class="section section-sand signup" id="signup" aria-labelledby="signup-title"><div class="wrap signup-grid">'
        f'<div>{head} Leave your email to receive the registration announcement.</p>'
        '<p class="signup-caveat">Joining this list does not reserve a place or count as registration.</p></div>'
        f'<form class="signup-form" novalidate{action} data-signup-form data-success="{e(sign["successState"])}">'
        '<label for="signup-email">Email address</label>'
        '<div class="input-row">'
        '<input id="signup-email" name="email" type="email" inputmode="email" autocapitalize="none" autocorrect="off" spellcheck="false" '
        'enterkeyhint="send" autocomplete="email" placeholder="you@example.com" required aria-describedby="signup-note signup-result">'
        f'<button class="btn btn-primary" type="submit">Notify me {icon("arrow-right")}</button>'
        "</div>"
        '<label class="choice choice-confirm"><input type="checkbox" name="consent" value="yes" id="signup-consent" required>'
        "<span>Email me about registration for India Datathon.</span></label>"
        f"{note}"
        '<p class="form-result" id="signup-result" role="status" aria-live="polite" data-form-result></p>'
        "</form></div></section>"
    )


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------
def lookup(ctx: dict, path: str):
    value = ctx
    for part in path.split("."):
        value = value[part]
    return value


def main() -> None:
    content = json.loads((ROOT / "content" / "event.json").read_text(encoding="utf-8"))
    template = (ROOT / "src" / "index.template.html").read_text(encoding="utf-8")
    ev, reg = content["event"], content["registration"]

    assets = b"".join((SITE / "assets" / p).read_bytes() for p in ("css/site.css", "js/app.js") if (SITE / "assets" / p).exists())
    status = {
        "upcoming": reg["opensText"],
        "open": "Registration is open.",
        "waitlist": "The waitlist is open.",
        "closed": "Registration is closed.",
    }[reg["state"]]
    ctx = dict(content)
    ctx["build"] = {"version": hashlib.sha1(assets).hexdigest()[:8]}
    ctx["meta"] = {
        "description": f'{ev["name"]}, {ev["dates"]}, {ev["venueName"]}, {ev["city"]}. '
        f"Two days where clinicians and data scientists work together on clinical questions. {status}"
    }

    blocks = build_blocks(content)
    warnings = blocks.pop("_warnings")

    def replace(match: re.Match) -> str:
        token = match.group(1).strip()
        if token.startswith(">"):
            return blocks[token[1:].strip()]
        if token.startswith("icon:"):
            return icon(token[5:])
        return e(lookup(ctx, token))

    html = re.sub(r"\{\{(.+?)\}\}", replace, template)
    form_page = ""
    if blocks.pop("_form_page"):
        form_page = re.sub(r"\{\{(.+?)\}\}", replace, (ROOT / "src" / "form.template.html").read_text(encoding="utf-8"))

    # Safety checks from the organizer's brief.
    visible = re.sub(r"<script\b.*?</script>", "", html + form_page, flags=re.S)
    for banned in ("xxx", "TBD", "lorem", "{{", "}}"):
        if banned.lower() in visible.lower():
            sys.exit(f"Build stopped: placeholder text {banned!r} would be visible on the page.")
    ids = re.findall(r'\sid="([^"]+)"', html)
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        sys.exit(f"Build stopped: duplicate ids {dupes}")
    for target in set(re.findall(r'href="#([^"]+)"', html)):
        if target not in ids:
            sys.exit(f"Build stopped: link to #{target} has no matching section.")

    (SITE / "index.html").write_text(html, encoding="utf-8")
    if form_page:
        (SITE / "form.html").write_text(form_page, encoding="utf-8")
    elif (SITE / "form.html").exists():
        (SITE / "form.html").unlink()
    if 'href="form.html"' in html and not form_page:
        sys.exit("Build stopped: the page links to form.html but no Google Form link is set.")
    build_google_form_script(content)
    print(f"Built site/index.html ({len(html.encode()) // 1024} KB) · registration: {reg['state']} · signup: {content['signup']['mode']}"
          + (" · site/form.html" if form_page else ""))
    if warnings:
        print("\nBefore launch:")
        for line in warnings.splitlines():
            print("  - " + line)


def build_google_form_script(content: dict) -> None:
    """Write google-form/create-form.gs: a Google Apps Script that creates the same questions as a Google Form."""
    ev, form, reg = content["event"], content["form"], content["registration"]
    js = lambda value: json.dumps(value, ensure_ascii=False)
    lines = []
    for section in form["sections"]:
        lines.append(f"  form.addSectionHeaderItem().setTitle({js(section['title'])});")
        for f in section["fields"]:
            req = "true" if f.get("required") else "false"
            title, kind = js(f["label"]), f["type"]
            hint = f".setHelpText({js(f['hint'])})" if f.get("hint") else ""
            if kind in ("text", "tel"):
                lines.append(f"  form.addTextItem().setTitle({title}){hint}.setRequired({req});")
            elif kind == "email":
                lines.append(f"  form.addTextItem().setTitle({title}){hint}.setRequired({req}).setValidation(emailRule);")
            elif kind == "textarea":
                lines.append(f"  form.addParagraphTextItem().setTitle({title}){hint}.setRequired({req});")
            elif kind == "select":
                lines.append(f"  form.addListItem().setTitle({title}){hint}.setChoiceValues({js(f['options'])}).setRequired({req});")
            elif kind == "radio":
                lines.append(f"  form.addMultipleChoiceItem().setTitle({title}){hint}.setChoiceValues({js(f['options'])}).setRequired({req});")
            elif kind == "checks":
                lines.append(f"  form.addCheckboxItem().setTitle({title}){hint}.setChoiceValues({js(f['options'])}).setRequired({req});")
            elif kind == "confirm":
                lines.append(f"  form.addCheckboxItem().setTitle({title}).setChoiceValues(['Yes']).setRequired({req});")
    lines.append("  form.addSectionHeaderItem().setTitle('Consent');")
    lines.append(f"  form.addCheckboxItem().setTitle({js(form['consent'])}).setChoiceValues(['I agree']).setRequired(true);")
    description = (
        f"{ev['name']}, {ev['dates']}, {ev['venueRoom']}, {ev['venueName']}, {ev['city']}. "
        "Apply individually. Organizers will form teams with a balanced mix of clinical knowledge and technical skills."
    )
    closed_message = js(f"{reg['opensText']} This form is not accepting responses yet.")
    script = f"""/**
 * {ev['name']}: participation form (Google Form).
 * Generated by build.py from content/event.json. Do not edit by hand; edit the JSON and rebuild.
 *
 * ONE-TIME SETUP (about two minutes, in the Google account that should own the responses):
 *   1. Open https://script.google.com and choose "New project".
 *   2. Delete the sample code, paste this whole file, and press Save.
 *   3. In the function menu choose createForm, press Run, and approve the Google permission prompt.
 *   4. Open "Execution log". It prints three links: the form to share, the form editor,
 *      and the Google Sheet where answers will arrive.
 *   5. Paste the "Share this link" address into registration.formUrl in content/event.json
 *      and run: python3 build.py
 *
 * The form is created CLOSED, so nobody can answer before registration opens.
 *   - On opening day: choose openRegistration and press Run, then set registration.state
 *     to "open" in content/event.json and rebuild the site.
 *   - To stop taking answers: choose closeRegistration and press Run.
 *
 * createForm refuses to run twice, so you cannot end up with two forms by accident.
 * (Deleted the form and want a fresh one? Run forgetForm first.)
 */
var FORM_TITLE = {js(ev['name'] + ': participation form')};

function createForm() {{
  var props = PropertiesService.getScriptProperties();
  if (props.getProperty('FORM_ID')) {{
    Logger.log('The form already exists. Edit it here: ' + FormApp.openById(props.getProperty('FORM_ID')).getEditUrl());
    return;
  }}
  var form = FormApp.create(FORM_TITLE);
  props.setProperty('FORM_ID', form.getId());  // remembered straight away, so a later error can never lead to a second form
  form.setDescription({js(description)});
  form.setConfirmationMessage('Your form has been received. This does not confirm a place. We will email you about next steps.');
  form.setAllowResponseEdits(false);
  form.setShowLinkToRespondAgain(false);
  form.setProgressBar(false);
  var emailRule = FormApp.createTextValidation().requireTextIsEmail().setHelpText('Enter a valid email address.').build();

{chr(10).join(lines)}

  // The steps below are extras. Each one is allowed to fail without stopping the script.
  var sheetUrl = 'not linked (in the form editor open Responses > Link to Sheets)';
  try {{
    var sheet = SpreadsheetApp.create(FORM_TITLE + ' (responses)');
    form.setDestination(FormApp.DestinationType.SPREADSHEET, sheet.getId());
    sheetUrl = sheet.getUrl();
  }} catch (err) {{ Logger.log('Note: could not link a Google Sheet: ' + err.message); }}

  var closed = closeForm_(form, {closed_message});

  Logger.log('Share this link:   ' + form.getPublishedUrl());
  Logger.log('Edit the form at:  ' + form.getEditUrl());
  Logger.log('Answers arrive in: ' + sheetUrl);
  Logger.log(closed
    ? 'The form is CLOSED for now. Run openRegistration on opening day.'
    : 'WARNING: the form could NOT be closed automatically. In the form editor open the Responses tab and switch off "Accepting responses".');
}}

/** Stops the form taking answers. Returns true when it is confirmed closed. */
function closeForm_(form, message) {{
  try {{ form.setAcceptingResponses(false); }} catch (err) {{ Logger.log('Note: setAcceptingResponses failed: ' + err.message); }}
  var closed = false;
  try {{ closed = !form.isAcceptingResponses(); }} catch (err) {{ Logger.log('Note: could not read the form state: ' + err.message); }}
  if (closed) {{
    try {{ form.setCustomClosedFormMessage(message); }} catch (err) {{ Logger.log('Note: the custom "closed" message was not set (Google shows its standard one): ' + err.message); }}
  }}
  return closed;
}}

function openRegistration() {{
  var form = FormApp.openById(PropertiesService.getScriptProperties().getProperty('FORM_ID'));
  form.setAcceptingResponses(true);
  Logger.log(form.isAcceptingResponses() ? 'Registration is OPEN: ' + form.getPublishedUrl() : 'WARNING: the form is still closed. Switch on "Accepting responses" in the form editor.');
}}

function closeRegistration() {{
  var form = FormApp.openById(PropertiesService.getScriptProperties().getProperty('FORM_ID'));
  var closed = closeForm_(form, 'Registration for {ev['name']} is closed. Thank you for your interest.');
  Logger.log(closed ? 'Registration is CLOSED.' : 'WARNING: could not close the form. Switch off "Accepting responses" in the form editor.');
}}

/** Only if you deleted the form and want a fresh one: run this, then run createForm again. */
function forgetForm() {{
  PropertiesService.getScriptProperties().deleteProperty('FORM_ID');
  Logger.log('Forgotten. createForm will now make a new form.');
}}
"""
    target = ROOT / "google-form" / "create-form.gs"
    target.parent.mkdir(exist_ok=True)
    target.write_text(script, encoding="utf-8")


def build_share_image() -> None:
    """Render site/assets/og-image.png (1200 x 630) with headless Chrome.  Run: python3 build.py --og"""
    import subprocess
    import tempfile

    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if not chrome.exists():
        sys.exit("Google Chrome was not found; the share image was not rebuilt.")
    page = (ROOT / "src" / "og-image.html").read_text(encoding="utf-8")
    page = page.replace("__SKYLINE__", inline_svg("delhi-skyline-desktop.svg", "sky-art"))
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "og.html"
        source.write_text(page, encoding="utf-8")
        target = SITE / "assets" / "og-image.png"
        subprocess.run(
            [str(chrome), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=6000",
             "--window-size=1200,630", f"--screenshot={target}", source.as_uri()],
            capture_output=True, timeout=120, check=False,
        )
    print("Built site/assets/og-image.png" if target.exists() else "The share image could not be built.")


if __name__ == "__main__":
    main()
    if "--og" in sys.argv:
        build_share_image()
