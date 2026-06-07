from urllib.parse import urlparse

from selenium.webdriver.common.by import By

from pnda.browser import (
    has_child_element,
    navigate_and_wait,
    safe_find_attr,
    safe_find_text,
)
from pnda.config import (
    ADDITIONAL_INFO_SELECTOR,
    CATEGORY_LIST_SELECTOR,
    DATASET_MARKER_SELECTOR,
    DATE_LABELS,
    PAGER_NEXT_SELECTOR,
    PUBLISHER_LABELS,
    RESOURCE_FORMAT_SELECTOR,
    SEARCH_RESULT_SELECTOR,
    SEARCH_URL,
    TITLE_LINK_SELECTOR,
    VALID_RESOURCE_FORMATS,
)
from pnda.text import make_absolute_url, normalize_label, normalize_spaces, split_name_and_count


def get_category_links(driver, wait):
    elements = navigate_and_wait(driver, wait, SEARCH_URL, CATEGORY_LIST_SELECTOR)

    categories = []
    for item in elements:
        raw_text = item.text.strip()
        name, _ = split_name_and_count(raw_text)
        href = make_absolute_url(item.get_attribute("href"))
        categories.append({"categoria": name, "link": href})

    return categories


def _build_paginated_url(url, page_index):
    if page_index == 0:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}page=0%2C{page_index}"


def _is_dataset_url(url):
    path = urlparse(url).path.rstrip("/")
    return "/dataset/" in path and "/resource/" not in path


def _extract_dataset_links_from_page(driver, categoria):
    datasets = []
    articles = driver.find_elements(By.CSS_SELECTOR, SEARCH_RESULT_SELECTOR)

    for article in articles:
        if not has_child_element(article, DATASET_MARKER_SELECTOR):
            continue

        title = safe_find_text(article, TITLE_LINK_SELECTOR)
        link = make_absolute_url(safe_find_attr(article, TITLE_LINK_SELECTOR, "href"))

        if not link or not _is_dataset_url(link):
            continue

        datasets.append({"titulo": title, "categoria": categoria, "link": link})

    return datasets


def scrape_category_dataset_links(driver, wait, category_info):
    categoria = category_info["categoria"]
    base_url = category_info["link"]
    dataset_rows = []
    seen_links = set()
    page_index = 0

    while True:
        page_url = _build_paginated_url(base_url, page_index)
        print(f"Procesando categoria '{categoria}' - pagina {page_index + 1}")

        navigate_and_wait(driver, wait, page_url, SEARCH_RESULT_SELECTOR)
        page_datasets = _extract_dataset_links_from_page(driver, categoria)

        if not page_datasets and page_index == 0:
            break

        for dataset in page_datasets:
            if dataset["link"] not in seen_links:
                seen_links.add(dataset["link"])
                dataset_rows.append(dataset)

        next_buttons = driver.find_elements(By.CSS_SELECTOR, PAGER_NEXT_SELECTOR)
        if not next_buttons:
            break

        page_index += 1

    return dataset_rows


def _get_table_value(driver, possible_labels):
    normalized = [normalize_label(label) for label in possible_labels]

    rows = driver.find_elements(By.CSS_SELECTOR, ADDITIONAL_INFO_SELECTOR)
    for row in rows:
        cells = row.find_elements(By.CSS_SELECTOR, "th, td")
        if len(cells) < 2:
            continue

        label = normalize_label(cells[0].text)
        if any(option in label for option in normalized):
            return normalize_spaces(cells[1].text)

    return ""


def _count_valid_resources(driver):
    count = 0
    resource_formats = driver.find_elements(By.CSS_SELECTOR, RESOURCE_FORMAT_SELECTOR)

    for item in resource_formats:
        fmt = (item.get_attribute("data-format") or "").strip().lower()
        if fmt in VALID_RESOURCE_FORMATS:
            count += 1

    return count


def extract_dataset_detail(driver, wait, dataset_info):
    print(f"Analizando dataset: {dataset_info['titulo']}")

    navigate_and_wait(
        driver, wait, dataset_info["link"], ADDITIONAL_INFO_SELECTOR, required=False
    )

    entidad = _get_table_value(driver, PUBLISHER_LABELS)
    fecha = _get_table_value(driver, DATE_LABELS)
    total_archivos = _count_valid_resources(driver)

    return {
        "titulo": dataset_info["titulo"],
        "categoria": dataset_info["categoria"],
        "numero_datasets_asociados": total_archivos,
        "fecha_ultima_actualizacion": fecha,
        "entidad_responsable": entidad,
    }
