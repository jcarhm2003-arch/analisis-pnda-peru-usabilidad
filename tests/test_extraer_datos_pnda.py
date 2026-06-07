"""Unit tests for extraer_datos_pnda.py"""

from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from extraer_datos_pnda import (
    attr_or_empty,
    build_paginated_url,
    count_csv_json_resources,
    extract_dataset_detail,
    extract_dataset_links_from_page,
    get_category_links,
    get_table_value,
    is_dataset_article,
    is_dataset_url,
    main,
    normalize_label,
    normalize_spaces,
    scrape_category_dataset_links,
    split_name_and_count,
    text_or_empty,
)


# ---------------------------------------------------------------------------
# normalize_spaces
# ---------------------------------------------------------------------------
class TestNormalizeSpaces:
    def test_basic(self):
        assert normalize_spaces("  hello   world  ") == "hello world"

    def test_tabs_and_newlines(self):
        assert normalize_spaces("hello\t\n  world") == "hello world"

    def test_already_clean(self):
        assert normalize_spaces("hello world") == "hello world"

    def test_empty(self):
        assert normalize_spaces("") == ""

    def test_only_whitespace(self):
        assert normalize_spaces("   ") == ""

    def test_single_word(self):
        assert normalize_spaces("  word  ") == "word"


# ---------------------------------------------------------------------------
# split_name_and_count
# ---------------------------------------------------------------------------
class TestSplitNameAndCount:
    def test_name_with_count(self):
        assert split_name_and_count("Economia (15)") == ("Economia", "15")

    def test_name_without_count(self):
        assert split_name_and_count("Salud") == ("Salud", "")

    def test_name_with_extra_whitespace(self):
        assert split_name_and_count("  Ciencia  (3)  ") == ("Ciencia", "3")

    def test_strips_apply_filter_suffix(self):
        name, count = split_name_and_count("Agricultura (7) Apply Agricultura filter")
        assert name == "Agricultura"
        assert count == "7"

    def test_no_count_no_filter(self):
        assert split_name_and_count("Transporte") == ("Transporte", "")

    def test_empty_string(self):
        assert split_name_and_count("") == ("", "")

    def test_count_zero(self):
        assert split_name_and_count("Vacio (0)") == ("Vacio", "0")


# ---------------------------------------------------------------------------
# build_paginated_url
# ---------------------------------------------------------------------------
class TestBuildPaginatedUrl:
    def test_first_page(self):
        url = "https://example.com/search?query=test"
        assert build_paginated_url(url, 0) == url

    def test_second_page_with_query(self):
        url = "https://example.com/search?query=test"
        result = build_paginated_url(url, 1)
        assert result == "https://example.com/search?query=test&page=0%2C1"

    def test_second_page_without_query(self):
        url = "https://example.com/search"
        result = build_paginated_url(url, 1)
        assert result == "https://example.com/search?page=0%2C1"

    def test_page_five(self):
        url = "https://example.com/search?q=a"
        result = build_paginated_url(url, 5)
        assert result == "https://example.com/search?q=a&page=0%2C5"


# ---------------------------------------------------------------------------
# is_dataset_url
# ---------------------------------------------------------------------------
class TestIsDatasetUrl:
    def test_valid_dataset_url(self):
        assert is_dataset_url("https://www.datosabiertos.gob.pe/dataset/covid-19") is True

    def test_resource_url(self):
        assert is_dataset_url("https://www.datosabiertos.gob.pe/dataset/covid-19/resource/abc") is False

    def test_non_dataset_url(self):
        assert is_dataset_url("https://www.datosabiertos.gob.pe/search") is False

    def test_trailing_slash(self):
        assert is_dataset_url("https://www.datosabiertos.gob.pe/dataset/test/") is True

    def test_empty_string(self):
        assert is_dataset_url("") is False


