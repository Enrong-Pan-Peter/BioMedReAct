"""
Step 2 — Fetch XML Files from S3

Thought process: Once we have PMC IDs from the E-utilities search, we need the actual
article content. The PubMed Central Open Access dataset lives on AWS S3. The bucket is
publicly readable — no AWS account or credentials needed. We use boto3 with UNSIGNED
config to access it. Not every PMC article is in the oa_comm subset; some are in
oa_noncomm or not open-access. We handle missing files gracefully.
"""

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from typing import List, Optional


# S3 client for public bucket (no AWS credentials needed)
# signature_version=UNSIGNED is required — boto3 defaults to signed requests
s3 = boto3.client(
    "s3",
    region_name="us-east-1",
    config=Config(signature_version=UNSIGNED),
)

BUCKET = "pmc-oa-opendata"
KEY_PREFIX = "oa_comm/xml/all"


def fetch_xml_from_s3(pmc_id: str) -> Optional[str]:
    """
    Download full-text XML for a given PMC ID from S3.

    Returns XML string or None if the article is not in oa_comm (e.g., oa_noncomm
    or not open-access). Handles NoSuchKey and other errors gracefully.
    """
    key = f"{KEY_PREFIX}/{pmc_id}.xml"
    try:
        obj = s3.get_object(Bucket=BUCKET, Key=key)
        return obj["Body"].read().decode("utf-8")
    except s3.exceptions.NoSuchKey:
        print(f"WARNING: {pmc_id} not found in oa_comm. Skipping.")
        return None
    except Exception as e:
        print(f"ERROR fetching {pmc_id}: {e}")
        return None


def fetch_all_xmls(pmc_ids: List[str]) -> List[str]:
    """
    Fetch XML for all PMC IDs. Returns only successfully retrieved XML strings.
    """
    raw_xmls = []
    for i, pmc_id in enumerate(pmc_ids):
        xml = fetch_xml_from_s3(pmc_id)
        if xml is not None:
            raw_xmls.append(xml)
        if (i + 1) % 10 == 0:
            print(f"Fetched {i + 1}/{len(pmc_ids)}...")
    return raw_xmls
