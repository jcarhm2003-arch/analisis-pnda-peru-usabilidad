import pandas as pd

from pnda.browser import create_driver
from pnda.config import OUTPUT_FILE
from pnda.scraper import (
    extract_dataset_detail,
    get_category_links,
    scrape_category_dataset_links,
)


def main():
    driver, wait = create_driver()

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
