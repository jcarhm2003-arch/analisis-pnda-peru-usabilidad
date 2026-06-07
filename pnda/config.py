BASE_URL = "https://www.datosabiertos.gob.pe"
SEARCH_URL = f"{BASE_URL}/search?query=&sort_by=changed&sort_order=DESC"
OUTPUT_FILE = "entregable1.xlsx"
WAIT_SECONDS = 20

CATEGORY_LIST_SELECTOR = "ul.facetapi-terms.facetapi-facet-field-topic li a"
SEARCH_RESULT_SELECTOR = "article.node-search-result"
DATASET_MARKER_SELECTOR = "div.search-result.search-result-dataset"
ADDITIONAL_INFO_SELECTOR = "section.group_additional table.field-group-format tr"
RESOURCE_FORMAT_SELECTOR = "#data-and-resources [data-format]"
PAGER_NEXT_SELECTOR = "li.pager-next a"
TITLE_LINK_SELECTOR = "h2.node-title a"

VALID_RESOURCE_FORMATS = {"csv", "json", "xls", ".xls"}

PUBLISHER_LABELS = ["publisher", "publicador", "entidad", "organization"]
DATE_LABELS = [
    "fecha modificada",
    "modified",
    "fecha de modificacion",
    "last updated",
    "updated",
]
