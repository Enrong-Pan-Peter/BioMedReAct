"""
Parse JATS XML to structured article dicts.
"""

from typing import Any, Dict, List, Optional

from lxml import etree


def _get_text(element) -> str:
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def parse_article_xml(xml_string: str) -> Optional[Dict[str, Any]]:
    """Parse JATS XML. Returns dict or None on failure."""
    try:
        root = etree.fromstring(xml_string.encode("utf-8"))
    except etree.XMLSyntaxError:
        return None

    front = root.find(".//front")
    article_meta = front.find(".//article-meta") if front is not None else None
    if article_meta is None:
        return None

    pmc_id = ""
    for aid in article_meta.findall(".//article-id"):
        if aid.get("pub-id-type") == "pmc":
            pmc_id = aid.text or ""
            break

    pmid = ""
    for aid in article_meta.findall(".//article-id"):
        if aid.get("pub-id-type") == "pmid":
            pmid = aid.text or ""
            break

    title_el = article_meta.find(".//article-title")
    title = _get_text(title_el)

    abstract_el = article_meta.find(".//abstract")
    abstract = _get_text(abstract_el) if abstract_el is not None else ""

    authors = []
    for contrib in article_meta.findall(".//contrib[@contrib-type='author']"):
        surname = contrib.findtext(".//surname", default="")
        given = contrib.findtext(".//given-names", default="")
        if surname:
            authors.append(f"{given} {surname}".strip())

    journal = ""
    journal_el = front.find(".//journal-title") if front is not None else None
    if journal_el is not None:
        journal = _get_text(journal_el)

    pub_date = ""
    pub_date_el = article_meta.find(".//pub-date")
    if pub_date_el is not None:
        y = pub_date_el.findtext("year", default="")
        m = pub_date_el.findtext("month", default="")
        d = pub_date_el.findtext("day", default="")
        pub_date = f"{y}-{m.zfill(2)}-{d.zfill(2)}" if y else ""

    keywords = []
    for kwd in article_meta.findall(".//kwd"):
        t = _get_text(kwd)
        if t:
            keywords.append(t)

    body_el = root.find(".//body")
    body_text = _get_text(body_el) if body_el is not None else ""

    if pmc_id and not pmc_id.upper().startswith("PMC"):
        pmc_id = f"PMC{pmc_id}"

    return {
        "pmc_id": pmc_id,
        "pmid": pmid,
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "journal": journal,
        "pub_date": pub_date,
        "keywords": keywords,
        "body_text": body_text[:5000],
    }


def parse_and_filter(raw_xmls: List[str]) -> List[Dict[str, Any]]:
    """Parse all, keep only those with abstracts."""
    articles = [parse_article_xml(x) for x in raw_xmls if x]
    return [a for a in articles if a and a.get("abstract")]