# ---------------------------------------------------------------------------
# normalize_label
# ---------------------------------------------------------------------------
class TestNormalizeLabel:
    def test_basic(self):
        assert normalize_label("Publisher:") == "publisher"

    def test_extra_whitespace(self):
        assert normalize_label("  Fecha  Modificada:  ") == "fecha modificada"

    def test_no_colon(self):
        assert normalize_label("entidad") == "entidad"

    def test_uppercase(self):
        assert normalize_label("MODIFIED:") == "modified"

    def test_empty(self):
        assert normalize_label("") == ""


# ---------------------------------------------------------------------------
# text_or_empty
# ---------------------------------------------------------------------------
class TestTextOrEmpty:
    def test_element_found(self):
        child = MagicMock()
        child.text = "  some text  "
        parent = MagicMock()
        parent.find_element.return_value = child
        assert text_or_empty(parent, "h2.title") == "some text"

    def test_element_not_found(self):
        parent = MagicMock()
        parent.find_element.side_effect = Exception("not found")
        assert text_or_empty(parent, "h2.title") == ""


# ---------------------------------------------------------------------------
# attr_or_empty
# ---------------------------------------------------------------------------
class TestAttrOrEmpty:
    def test_attribute_found(self):
        child = MagicMock()
        child.get_attribute.return_value = "  /some/path  "
        parent = MagicMock()
        parent.find_element.return_value = child
        assert attr_or_empty(parent, "a.link", "href") == "/some/path"

    def test_attribute_none(self):
        child = MagicMock()
        child.get_attribute.return_value = None
        parent = MagicMock()
        parent.find_element.return_value = child
        assert attr_or_empty(parent, "a.link", "href") == ""

    def test_element_not_found(self):
        parent = MagicMock()
        parent.find_element.side_effect = Exception("not found")
        assert attr_or_empty(parent, "a.link", "href") == ""


# ---------------------------------------------------------------------------
# is_dataset_article
# ---------------------------------------------------------------------------
class TestIsDatasetArticle:
    def test_is_dataset(self):
        article = MagicMock()
        article.find_element.return_value = MagicMock()
        assert is_dataset_article(article) is True

    def test_is_not_dataset(self):
        article = MagicMock()
        article.find_element.side_effect = Exception("not found")
        assert is_dataset_article(article) is False


# ---------------------------------------------------------------------------
# count_csv_json_resources
# ---------------------------------------------------------------------------
class TestCountCsvJsonResources:
    def _make_format_element(self, fmt):
        el = MagicMock()
        el.get_attribute.return_value = fmt
        return el

    def test_counts_csv_and_json(self):
        driver = MagicMock()
        driver.find_elements.return_value = [
            self._make_format_element("csv"),
            self._make_format_element("json"),
            self._make_format_element("pdf"),
        ]
        assert count_csv_json_resources(driver) == 2

    def test_counts_xls_formats(self):
        driver = MagicMock()
        driver.find_elements.return_value = [
            self._make_format_element("xls"),
            self._make_format_element(".xls"),
        ]
        assert count_csv_json_resources(driver) == 2

    def test_no_matching_formats(self):
        driver = MagicMock()
        driver.find_elements.return_value = [
            self._make_format_element("pdf"),
            self._make_format_element("docx"),
        ]
        assert count_csv_json_resources(driver) == 0

    def test_empty_list(self):
        driver = MagicMock()
        driver.find_elements.return_value = []
        assert count_csv_json_resources(driver) == 0

    def test_none_format_attribute(self):
        driver = MagicMock()
        el = MagicMock()
        el.get_attribute.return_value = None
        driver.find_elements.return_value = [el]
        assert count_csv_json_resources(driver) == 0

    def test_case_insensitive(self):
        driver = MagicMock()
        driver.find_elements.return_value = [
            self._make_format_element("CSV"),
            self._make_format_element("JSON"),
        ]
        assert count_csv_json_resources(driver) == 2


