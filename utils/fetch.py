"""
Fetch article XML from PubMed Central Open Access S3 bucket.
Tries both old and new key structures. Caches to .cache/ on disk.
"""

from pathlib import Path
from typing import List, Optional

import boto3
from botocore import UNSIGNED
from botocore.config import Config

s3 = boto3.client(
    "s3",
    region_name="us-east-1",
    config=Config(signature_version=UNSIGNED),
)

BUCKET = "pmc-oa-opendata"
CACHE_DIR = Path(".cache")


def fetch_xml_from_s3(pmc_id: str, quiet: bool = False) -> Optional[str]:
    """
    Download XML for a PMC ID. Checks local cache first.
    Returns None if not found. Set quiet=True to suppress warnings.
    """
    # check cache
    cache_file = CACHE_DIR / f"{pmc_id}.xml"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")

    new_key = f"{pmc_id}.1/{pmc_id}.1.xml"
    old_key = f"oa_comm/xml/all/{pmc_id}.xml"

    for key in [new_key, old_key]:
        try:
            obj = s3.get_object(Bucket=BUCKET, Key=key)
            xml = obj["Body"].read().decode("utf-8")
            # write to cache
            CACHE_DIR.mkdir(exist_ok=True)
            cache_file.write_text(xml, encoding="utf-8")
            return xml
        except Exception:
            continue

    if not quiet:
        print(f"WARNING: {pmc_id} not found in oa_comm. Skipping.")
    return None


def fetch_all_xmls(pmc_ids: List[str], quiet: bool = False) -> List[str]:
    """Fetch XML for each ID. Returns list of successfully fetched XML strings."""
    out = []
    for pmc_id in pmc_ids:
        xml = fetch_xml_from_s3(pmc_id, quiet=quiet)
        if xml:
            out.append(xml)
    return out
