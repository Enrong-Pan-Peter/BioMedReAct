"""
Fetch article XML from PubMed Central Open Access S3 bucket.
Tries both old and new key structures.
"""

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


def fetch_xml_from_s3(pmc_id: str, quiet: bool = False) -> Optional[str]:
    """
    Download XML for a PMC ID. Tries new path first, then old.
    Returns None if not found. Set quiet=True to suppress warnings.
    """
    new_key = f"{pmc_id}.1/{pmc_id}.1.xml"
    old_key = f"oa_comm/xml/all/{pmc_id}.xml"

    for key in [new_key, old_key]:
        try:
            obj = s3.get_object(Bucket=BUCKET, Key=key)
            return obj["Body"].read().decode("utf-8")
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