# ---------------------------------------------------------------------------
# get_table_value
# ---------------------------------------------------------------------------
class TestGetTableValue:
    def _make_row(self, label, value):
        th = MagicMock()
        th.text = label
        td = MagicMock()
        td.text = value
        row = MagicMock()
        row.find_elements.return_value = [th, td]
        return row

    def test_finds_matching_label(self):
        driver = MagicMock()
        driver.find_elements.return_value = [
            self._make_row("Publisher:", "INEI"),
            self._make_row("Modified:", "2024-01-01"),
        ]
        result = get_table_value(driver, ["publisher"])
        assert result == "INEI"

    def test_no_matching_label(self):
        driver = MagicMock()
        driver.find_elements.return_value = [
            self._make_row("Autor:", "Juan"),
        ]
        result = get_table_value(driver, ["publisher"])
        assert result == ""

    def test_empty_table(self):
        driver = MagicMock()
        driver.find_elements.return_value = []
        assert get_table_value(driver, ["publisher"]) == ""

    def test_row_with_single_cell_skipped(self):
        row = MagicMock()
        single_cell = MagicMock()
        single_cell.text = "header only"
        row.find_elements.return_value = [single_cell]

        driver = MagicMock()
        driver.find_elements.return_value = [row]
        assert get_table_value(driver, ["publisher"]) == ""

    def test_multiple_possible_labels(self):
        driver = MagicMock()
        driver.find_elements.return_value = [
            self._make_row("Entidad:", "SUNAT"),
        ]
        result = get_table_value(driver, ["publisher", "entidad"])
        assert result == "SUNAT"


# ---------------------------------------------------------------------------
# extract_dataset_links_from_page
# ---------------------------------------------------------------------------
class TestExtractDatasetLinksFromPage:
    def _make_article(self, is_dataset, title, href):
        article = MagicMock()

        if is_dataset:
            article.find_element.return_value = MagicMock()
        else:
            def side_effect(by, selector):
                if "search-result-dataset" in selector:
                    raise Exception("not dataset")
                child = MagicMock()
                child.text = title
                child.get_attribute.return_value = href
                return child
            article.find_element.side_effect = side_effect

        title_el = MagicMock()
        title_el.text = f"  {title}  "
        href_el = MagicMock()
        href_el.text = f"  {title}  "
        href_el.get_attribute.return_value = href

        def find_element_side_effect(by, selector):
            if "search-result-dataset" in selector:
                if not is_dataset:
                    raise Exception("not dataset")
                return MagicMock()
            return href_el

        article.find_element.side_effect = find_element_side_effect
        return article

    def test_extracts_dataset_links(self):
        article = MagicMock()

        def find_element_side_effect(by, selector):
            if "search-result-dataset" in selector:
                return MagicMock()
            el = MagicMock()
            el.text = "Test Dataset"
            el.get_attribute.return_value = "/dataset/test-dataset"
            return el

        article.find_element.side_effect = find_element_side_effect

        driver = MagicMock()
        driver.find_elements.return_value = [article]

        results = extract_dataset_links_from_page(driver, "Economia")
        assert len(results) == 1
        assert results[0]["titulo"] == "Test Dataset"
        assert results[0]["categoria"] == "Economia"
        assert "dataset/test-dataset" in results[0]["link"]

    def test_skips_non_dataset_articles(self):
        article = MagicMock()
        article.find_element.side_effect = Exception("not dataset")

        driver = MagicMock()
        driver.find_elements.return_value = [article]

        results = extract_dataset_links_from_page(driver, "Economia")
        assert len(results) == 0

    def test_skips_resource_urls(self):
        article = MagicMock()

        def find_element_side_effect(by, selector):
            if "search-result-dataset" in selector:
                return MagicMock()
            el = MagicMock()
            el.text = "Resource"
            el.get_attribute.return_value = "/dataset/test/resource/abc"
            return el

        article.find_element.side_effect = find_element_side_effect

        driver = MagicMock()
        driver.find_elements.return_value = [article]

        results = extract_dataset_links_from_page(driver, "Economia")
        assert len(results) == 0

    def test_empty_page(self):
        driver = MagicMock()
        driver.find_elements.return_value = []
        results = extract_dataset_links_from_page(driver, "Economia")
        assert results == []


