"""
Procesador de Estados de Cuenta del BCP (Perú).

Extrae todos los movimientos y registros de PDFs protegidos con contraseña,
sin clasificar ni filtrar. Genera un CSV crudo (movimientos_raw.csv) con
toda la información encontrada en los estados de cuenta.
"""

import csv
import hashlib
import re
import tempfile
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
CARPETA_PDF = Path(".")           # Carpeta donde están los PDFs
ARCHIVO_HASHES = Path("procesados.txt")
ARCHIVO_CSV = Path("movimientos_raw.csv")
PASSWORD = "62022248"

# ---------------------------------------------------------------------------
# Patrones de expresiones regulares para líneas del estado de cuenta BCP
# ---------------------------------------------------------------------------

# Fecha dd/mm o dd/mm/aaaa
_FECHA = r"\d{2}/\d{2}(?:/\d{2,4})?"

# Monto con separador de miles (punto) y decimales (coma) — formato peruano
# Ejemplos: 1.234,56  o  234,56  o  0,50
_MONTO = r"-?[\d]+(?:[.,]\d{2,3})*(?:[.,]\d{2})"

# Movimiento con dos fechas + descripción + monto
RE_MOV_DOS_FECHAS = re.compile(
    rf"^({_FECHA})\s+({_FECHA})\s+(.+?)\s+({_MONTO})\s*$"
)

# Movimiento con una sola fecha + descripción + monto
RE_MOV_UNA_FECHA = re.compile(
    rf"^({_FECHA})\s+(.+?)\s+({_MONTO})\s*$"
)

# Línea que solo tiene descripción + monto (sin fecha)
RE_DESC_MONTO = re.compile(
    rf"^(.+?)\s+({_MONTO})\s*$"
)

# Registros especiales (saldo anterior, saldo final, totales, etc.)
RE_SALDO_ANTERIOR = re.compile(
    r"(?i)^(.*SALDO\s+ANTERIOR.*?)\s+({monto})\s*$".format(monto=_MONTO)
)
RE_SALDO_FINAL = re.compile(
    r"(?i)^(.*SALDO\s+FINAL.*?)\s+({monto})\s*$".format(monto=_MONTO)
)
RE_SALDO = re.compile(
    r"(?i)^(SALDO\b.*?)\s+({monto})\s*$".format(monto=_MONTO)
)
RE_TOTAL_MOVIMIENTO = re.compile(
    r"(?i)^(.*TOTAL\s+MOVIMIENT.*?)\s+({monto})\s*$".format(monto=_MONTO)
)

# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def calcular_md5(ruta: Path) -> str:
    """Calcula el hash MD5 de un archivo."""
    h = hashlib.md5()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(8192), b""):
            h.update(bloque)
    return h.hexdigest()


def cargar_hashes_procesados() -> set[str]:
    """Lee los hashes ya procesados desde procesados.txt."""
    if not ARCHIVO_HASHES.exists():
        return set()
    with open(ARCHIVO_HASHES, "r", encoding="utf-8") as f:
        return {linea.strip() for linea in f if linea.strip()}


def guardar_hash(hash_md5: str) -> None:
    """Agrega un hash al archivo de control."""
    with open(ARCHIVO_HASHES, "a", encoding="utf-8") as f:
        f.write(hash_md5 + "\n")


def limpiar_pdf(ruta: Path) -> Path:
    """
    Algunos PDFs del BCP tienen datos basura antes del encabezado %PDF.
    Localiza el marcador real y devuelve una ruta temporal limpia.
    Si el PDF ya está limpio, devuelve la ruta original.
    """
    with open(ruta, "rb") as f:
        contenido = f.read()

    idx = contenido.find(b"%PDF")
    if idx == 0:
        return ruta  # ya está limpio
    if idx < 0:
        raise ValueError(f"No se encontró encabezado %PDF en {ruta.name}")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(contenido[idx:])
    tmp.close()
    return Path(tmp.name)


def normalizar_monto(texto: str) -> str:
    """
    Devuelve el monto tal cual aparece en el PDF, sin interpretar signo.
    Solo limpia espacios.
    """
    return texto.strip()


# ---------------------------------------------------------------------------
# Clasificación de líneas
# ---------------------------------------------------------------------------


