import re
from urllib.parse import urljoin, urlparse

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


BASE_URL = "https://www.datosabiertos.gob.pe"
SEARCH_URL = f"{BASE_URL}/search?query=&sort_by=changed&sort_order=DESC"
OUTPUT_FILE = "entregable1.xlsx"
WAIT_SECONDS = 20


def text_or_empty(parent, selector):
    try:
        return parent.find_element(By.CSS_SELECTOR, selector).text.strip()
    except Exception:
        return ""


def attr_or_empty(parent, selector, attr):
    try:
        value = parent.find_element(By.CSS_SELECTOR, selector).get_attribute(attr)
        return value.strip() if value else ""
    except Exception:
        return ""


def normalize_spaces(text):
    return " ".join(text.split()).strip()


def split_name_and_count(text):
    cleaned = normalize_spaces(text)
    cleaned = re.sub(r"Apply\s+.*?filter$", "", cleaned, flags=re.IGNORECASE).strip()
    match = re.match(r"^(.*?)(?:\s*\((\d+)\))?$", cleaned)
    if not match:
        return cleaned, ""
    return match.group(1).strip(), match.group(2) or ""


def get_category_links(driver, wait):
    driver.get(SEARCH_URL)
    wait.until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "ul.facetapi-terms.facetapi-facet-field-topic li a")
        )
    )

    categories = []
    items = driver.find_elements(
        By.CSS_SELECTOR, "ul.facetapi-terms.facetapi-facet-field-topic li a"
    )

    for item in items:
        raw_text = item.text.strip()
        name, _ = split_name_and_count(raw_text)
        href = urljoin(BASE_URL, item.get_attribute("href"))
        categories.append({"categoria": name, "link": href})

    return categories


def build_paginated_url(url, page_index):
    if page_index == 0:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}page=0%2C{page_index}"


def is_dataset_article(article):
    try:
        article.find_element(By.CSS_SELECTOR, "div.search-result.search-result-dataset")
        return True
    except Exception:
        return False


def is_dataset_url(url):
    path = urlparse(url).path.rstrip("/")
    return "/dataset/" in path and "/resource/" not in path


def extract_dataset_links_from_page(driver, categoria):
    datasets = []
    articles = driver.find_elements(By.CSS_SELECTOR, "article.node-search-result")

    for article in articles:
        if not is_dataset_article(article):
            continue

        title = text_or_empty(article, "h2.node-title a")
        relative_link = attr_or_empty(article, "h2.node-title a", "href")
        link = urljoin(BASE_URL, relative_link)

        if not link or not is_dataset_url(link):
            continue

        datasets.append(
            {
                "titulo": title,
                "categoria": categoria,
                "link": link,
            }
        )

    return datasets


def scrape_category_dataset_links(driver, wait, category_info):
    categoria = category_info["categoria"]
    base_url = category_info["link"]
    dataset_rows = []
    seen_links = set()
    page_index = 0

    while True:
        page_url = build_paginated_url(base_url, page_index)
        print(f"Procesando categoria '{categoria}' - pagina {page_index + 1}")
        driver.get(page_url)

        wait.until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "article.node-search-result")
            )
        )

        page_datasets = extract_dataset_links_from_page(driver, categoria)
        if not page_datasets and page_index == 0:
            break

        for dataset in page_datasets:
            if dataset["link"] not in seen_links:
                seen_links.add(dataset["link"])
                dataset_rows.append(dataset)

        next_buttons = driver.find_elements(By.CSS_SELECTOR, "li.pager-next a")
        if not next_buttons:
            break

        page_index += 1

    return dataset_rows


def normalize_label(text):
    lowered = normalize_spaces(text).lower()
    lowered = lowered.replace(":", "")
    return lowered


def get_table_value(driver, possible_labels):
    possible_labels = [normalize_label(label) for label in possible_labels]

    rows = driver.find_elements(
        By.CSS_SELECTOR, "section.group_additional table.field-group-format tr"
    )
    for row in rows:
        cells = row.find_elements(By.CSS_SELECTOR, "th, td")
        if len(cells) < 2:
            continue

        label = normalize_label(cells[0].text)
        if any(option in label for option in possible_labels):
            return normalize_spaces(cells[1].text)

    return ""


def count_csv_json_resources(driver):
    count = 0
    resource_formats = driver.find_elements(
        By.CSS_SELECTOR, "#data-and-resources [data-format]"
    )

    for item in resource_formats:
        fmt = (item.get_attribute("data-format") or "").strip().lower()
        if fmt in {"csv", "json","xls", ".xls"}:
            count += 1

    return count


def extract_dataset_detail(driver, wait, dataset_info):
    print(f"Analizando dataset: {dataset_info['titulo']}")
    driver.get(dataset_info["link"])

    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

    try:
        wait.until(
            EC.presence_of_all_elements_located(
                (
                    By.CSS_SELECTOR,
                    "section.group_additional table.field-group-format tr",
                )
            )
        )
    except TimeoutException:
        pass

    entidad = get_table_value(
        driver,
        [
            "publisher",
            "publicador",
            "entidad",
            "organization",
        ],
    )
    fecha = get_table_value(
        driver,
        [
            "fecha modificada",
            "modified",
            "fecha de modificacion",
            "last updated",
            "updated",
        ],
    )
    total_archivos = count_csv_json_resources(driver)

    return {
        "titulo": dataset_info["titulo"],
        "categoria": dataset_info["categoria"],
        "numero_datasets_asociados": total_archivos,
        "fecha_ultima_actualizacion": fecha,
        "entidad_responsable": entidad,
    }


def main():
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    wait = WebDriverWait(driver, WAIT_SECONDS)

    try:
        categories = get_category_links(driver, wait)
        dataset_index = []

        for category_info in categories:
            dataset_index.extend(
                scrape_category_dataset_links(driver, wait, category_info)
            )

        all_rows = []
        for dataset_info in dataset_index:
            all_rows.append(extract_dataset_detail(driver, wait, dataset_info))

        df = pd.DataFrame(
            all_rows,
            columns=[
                "titulo",
                "categoria",
                "numero_datasets_asociados",
                "fecha_ultima_actualizacion",
                "entidad_responsable",
            ],
        )
        df.to_excel(OUTPUT_FILE, index=False)

        print(f"Archivo generado: {OUTPUT_FILE}")
        print(f"Datasets analizados: {len(df)}")
        print(f"Categorias procesadas: {len(categories)}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