# ---------------------------------------------------------------------------
# get_category_links
# ---------------------------------------------------------------------------
class TestGetCategoryLinks:
    def test_returns_categories(self):
        link1 = MagicMock()
        link1.text = "Economia (15)"
        link1.get_attribute.return_value = "/search?f[0]=field_topic%3A123"

        link2 = MagicMock()
        link2.text = "Salud (8)"
        link2.get_attribute.return_value = "/search?f[0]=field_topic%3A456"

        driver = MagicMock()
        driver.find_elements.return_value = [link1, link2]
        wait = MagicMock()

        results = get_category_links(driver, wait)
        assert len(results) == 2
        assert results[0]["categoria"] == "Economia"
        assert results[1]["categoria"] == "Salud"
        assert "datosabiertos.gob.pe" in results[0]["link"]

    def test_empty_categories(self):
        driver = MagicMock()
        driver.find_elements.return_value = []
        wait = MagicMock()

        results = get_category_links(driver, wait)
        assert results == []


# ---------------------------------------------------------------------------
# scrape_category_dataset_links
# ---------------------------------------------------------------------------
class TestScrapeCategoryDatasetLinks:
    def test_single_page_no_next(self):
        article = MagicMock()

        def find_el(by, selector):
            if "search-result-dataset" in selector:
                return MagicMock()
            el = MagicMock()
            el.text = "Dataset A"
            el.get_attribute.return_value = "/dataset/a"
            return el

        article.find_element.side_effect = find_el

        driver = MagicMock()

        def find_elements_side_effect(by, selector):
            if "article" in selector:
                return [article]
            if "pager-next" in selector:
                return []
            return []

        driver.find_elements.side_effect = find_elements_side_effect
        wait = MagicMock()

        category_info = {"categoria": "Economia", "link": "https://example.com/search?q=econ"}
        results = scrape_category_dataset_links(driver, wait, category_info)
        assert len(results) == 1
        assert results[0]["titulo"] == "Dataset A"

    def test_empty_first_page(self):
        driver = MagicMock()

        def find_elements_side_effect(by, selector):
            if "article" in selector:
                return []
            return []

        driver.find_elements.side_effect = find_elements_side_effect
        wait = MagicMock()

        category_info = {"categoria": "Vacio", "link": "https://example.com/search?q=vacio"}
        results = scrape_category_dataset_links(driver, wait, category_info)
        assert results == []

    def test_deduplicates_links(self):
        def make_article(title, href):
            art = MagicMock()

            def find_el(by, selector):
                if "search-result-dataset" in selector:
                    return MagicMock()
                el = MagicMock()
                el.text = title
                el.get_attribute.return_value = href
                return el

            art.find_element.side_effect = find_el
            return art

        article1 = make_article("Dataset A", "/dataset/a")
        article2 = make_article("Dataset A dup", "/dataset/a")

        call_count = [0]
        driver = MagicMock()

        def find_elements_side_effect(by, selector):
            if "article" in selector:
                call_count[0] += 1
                if call_count[0] == 1:
                    return [article1, article2]
                return []
            if "pager-next" in selector:
                return []
            return []

        driver.find_elements.side_effect = find_elements_side_effect
        wait = MagicMock()

        category_info = {"categoria": "Test", "link": "https://example.com/search"}
        results = scrape_category_dataset_links(driver, wait, category_info)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# extract_dataset_detail
