import re
from urllib.parse import urljoin

from pnda.config import BASE_URL


def normalize_spaces(text):
    return " ".join(text.split()).strip()


def normalize_label(text):
    return normalize_spaces(text).lower().replace(":", "")


def split_name_and_count(text):
    cleaned = normalize_spaces(text)
    cleaned = re.sub(r"Apply\s+.*?filter$", "", cleaned, flags=re.IGNORECASE).strip()
    match = re.match(r"^(.*?)(?:\s*\((\d+)\))?$", cleaned)
    if not match:
        return cleaned, ""
    return match.group(1).strip(), match.group(2) or ""


def make_absolute_url(relative_url):
    return urljoin(BASE_URL, relative_url)
