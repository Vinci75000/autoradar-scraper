"""Generic JSON-LD-first extractor — config-driven, multi-dealer.

Doctrine: ajout dealer = 1 ligne SQL (extractor='generic_jsonld' + listings_url
+ selectors JSONB). Couvre la longue traine.

Decouverte: config.selectors['detail_url_regex'] (override) OU heuristique
(segments URL voiture multi-langue + slug terminal) ; pagination via
selectors['page_param'] + ['max_pages'] (stop si plus de nouvelles fiches).

Extraction par fiche, en cascade:
  1. schema.org JSON-LD (Car/Vehicle/Product/@graph) — brand/model/year/km/
     fuel/transmission/price/photos/description. Le coeur.
  2. fallback marque via BRAND_REGISTRY sur h1/og:title/title (sites sans schema).
  3. fallback meta description (prix).
  4. fallback HTML labels multilingues (annee, km, boite, carburant, prix).
  5. fallback selecteurs CSS (selectors: price/title/year/km).
  6. ci/co/cu depuis config. Sanity gate: marque requise.

Durcissement qualite (hardening):
  - annee: si JSON-LD donne l'annee courante (date de publication) ou rien,
    relire "Bj. YYYY"/"Baujahr" depuis le titre.
  - modele: couper suffixe " - {dealer}" / " - {site}" / apres " | ".
  - SOLD: drop si vendu (titre, slug, url).
  - slug bruit: a la decouverte, exclure les pages de site (news, kontakt,
    ueber-uns, fahrzeuge nu, etc.).
  - sanity: drop si modele vide / == marque / == nom du dealer.
"""
from __future__ import annotations

import json
import logging
import re
import time
import unicodedata
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .base import CarListing, ExtractionResult, Extractor, SourceConfig
from .registry import register

logger = logging.getLogger(__name__)

_DETAIL_HINT_RE = re.compile(
    r"/(?:cars?|vehicles?|vehicule|voiture|voitures|auto|autos|fahrzeug|fahrzeuge|"
    r"stock|stocklist|inventory|occasion|occasions|veicoli|coche|coches|samochod|"
    r"classic|oldtimer|youngtimer|for-sale|te-koop|a-vendre|sprzedaz|"
    r"produit|produkt|prodotto|producto|product|listing|listings|annonce|annonces)/",
    re.IGNORECASE,
)
_DETAIL_TAIL_RE = re.compile(r"/[a-z0-9][a-z0-9\-]{4,}/?$", re.IGNORECASE)

_JSONLD_VEHICLE_TYPES = {"car", "vehicle", "product", "individualproduct", "motorcycle"}

_FUEL_MAP = [
    ("benzin", "Essence"), ("petrol", "Essence"), ("gasoline", "Essence"),
    ("essence", "Essence"), ("benzina", "Essence"), ("benzine", "Essence"),
    ("diesel", "Diesel"), ("gasoil", "Diesel"),
    ("elektro", "Électrique"), ("electric", "Électrique"),
    ("hybrid", "Hybride"), ("lpg", "GPL"), ("gpl", "GPL"),
]

_BRAND_CANONICAL = {
    "mercedes-benz": "Mercedes-Benz", "mercedes benz": "Mercedes-Benz", "mercedes": "Mercedes-Benz",
    "rolls-royce": "Rolls-Royce", "rolls royce": "Rolls-Royce",
    "aston martin": "Aston Martin", "alfa romeo": "Alfa Romeo", "alfa-romeo": "Alfa Romeo",
    "land rover": "Land Rover", "land-rover": "Land Rover", "range rover": "Land Rover",
    "vw": "Volkswagen", "volkswagen": "Volkswagen",
    "citroen": "Citroën", "citroën": "Citroën", "austin healey": "Austin-Healey",
}


def _norm_brand(name):
    if not name or not isinstance(name, str):
        return None
    raw = name.strip()
    # Essaie: casse, puis sans ponctuation/espaces (PORSCHE, B.M.W., MC LAREN...)
    # contre le petit dict ET le registry complet (_BRAND_LOOKUP, defini plus bas).
    lookup = globals().get("_BRAND_LOOKUP", {})
    for key in (raw.lower(),
                re.sub(r"[.\s]+", " ", raw.lower()).strip(),
                re.sub(r"[.\s]+", "", raw.lower())):
        if key in _BRAND_CANONICAL:
            return _BRAND_CANONICAL[key]
        if key in lookup:
            return lookup[key]
    return raw