# ---------------------------------------------------------------------------
class TestExtractDatasetDetail:
    def test_extracts_detail(self):
        driver = MagicMock()
        wait = MagicMock()

        def make_row(label, value):
            th = MagicMock()
            th.text = label
            td = MagicMock()
            td.text = value
            row = MagicMock()
            row.find_elements.return_value = [th, td]
            return row

        rows = [
            make_row("Publisher:", "INEI"),
            make_row("Modified:", "2024-06-01"),
        ]

        format_el = MagicMock()
        format_el.get_attribute.return_value = "csv"

        def find_elements_side_effect(by, selector):
            if "table" in selector:
                return rows
            if "data-format" in selector:
                return [format_el]
            return []

        driver.find_elements.side_effect = find_elements_side_effect

        dataset_info = {
            "titulo": "COVID-19",
            "categoria": "Salud",
            "link": "https://www.datosabiertos.gob.pe/dataset/covid-19",
        }

        result = extract_dataset_detail(driver, wait, dataset_info)
        assert result["titulo"] == "COVID-19"
        assert result["categoria"] == "Salud"
        assert result["entidad_responsable"] == "INEI"
        assert result["fecha_ultima_actualizacion"] == "2024-06-01"
        assert result["numero_datasets_asociados"] == 1

    def test_handles_timeout(self):
        from selenium.common.exceptions import TimeoutException

        driver = MagicMock()
        wait = MagicMock()

        # First wait succeeds (body), second raises TimeoutException
        wait.until.side_effect = [None, TimeoutException("timeout")]

        driver.find_elements.return_value = []

        dataset_info = {
            "titulo": "Missing",
            "categoria": "Unknown",
            "link": "https://www.datosabiertos.gob.pe/dataset/missing",
        }

        result = extract_dataset_detail(driver, wait, dataset_info)
        assert result["titulo"] == "Missing"
        assert result["entidad_responsable"] == ""
        assert result["fecha_ultima_actualizacion"] == ""
        assert result["numero_datasets_asociados"] == 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
class TestMain:
    @patch("extraer_datos_pnda.webdriver")
    @patch("extraer_datos_pnda.WebDriverWait")
    @patch("extraer_datos_pnda.Service")
    @patch("extraer_datos_pnda.ChromeDriverManager")
    def test_main_flow(self, mock_cdm, mock_service, mock_wait_cls, mock_webdriver):
        mock_driver = MagicMock()
        mock_webdriver.Chrome.return_value = mock_driver
        mock_wait = MagicMock()
        mock_wait_cls.return_value = mock_wait

        # get_category_links: return one category
        cat_link = MagicMock()
        cat_link.text = "Economia (5)"
        cat_link.get_attribute.return_value = "/search?f[0]=field_topic%3A1"

        # scrape_category_dataset_links: article on page
        article = MagicMock()

        def find_el(by, selector):
            if "search-result-dataset" in selector:
                return MagicMock()
            el = MagicMock()
            el.text = "Dataset X"
            el.get_attribute.return_value = "/dataset/x"
            return el

        article.find_element.side_effect = find_el

        # extract_dataset_detail: table rows
        def make_row(label, value):
            th = MagicMock()
            th.text = label
            td = MagicMock()
            td.text = value
            row = MagicMock()
            row.find_elements.return_value = [th, td]
            return row

        detail_rows = [
            make_row("Publisher:", "INEI"),
            make_row("Modified:", "2024-01-01"),
        ]

        fmt_el = MagicMock()
        fmt_el.get_attribute.return_value = "csv"

        call_index = [0]

        def find_elements_side_effect(by, selector):
            call_index[0] += 1
            # category links
            if "facetapi" in selector:
                return [cat_link]
            # articles for scraping
            if "article" in selector:
                return [article]
            # pager-next
            if "pager-next" in selector:
                return []
            # table rows
            if "table" in selector:
                return detail_rows
            # data-format
            if "data-format" in selector:
                return [fmt_el]
            return []

        mock_driver.find_elements.side_effect = find_elements_side_effect

        with patch("extraer_datos_pnda.pd.DataFrame") as mock_df_cls:
            mock_df = MagicMock()
            mock_df_cls.return_value = mock_df

            main()

            mock_df.to_excel.assert_called_once()
            mock_driver.quit.assert_called_once()
