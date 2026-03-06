"""
Step 3 — Parse XML to Structured JSON

Thought process: The S3 XML files use the JATS (Journal Article Tag Suite) format.
Each field has dedicated tags — title, abstract, authors, keywords, etc. We use lxml
to parse and extract structured data. Chose XML over TXT for clean field extraction.
Articles without abstracts are excluded since embedding and summarization need text.
"""

from typing import Any, Dict, List, Optional

from lxml import etree


def _get_text(element) -> str:
    """Recursively get all text from an element and its children."""
    return "".join(element.itertext()).strip() if element is not None else ""


def parse_article_xml(xml_string: str) -> Optional[Dict[str, Any]]:
    """
    Parse JATS XML and return a structured article dict.

    Extracts: pmc_id, pmid, title, abstract, authors, journal, pub_date,
    keywords, body_text. Returns None on parse failure.
    """
    try:
        root = etree.fromstring(xml_string.encode("utf-8"))
    except etree.XMLSyntaxError:
        return None

    front = root.find(".//front")
    article_meta = front.find(".//article-meta") if front is not None else None

    if article_meta is None:
        return None

    # PMC ID
    pmc_id = ""
    for aid in article_meta.findall(".//article-id"):
        if aid.get("pub-id-type") == "pmc":
            pmc_id = aid.text or ""
            break

    # PMID
    pmid = ""
    for aid in article_meta.findall(".//article-id"):
        if aid.get("pub-id-type") == "pmid":
            pmid = aid.text or ""
            break

    # Title
    title_el = article_meta.find(".//article-title")
    title = _get_text(title_el)

    # Abstract
    abstract_el = article_meta.find(".//abstract")
    abstract = _get_text(abstract_el) if abstract_el is not None else ""

    # Authors
    authors = []
    for contrib in article_meta.findall(".//contrib[@contrib-type='author']"):
        surname = contrib.findtext(".//surname", default="")
        given = contrib.findtext(".//given-names", default="")
        if surname:
            authors.append(f"{given} {surname}".strip())

    # Journal
    journal = ""
    journal_el = front.find(".//journal-title") if front is not None else None
    if journal_el is not None:
        journal = _get_text(journal_el)

    # Publication date
    pub_date = ""
    pub_date_el = article_meta.find(".//pub-date")
    if pub_date_el is not None:
        year = pub_date_el.findtext("year", default="")
        month = pub_date_el.findtext("month", default="")
        day = pub_date_el.findtext("day", default="")
        pub_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}" if year else ""

    # Keywords
    keywords = []
    for kwd in article_meta.findall(".//kwd"):
        kw_text = _get_text(kwd)
        if kw_text:
            keywords.append(kw_text)

    # Body text (for future RAG use)
    body_el = root.find(".//body")
    body_text = _get_text(body_el) if body_el is not None else ""

    # Normalize PMC ID format (ensure PMC prefix)
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
    """
    Parse all XMLs and filter out articles without abstracts.

    Abstracts are required for embedding and summarization downstream.
    """
    articles = [parse_article_xml(xml) for xml in raw_xmls if xml]
    return [a for a in articles if a is not None and a["abstract"]]