def _norm_fuel(s):
    if not s:
        return None
    low = s.lower()
    for k, v in _FUEL_MAP:
        if k in low:
            return v
    return None


def _norm_gear(s):
    if not s:
        return None
    low = s.lower()
    if re.search(r"autom", low):
        return "Automatique"
    if re.search(r"manu|schalt|schakel|handgesch", low):
        return "Manuelle"
    return None


def _year_from(value):
    if value is None:
        return None
    m = re.search(r"((?:18|19|20)\d{2})", str(value))
    if m:
        y = int(m.group(1))
        if 1900 < y <= datetime.now().year + 1:
            return y
    return None


def _parse_price(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    if not isinstance(value, str):
        return None
    s = re.sub(r"[^\d.,]", "", value)
    if not s:
        return None
    if "." in s and "," in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        tail = s.split(",")[-1]
        s = s.replace(",", "") if len(tail) == 3 else s.replace(",", ".")
    else:
        parts = s.split(".")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            s = s.replace(".", "")
    try:
        v = float(s)
        return v if v > 0 else None
    except ValueError:
        return None


try:
    from make_normalizer import BRAND_REGISTRY as _BRAND_REG
except Exception:
    _BRAND_REG = dict(_BRAND_CANONICAL)
_BRAND_LOOKUP = {k.lower(): v for k, v in _BRAND_REG.items()}
_BRAND_KEYS = sorted(_BRAND_LOOKUP.keys(), key=lambda s: -len(s))


_TITLE_SEP_RE = re.compile(r"\s*\|\s*|\s+[\u2022\u00b7\u2013\u2014]\s+|\s+-\s+")


def _brand_from_title(title):
    if not title:
        return None, None
    # gere "Dealer | Marque Modele" : teste le titre entier puis chaque
    # segment (| . - ). 1er segment a marque connue gagne. Strip prefixe
    # annee. L'annee reste recuperee via _year_from_title(_hint).
    for cand in [title, *_TITLE_SEP_RE.split(title)]:
        cand = cand.strip()
        if not cand:
            continue
        t = re.sub(r"^\s*(?:18|19|20)\d{2}\s+", "", cand)
        low = t.lower()
        for key in _BRAND_KEYS:
            if low == key or low.startswith(key + " "):
                rest = t[len(key):].strip(" -/|").strip()
                return _BRAND_LOOKUP[key], (re.sub(r"\s+", " ", rest)[:120] or None)
    return None, None


# ---------------------------------------------------------------------------
# Quality hardening helpers
# ---------------------------------------------------------------------------
_CURRENT_YEAR = datetime.now().year

_SOLD_RE = re.compile(
    r"\b(sold|verkauft|verkocht|vendu|venduto|vendido|reserved|reserviert|"
    r"r[ée]serv[ée]|onder\s+bod)\b", re.IGNORECASE)

# slugs terminaux qui sont des pages de site, jamais des fiches voiture
_NOISE_SLUGS = {
    "fahrzeuge", "fahrzeug", "vehicles", "vehicle", "cars", "car", "voitures",
    "voiture", "stock", "stocklist", "inventory", "occasion", "occasions",
    "veicoli", "coches", "coche", "samochody",
    "news", "news-ticker", "newsticker", "aktuelles", "blog", "nieuws",
    "kontakt", "contact", "impressum", "imprint", "ueber-uns", "uber-uns",
    "about", "about-us", "over-ons", "datenschutz", "privacy", "privacybeleid",
    "agb", "cgv", "mentions-legales", "ankauf", "verkauf", "verkaufen", "sell",
    "team", "galerie", "gallery", "home", "index", "service", "services",
    "finanzierung", "financing", "anfahrt", "history", "historie", "philosophie",
    "philosophy", "leistungen", "partner", "presse", "press", "jobs", "karriere",
    "career", "careers", "faq", "newsletter", "shop", "merchandise",
}

# vocabulaire de NOM de dealer (pour reperer un suffixe marque/site dans le modele)
_DEALER_WORDS = {
    "classic", "classics", "racing", "cars", "car", "collection", "collections",
    "automobile", "automobiles", "automobili", "auto", "autos", "oldtimer",
    "youngtimer", "motors", "motor", "motorcars", "garage", "garages", "center",
    "centre", "gmbh", "kg", "ltd", "srl", "bv", "sarl", "co", "company",
    "autoclassic", "sportwagen", "salon", "exclusive", "prestige", "gallery",
    "galerie", "fahrzeuge", "fahrzeug", "vehicles", "stock", "news", "kontakt",
    "ankauf", "archives", "archive", "kaufen", "gutshof", "rechtliches",
}

# mots de nom de dealer "forts" : suffisent a couper un suffixe de titre
_DEALER_STRONG = {
    "classic", "classics", "racing", "collection", "automobile", "automobili",
    "oldtimer", "youngtimer", "motors", "motorcars", "garage", "center", "centre",
    "sportwagen", "autoclassic", "exclusive", "prestige", "galerie", "gallery",
}

_NOISE_TITLE_RE = re.compile(
    r"^\s*(fahrzeuge|vehicles|news[\s-]*ticker|kontakt|contact|impressum|"
    r"(?:ü|u)ber[\s-]*uns|about(?:\s+us)?|over\s+ons|datenschutz|privacy|"
    r"ankauf|aktuelles|home|galerie|gallery|team|newsletter)\s*$",
    re.IGNORECASE)
_NOISE_CONTAINS_RE = re.compile(
    r"\barchives?\b|oldtimer\s+kaufen|\bkaufen\s*$|news[\s-]*ticker|"
    r"gutshof|rechtliches", re.IGNORECASE)


def _strip_accents(s):
    if not s:
        return ""
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def _bad_slug(last):
    return last.lower() in _NOISE_SLUGS or bool(_SOLD_RE.search(last))


def _year_from_title(text):
    if not text:
        return None
    m = re.search(r"\b(?:bj\.?|baujahr|year|ann[ée]e|anno|jahr)\s*:?\s*"
                  r"((?:18|19|20)\d{2})", text, re.IGNORECASE)
    if not m:
        m = re.search(r"\b((?:18|19|20)\d{2})\b", text)
    if m:
        y = int(m.group(1))
        if 1900 < y < _CURRENT_YEAR:
            return y
    return None


def _dealer_tokens(config):
    toks = set()
    dn = getattr(config, "display_name", None) or ""
    for t in re.split(r"[\s\-&_.]+", _strip_accents(dn).lower()):
        if len(t) >= 3:
            toks.add(t)
    host = urlparse(getattr(config, "listings_url", "") or "").netloc.lower().replace("www.", "")
    if host:
        toks.add(host)
        base = host.split(".")[0]
        for t in re.split(r"[\-_]+", base):
            if len(t) >= 3:
                toks.add(t)
    return toks


def _clean_model(mo, toks):
    if not mo:
        return mo
    mo = mo.split(" | ")[0].strip()
    for sep in (" – ", " — ", " - "):
        if sep in mo:
            left, right = mo.rsplit(sep, 1)
            rl = _strip_accents(right).lower().strip()
            rl_words = [w for w in re.split(r"[\s&]+", rl) if w]
            has_digit = any(ch.isdigit() for ch in rl)
            signal = (
                any(tok in rl for tok in toks if len(tok) >= 4)
                or re.search(r"\.(de|com|eu|nl|fr|it|ch|be|at|es)\b|co\.uk", rl)
                or (rl_words and all(w in _DEALER_WORDS for w in rl_words))
                or any(w in _DEALER_STRONG for w in rl_words)
            )
            if left.strip() and not has_digit and len(rl_words) <= 4 and signal:
                mo = left.strip()
    return re.sub(r"\s+", " ", mo).strip(" -–—/|") or None


def _is_noise_title(mo):
    if not mo:
        return False
    s = mo.strip()
    return bool(_NOISE_TITLE_RE.search(s) or _NOISE_CONTAINS_RE.search(s))


def _looks_sold(text):
    return bool(text and _SOLD_RE.search(text))


def _mostly_dealer(ml, toks):
    words = [w for w in re.split(r"[\s&\-]+", _strip_accents(ml).lower()) if len(w) >= 3]
    if not words:
        return False
    bag = _DEALER_WORDS | {t for t in toks if len(t) >= 3 and "." not in t}
    return all(w in bag for w in words)


def _title_hint(soup):
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(" ", strip=True)
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        return og["content"]
    t = soup.find("title")
    return t.get_text(" ", strip=True) if t else ""


@register("generic_jsonld")
class GenericJsonLdExtractor(Extractor):
    """Config-driven JSON-LD-first extractor for the long tail of dealers."""

    DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; AutoRadarBot/1.0; +https://carnet.life/about)",
        "Accept-Language": "en;q=0.9,de;q=0.8,fr;q=0.8,it;q=0.7,nl;q=0.7",
    }
    INTER_REQUEST_DELAY_S = 0.5
    DEFAULT_MAX_PAGES = 10

    def __init__(self, http_client: Optional[httpx.Client] = None):
        self._client = http_client or httpx.Client(
            timeout=self.DEFAULT_TIMEOUT, headers=self.DEFAULT_HEADERS, follow_redirects=True,
        )

    def extract(self, config: SourceConfig, limit: Optional[int] = None) -> ExtractionResult:
        result = ExtractionResult(source_slug=config.slug)
        t0 = time.monotonic()
        try:
            urls = self._discover(config)
            result.pages_fetched = 1
            if limit is not None:
                urls = urls[:limit]
            for url in urls:
                try:
                    car = self._one(url, config)
                    if car is not None:
                        result.cars.append(car)
                    result.pages_fetched += 1
                except Exception as exc:
                    msg = f"{config.slug} detail failed for {url}: {exc}"
                    logger.warning(msg)
                    result.errors.append(msg)
                time.sleep(self.INTER_REQUEST_DELAY_S)
        except Exception as exc:
            msg = f"{config.slug} listing catastrophic: {exc}"
            logger.error(msg)
            result.errors.append(msg)
        result.duration_s = time.monotonic() - t0
        return result

    def _discover(self, config: SourceConfig) -> list[str]:
        sel = config.selectors or {}
        listings_url = config.listings_url
        if not listings_url:
            logger.warning(f"{config.slug}: pas de listings_url — skip")
            return []
        p = urlparse(listings_url)
        base = f"{p.scheme}://{p.netloc}"
        custom = sel.get("detail_url_regex")
        detail_re = re.compile(custom, re.IGNORECASE) if custom else None
        page_param = sel.get("page_param")
        max_pages = int(sel.get("max_pages", self.DEFAULT_MAX_PAGES))
        min_group = int(sel.get("min_group", 4))
        noise_re = re.compile(
            r"/(?:blog|news|nieuws|actualites|category|categorie|categorias|tag|tags|"
            r"page|pagina|cart|panier|warenkorb|account|login|register|contact|about|"
            r"over-ons|impressum|datenschutz|privacy|privacybeleid|cookie|wp-content|"
            r"wp-admin|wp-json|feed|sitemap|mentions|cgv|agb|faq|service|services|"
            r"finance|financ|verkopen|verkaufen|sell|kopen|buy|home|merk|merken|"
            r"marque|marques|marca|marcas|brand|brands)(?:/|$)",
            re.IGNORECASE,
        )

        def page_links(html):
            soup = BeautifulSoup(html, "html.parser")
            out = []
            for a in soup.find_all("a", href=True):
                href = a["href"].split("#")[0].split("?")[0]
                if not href:
                    continue
                full = href if href.startswith("http") else urljoin(base, href)
                u = urlparse(full)
                if u.netloc != p.netloc or not u.path or u.path == "/":
                    continue
                out.append(full)
            return out

        def fiche_like(last):
            if len(last) < 5 or not re.search(r"[a-z]", last, re.IGNORECASE):
                return False
            if _bad_slug(last):
                return False
            return ("-" in last) or bool(re.search(r"\d", last))

        def pick_detail(links):
            if detail_re:
                return [l for l in links if detail_re.search(l)]
            groups = {}
            for l in links:
                path = urlparse(l).path.rstrip("/")
                if "/" not in path or noise_re.search(path):
                    continue
                prefix, _, last = path.rpartition("/")
                if not fiche_like(last):
                    continue
                groups.setdefault(prefix, []).append(l)
            if not groups:
                return []
            best = max(groups, key=lambda k: len(set(groups[k])))
            picked = list(dict.fromkeys(groups[best]))
            if len(picked) < min_group:
                alll = []
                for ls in groups.values():
                    alll.extend(ls)
                return list(dict.fromkeys(alll))
            return picked

        seen = set()
        urls = []
        try:
            first = self._client.get(listings_url)
            first.raise_for_status()
        except Exception:
            # listings_url mort (404, vieux recon...) : retombe sur la racine du
            # domaine, d'ou le saut home->stock pourra retrouver la page-stock.
            root = f"{p.scheme}://{p.netloc}/"
            if root.rstrip("/") == listings_url.rstrip("/"):
                raise
            first = self._client.get(root)
            first.raise_for_status()
            listings_url = root
            p = urlparse(listings_url)
        for l in pick_detail(page_links(first.text)):
            if l not in seen:
                seen.add(l)
                urls.append(l)

        # Home -> page-stock : si la page de depart donne peu de fiches, suivre
        # le lien "nos vehicules / stock / annonces / fahrzeuge..." et
        # redecouvrir de la. On n'adopte le saut que s'il rapporte PLUS de
        # fiches (garde-fou anti-mauvais-lien). Un seul hop.
        if len(urls) < 20:
            stock = self._find_stock_link(first.text, listings_url, p.netloc)
            if stock and stock.rstrip("/") != listings_url.rstrip("/"):
                try:
                    r2 = self._client.get(stock)
                    r2.raise_for_status()
                    new = pick_detail(page_links(r2.text))
                    if len(set(new)) > len(urls):
                        listings_url = stock
                        p = urlparse(listings_url)
                        first = r2
                        seen, urls = set(), []
                        for l in new:
                            if l not in seen:
                                seen.add(l)
                                urls.append(l)
                        logger.info(f"{config.slug}: hop home->stock {stock}")
                except Exception as exc:
                    logger.warning(f"{config.slug} stock-hop KO: {exc}")

        # Pagination : explicite (selectors) sinon auto-detectee depuis la page 1.
        # Debloque le catalogue complet des dealers dont le stock est pagine
        # (?page=N, ?paged=N... ou /page/N/) sans config par dealer.
        page_style = "query"
        if not page_param and urls:
            _soup1 = BeautifulSoup(first.text, "html.parser")
            for a in _soup1.find_all("a", href=True):
                mm = re.search(r"[?&](page|paged|pagina|seite|pagenumber|pagenr|pg)=(\d+)",
                               a["href"], re.IGNORECASE)
                if mm and int(mm.group(2)) >= 2:
                    page_param, page_style = mm.group(1), "query"
                    break
            if not page_param:
                for a in _soup1.find_all("a", href=True):
                    if re.search(r"/page/\d+/?$", urlparse(a["href"]).path, re.IGNORECASE):
                        page_param, page_style = "page", "path"
                        break

        if page_param and urls:
            for n in range(2, max_pages + 1):
                if page_style == "path":
                    page_url = f"{listings_url.rstrip('/')}/page/{n}/"
                else:
                    sep = "&" if "?" in listings_url else "?"
                    page_url = f"{listings_url}{sep}{page_param}={n}"
                try:
                    r = self._client.get(page_url)
                    r.raise_for_status()
                    before = len(urls)
                    for l in pick_detail(page_links(r.text)):
                        if l not in seen:
                            seen.add(l)
                            urls.append(l)
                    if len(urls) == before:
                        break
                except Exception as exc:
                    logger.warning(f"{config.slug} page {n} failed: {exc}")
                    break
                time.sleep(self.INTER_REQUEST_DELAY_S)
        logger.info(f"{config.slug}: discovered {len(urls)} detail URLs")
        return urls

    _STOCK_KW = re.compile(
        r"(v[eé]hicule|voiture|stock|inventory|inventaire|annonce|occasion|"
        r"showroom|for[-\s]?sale|fahrzeug|bestand|gebrauchtwagen|catalog|"
        r"vetrina|vendita|our[-\s]?cars|le[-\s]?nostre[-\s]?auto|nos[-\s]?autos?)",
        re.IGNORECASE,
    )
    _STOCK_STRONG = re.compile(
        r"(stock|annonce|occasion|inventory|inventaire|vehicules?|voitures|"
        r"fahrzeuge|for-sale|vendita|showroom)",
        re.IGNORECASE,
    )

    @classmethod
    def _find_stock_link(cls, html, listings_url, netloc):
        """Depuis une home, trouve le meilleur lien vers la page-stock."""
        soup = BeautifulSoup(html, "html.parser")
        base = f"{urlparse(listings_url).scheme}://{netloc}"
        host = netloc.replace("www.", "")
        best, best_score = None, 0.0
        for a in soup.find_all("a", href=True):
            href = a["href"].split("#")[0]
            if not href or href.startswith(("mailto:", "tel:", "javascript:")):
                continue
            full = href if href.startswith("http") else urljoin(base, href)
            u = urlparse(full)
            if u.netloc.replace("www.", "") != host:
                continue
            path = u.path.rstrip("/")
            if not path or path == "/":
                continue
            text = a.get_text(" ", strip=True) or ""
            if not cls._STOCK_KW.search(f"{path} {text}"):
                continue
            score = 0.0
            if cls._STOCK_KW.search(path):
                score += 2
            if cls._STOCK_KW.search(text):
                score += 1
            if cls._STOCK_STRONG.search(path):
                score += 2
            score -= path.count("/") * 0.2
            if score > best_score:
                best_score, best = score, full
        return best

    def _one(self, url: str, config: SourceConfig) -> Optional[CarListing]:
        resp = self._client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        car = CarListing(src_url=url, src=config.slug)
        obj = self._find_vehicle_jsonld(soup)
        if obj:
            self._apply_jsonld(obj, car)
        if not car.mk:
            for node in (soup.find("h1"),
                         soup.find("meta", attrs={"property": "og:title"}),
                         soup.find("title")):
                if not node:
                    continue
                txt = node.get("content") if node.name == "meta" else node.get_text(" ", strip=True)
                mk2, mo2 = _brand_from_title((txt or "").strip())
                if mk2:
                    car.mk = mk2
                    if not car.mo and mo2:
                        car.mo = mo2
                    break
        meta = self._meta_desc(soup)
        if meta and car.px is None:
            m = re.search(r"(?:Preis|Price|Prix|Prezzo|Prijs)\s*[:.]?\s*([\d.,]+)\s*(?:eur|EUR|€)", meta, re.IGNORECASE)
            if m:
                car.px = _parse_price(m.group(1))
                car.cu = car.cu or "EUR"
        self._enrich_html(soup, car)
        self._enrich_css(soup, car, config.selectors or {})
        if not car.mo:
            h1 = soup.find("h1")
            if h1:
                t = h1.get_text(" ", strip=True)
                if car.mk and t.lower().startswith(car.mk.lower() + " "):
                    t = t[len(car.mk) + 1:].strip()
                car.mo = (t[:120] or None)
        if not car.photos:
            og = soup.find("meta", attrs={"property": "og:image"})
            if og and og.get("content"):
                car.photos = [og["content"]]
        car.ci = car.ci or config.city
        car.co = car.co or config.country
        car.cu = car.cu or (config.currency.upper() if config.currency else "EUR")

        # --- quality hardening -------------------------------------------------
        _toks = _dealer_tokens(config)
        _hint = _title_hint(soup)
        car.mo = _clean_model(car.mo, _toks)
        if car.mo:
            car.mo = re.split(r"\s+(?:kaufen|zu\s+verkaufen|for\s+sale|te\s+koop)\b", car.mo, flags=re.IGNORECASE)[0].strip()
        if car.mk and car.mo:
            for _w in car.mk.replace("-", " ").split():
                if len(_w) >= 3 and car.mo.lower().startswith(_w.lower() + " "):
                    car.mo = car.mo[len(_w) + 1:].strip()
                    break
        # annee: prefere "Bj./Baujahr" du titre si JSON-LD a donne l'annee courante ou rien
        _yt = _year_from_title(car.mo) or _year_from_title(_hint)
        if _yt and (car.yr is None or car.yr >= _CURRENT_YEAR):
            car.yr = _yt
        # SOLD: drop si vendu (titre, modele, url)
        if _looks_sold(car.mo) or _looks_sold(_hint) or _looks_sold(url):
            logger.debug(f"sold, dropping {url}")
            return None
        # titre de page de site pris pour une fiche
        if _is_noise_title(car.mo) or _is_noise_title(_hint):
            logger.debug(f"noise title, dropping {url}")
            return None
        # modele == marque / nom du dealer / contient le domaine
        if car.mo:
            _ml = car.mo.lower().strip()
            if (_ml == (car.mk or "").lower()
                    or _mostly_dealer(_ml, _toks)
                    or any(t in _ml for t in _toks if "." in t and len(t) >= 6)):
                logger.debug(f"model==dealer/brand, dropping {url}")
                return None
        # --- end hardening -----------------------------------------------------

        car.raw = {"extractor": "generic_jsonld", "jsonld": bool(obj)}
        if not car.mk:
            # Fallback : marque depuis le slug d'URL (fiat-abarth-695, autobianchi-y10,
            # volkswagen-t-roc...,svoc260.html) quand titre/JSON-LD n'ont rien donne.
            _slug = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
            _slug = re.sub(r",\w+\.html?$", "", _slug, flags=re.IGNORECASE)
            _slug = re.sub(r"[-_]+", " ", _slug).strip()
            _mk4, _mo4 = _brand_from_title(_slug)
            if _mk4:
                car.mk = _mk4
                if not car.mo and _mo4:
                    car.mo = _mo4
        if not car.mk:
            logger.debug(f"no brand from {url}; dropping")
            return None
        if not obj and not car.mo:
            logger.debug(f"no model (non-jsonld) from {url}; dropping")
            return None
        return car

    @staticmethod
    def _find_vehicle_jsonld(soup: BeautifulSoup) -> Optional[dict]:
        best = None
        for block in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw = block.string or block.get_text() or ""
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            stack = data if isinstance(data, list) else [data]
            flat = []
            for it in stack:
                if isinstance(it, dict) and isinstance(it.get("@graph"), list):
                    flat.extend(it["@graph"])
                else:
                    flat.append(it)
            for cand in flat:
                if not isinstance(cand, dict):
                    continue
                t = cand.get("@type")
                types = {str(x).lower() for x in ([t] if isinstance(t, str) else (t or []))}
                if types & _JSONLD_VEHICLE_TYPES:
                    if types & {"car", "vehicle"}:
                        return cand
                    best = best or cand
        return best

    @staticmethod
    def _apply_jsonld(obj: dict, car: CarListing) -> None:
        b = obj.get("brand") or obj.get("manufacturer")
        if isinstance(b, dict):
            b = b.get("name")
        if b:
            car.mk = _norm_brand(b)
        model = obj.get("model")
        if isinstance(model, dict):
            model = model.get("name")
        name = obj.get("name")
        if model and isinstance(model, str):
            car.mo = model.strip()[:120]
        elif name and isinstance(name, str):
            n = name.strip()
            if car.mk and n.lower().startswith(car.mk.lower() + " "):
                n = n[len(car.mk) + 1:].strip()
            car.mo = n[:120]
        for k in ("vehicleModelDate", "modelDate", "productionDate", "releaseDate", "dateVehicleFirstRegistered"):
            if obj.get(k):
                y = _year_from(obj[k])
                if y and y < _CURRENT_YEAR:
                    car.yr = y
                    break
        mil = obj.get("mileageFromOdometer")
        if isinstance(mil, dict):
            mil = mil.get("value")
        if mil is not None:
            c = re.sub(r"[^\d]", "", str(mil))
            if c:
                km = int(c)
                if 0 <= km <= 2_000_000:
                    car.km = km
        if obj.get("fuelType"):
            car.fu = _norm_fuel(str(obj["fuelType"]))
        if obj.get("vehicleTransmission"):
            car.ge = _norm_gear(str(obj["vehicleTransmission"]))
        offers = obj.get("offers") or {}
        if isinstance(offers, list) and offers:
            offers = offers[0]
        if isinstance(offers, dict):
            px = _parse_price(offers.get("price"))
            if px:
                car.px = px
            cu = offers.get("priceCurrency")
            if isinstance(cu, str):
                car.cu = cu.upper()
        img = obj.get("image")
        if isinstance(img, str):
            car.photos = [img]
        elif isinstance(img, list):
            car.photos = [x for x in img if isinstance(x, str)][:10]
        elif isinstance(img, dict) and img.get("url"):
            car.photos = [img["url"]]
        desc = obj.get("description")
        if isinstance(desc, str) and len(desc) > 30:
            car.de = re.sub(r"\s+", " ", desc).strip()[:2000]

    @staticmethod
    def _meta_desc(soup: BeautifulSoup) -> Optional[str]:
        m = soup.find("meta", attrs={"name": "description"})
        return m["content"] if m and isinstance(m.get("content"), str) else None

    @staticmethod
    def _enrich_html(soup: BeautifulSoup, car: CarListing) -> None:
        text = soup.get_text(" ", strip=True)
        # Coupe la section "vehicules similaires" : sinon prix/annee/km de la
        # fiche sujet sont pollues par les cartes liees (jusqu'a ~40 voitures).
        _rel = re.search(
            r"(?:dans la m[eê]me collection|m[eê]me collection|vous aimerez"
            r"|autres v[eé]hicules|nos autres|v[eé]hicules similaires"
            r"|[aä]hnliche fahrzeuge|potrebbe(?:ro)? interessart|veicoli simili"
            r"|related vehicles?|you may also|similar (?:cars|vehicles))",
            text, re.IGNORECASE)
        if _rel:
            text = text[:_rel.start()]
        if not car.yr:
            m = re.search(r"(?:Erstzulassung|Baujahr|First registration|Year of (?:construction|manufacture)|Mise en circulation|1(?:re|ere|ère)? mise en circulation|Immatriculation|Immatricolazione|Prima immatricolazione|Model year|Modelljahr|mod[eè]le|Année|Anno|Bouwjaar|Year)[^\d]{0,12}(?:\d{1,2}\s*[/.\-]\s*){0,2}((?:18|19|20)\d{2})", text, re.IGNORECASE)
            if m:
                y = int(m.group(1))
                if 1900 < y <= datetime.now().year + 1:
                    car.yr = y
        if not car.km:
            m = re.search(r"(?:Kilometerstand|Mileage|Odometer|Kilométrage|Chilometraggio)\s*[:.]?\s*([\d.,]+)\s*km", text, re.IGNORECASE)
            if not m:
                m = re.search(r"([\d.,'’]{3,})\s*km\b(?!\s*/?\s*h)", text, re.IGNORECASE)
            if m:
                c = re.sub(r"[^\d]", "", m.group(1))
                if c:
                    km = int(c)
                    if 0 <= km <= 2_000_000:
                        car.km = km
        if car.px is None:
            best = None
            for m in re.finditer(r"(?:€|EUR|CHF|£)\s*([\d][\d.,'’]{3,})|([\d][\d.,'’]{3,})\s*(?:€|EUR|CHF|£)", text):
                val = _parse_price(m.group(1) or m.group(2))
                if val and 1000 <= val <= 100_000_000 and (best is None or val > best):
                    best = val
            if best:
                car.px = best
        if not car.ge:
            if re.search(r"\b(?:Automatik|Automatic|Automatique|Automatico|Automaat)\b", text, re.IGNORECASE):
                car.ge = "Automatique"
            elif re.search(r"\b(?:Schaltgetriebe|Manual|Manuell|Manuelle|Manuale|Handgeschakeld)\b", text, re.IGNORECASE):
                car.ge = "Manuelle"
        if not car.fu:
            m = re.search(r"(?:Kraftstoff|Fuel type|Fuel|Carburant|Brandstof|Treibstoff|Alimentazione)\s*[:.]?\s*([A-Za-z]+)", text, re.IGNORECASE)
            if m:
                car.fu = _norm_fuel(m.group(1))

    @staticmethod
    def _enrich_css(soup: BeautifulSoup, car: CarListing, sel: dict) -> None:
        def pick(key):
            css = sel.get(key)
            if not css:
                return None
            el = soup.select_one(css)
            return el.get_text(" ", strip=True) if el else None
        if car.px is None and sel.get("price_selector"):
            car.px = _parse_price(pick("price_selector"))
        if not car.mo and sel.get("title_selector"):
            t = pick("title_selector")
            if t:
                car.mo = t[:120]
        if not car.yr and sel.get("year_selector"):
            car.yr = _year_from(pick("year_selector"))
        if not car.km and sel.get("km_selector"):
            v = pick("km_selector")
            if v:
                c = re.sub(r"[^\d]", "", v)
                if c:
                    car.km = int(c)
