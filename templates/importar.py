import os
import oracledb
import pandas as pd
from datetime import datetime


def load_csv(csv_path):
    # El CSV no tiene cabecera, tiene 4 columnas: TEXTO1, TEXTO2, FECHA, MSISDN
    df = pd.read_csv(csv_path, header=None, names=["TEXTO1", "TEXTO2", "FECHA", "MSISDN"], dtype=str)
    # Parsear la fecha con formato día/mes/año
    df["FECHA"] = pd.to_datetime(df["FECHA"], dayfirst=True, errors="coerce")
    # Convertir FECHA a objeto date de Python (si se necesita)
    df["FECHA"] = df["FECHA"].dt.date
    # Limpiar MSISDN (quitar espacios) y mantener como string
    df["MSISDN"] = df["MSISDN"].str.strip()
    return df


def insert_into_db(df, user, password, dsn):
    sql = "INSERT INTO TMP_CMO (TEXTO1, TEXTO2, FECHA, MSISDN) VALUES (:1, :2, :3, :4)"
    # Seleccionar y convertir a lista de tuplas en el orden correcto
    data_to_insert = list(df[["TEXTO1", "TEXTO2", "FECHA", "MSISDN"]].itertuples(index=False, name=None))

    connection = None
    cursor = None
    try:
        connection = oracledb.connect(user=user, password=password, dsn=dsn)
        cursor = connection.cursor()
        cursor.executemany(sql, data_to_insert)
        connection.commit()
        print(f"Insertadas {cursor.rowcount} filas en TMP_CMO")
    except oracledb.Error as error:
        print(f"Error al insertar datos: {error}")
        raise
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


if __name__ == "__main__":
    # Ruta del CSV relativa al archivo actual
    base_dir = os.path.dirname(__file__)
    csv_files = ["BasePlmntplid.csv", "BaseWificalling.csv"]

    frames = []
    for csv_file in csv_files:
        csv_path = os.path.join(base_dir, csv_file)
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"No se encontró el CSV en {csv_path}")
        df_part = load_csv(csv_path)
        print(f"Cargadas {len(df_part)} filas desde {csv_file}")
        frames.append(df_part)

    df = pd.concat(frames, ignore_index=True)
    print(f"Total combinado: {len(df)} filas")

    # Parámetros de conexión (ajusta si es necesario)
    DB_USER = "SYSADM"
    DB_PASSWORD = "SYSADM"
    DB_DSN = "10.101.115.24:1521/EBSBSB2B_PSB_EBSCSB2B.paas.oracle.com"

    insert_into_db(df, DB_USER, DB_PASSWORD, DB_DSN)