def clasificar_linea(linea: str) -> dict | None:
    """
    Intenta clasificar una línea del texto extraído del PDF.
    Retorna un dict con las columnas requeridas o None si la línea está vacía.
    """
    linea = linea.strip()
    if not linea:
        return None

    # --- Registros especiales (se evalúan primero) ---

    m = RE_SALDO_ANTERIOR.match(linea)
    if m:
        return {
            "fecha_proc": "",
            "fecha_valor": "",
            "descripcion": m.group(1).strip(),
            "monto": normalizar_monto(m.group(2)),
            "tipo_registro": "SALDO_ANTERIOR",
        }

    m = RE_SALDO_FINAL.match(linea)
    if m:
        return {
            "fecha_proc": "",
            "fecha_valor": "",
            "descripcion": m.group(1).strip(),
            "monto": normalizar_monto(m.group(2)),
            "tipo_registro": "SALDO_FINAL",
        }

    m = RE_TOTAL_MOVIMIENTO.match(linea)
    if m:
        return {
            "fecha_proc": "",
            "fecha_valor": "",
            "descripcion": m.group(1).strip(),
            "monto": normalizar_monto(m.group(2)),
            "tipo_registro": "TOTAL_MOVIMIENTO",
        }

    m = RE_SALDO.match(linea)
    if m:
        return {
            "fecha_proc": "",
            "fecha_valor": "",
            "descripcion": m.group(1).strip(),
            "monto": normalizar_monto(m.group(2)),
            "tipo_registro": "SALDO",
        }

    # --- Movimiento con dos fechas ---

    m = RE_MOV_DOS_FECHAS.match(linea)
    if m:
        return {
            "fecha_proc": m.group(1),
            "fecha_valor": m.group(2),
            "descripcion": m.group(3).strip(),
            "monto": normalizar_monto(m.group(4)),
            "tipo_registro": "MOVIMIENTO",
        }

    # --- Movimiento con una fecha ---

    m = RE_MOV_UNA_FECHA.match(linea)
    if m:
        return {
            "fecha_proc": m.group(1),
            "fecha_valor": "",
            "descripcion": m.group(2).strip(),
            "monto": normalizar_monto(m.group(3)),
            "tipo_registro": "MOVIMIENTO",
        }

    # --- Línea con descripción y monto (sin fecha) ---

    m = RE_DESC_MONTO.match(linea)
    if m:
        desc = m.group(1).strip()
        monto = normalizar_monto(m.group(2))
        return {
            "fecha_proc": "",
            "fecha_valor": "",
            "descripcion": desc,
            "monto": monto,
            "tipo_registro": "OTRO",
        }

    # --- Línea sin monto: conservar como OTRO ---

    return {
        "fecha_proc": "",
        "fecha_valor": "",
        "descripcion": linea,
        "monto": "",
        "tipo_registro": "OTRO",
    }


# ---------------------------------------------------------------------------
# Procesamiento de un PDF
# ---------------------------------------------------------------------------


def procesar_pdf(ruta_pdf: Path) -> list[dict]:
    """
    Abre un PDF protegido, extrae el texto de todas las páginas y clasifica
    cada línea. Retorna una lista de dicts (registros).
    """
    ruta_limpia = limpiar_pdf(ruta_pdf)
    try:
        reader = PdfReader(str(ruta_limpia), password=PASSWORD)
    except Exception as e:
        print(f"[ERROR] No se pudo abrir {ruta_pdf.name}: {e}")
        return []

    registros: list[dict] = []

    for num_pagina, pagina in enumerate(reader.pages, start=1):
        texto = pagina.extract_text() or ""
        for linea in texto.split("\n"):
            resultado = clasificar_linea(linea)
            if resultado is None:
                continue
            resultado["archivo_pdf"] = ruta_pdf.name
            resultado["pagina"] = num_pagina
            registros.append(resultado)

    # Limpiar archivo temporal si se creó uno
    if ruta_limpia != ruta_pdf:
        try:
            ruta_limpia.unlink()
        except OSError:
            pass

    return registros


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

COLUMNAS_CSV = [
    "archivo_pdf",
    "pagina",
    "fecha_proc",
    "fecha_valor",
    "descripcion",
    "monto",
    "tipo_registro",
]


def main() -> None:
    # Buscar todos los PDFs en la carpeta
    pdfs = sorted(CARPETA_PDF.glob("*.pdf"), key=lambda p: p.name.upper())
    if not pdfs:
        print("No se encontraron archivos PDF en la carpeta.")
        return

    hashes_previos = cargar_hashes_procesados()
    todos_los_registros: list[dict] = []
    archivos_procesados = 0

    for pdf in pdfs:
        hash_actual = calcular_md5(pdf)
        if hash_actual in hashes_previos:
            print(f"[SALTADO] {pdf.name} (ya procesado)")
            continue

        print(f"[PROCESANDO] {pdf.name}")
        registros = procesar_pdf(pdf)
        print(f"[OK] movimientos encontrados: {len(registros)}")

        todos_los_registros.extend(registros)
        guardar_hash(hash_actual)
        archivos_procesados += 1

    if not todos_los_registros:
        print("\nNo se encontraron registros nuevos para procesar.")
        return

    # Crear DataFrame y guardar CSV
    df = pd.DataFrame(todos_los_registros, columns=COLUMNAS_CSV)

    # Si el CSV ya existe, agregar sin duplicar encabezados
    if ARCHIVO_CSV.exists():
        df_existente = pd.read_csv(ARCHIVO_CSV, dtype=str)
        df = pd.concat([df_existente, df], ignore_index=True)

    df.to_csv(ARCHIVO_CSV, index=False, quoting=csv.QUOTE_ALL, encoding="utf-8-sig")

    print(f"\n{'='*50}")
    print(f"Archivos procesados: {archivos_procesados}")
    print(f"Total registros extraídos: {len(todos_los_registros)}")
    print(f"CSV guardado en: {ARCHIVO_CSV.resolve()}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
