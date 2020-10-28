import os
from typing import Dict, List

import psycopg2

conn = psycopg2.connect(
    dbname=os.environ.get('DB_NAME'),
    user=os.environ.get('DB_USER'),
    password=os.environ.get('DB_PASS'),
    host=os.environ.get('DB_HOST')
)
cursor = conn.cursor()


def insert(table: str, column_values: Dict):
    """
    Adds data to the database
    """
    columns = ', '.join(column_values.keys())
    values = [tuple(column_values.values())]
    placeholders = "%s, " * len(column_values.keys())
    cursor.executemany(
        f"INSERT INTO {table} "
        f"({columns}) "
        f"VALUES ({placeholders[:-2]})",
        values)
    conn.commit()


def fetchall(columns: List[str], table: str):
    """
    Returns a list of tuples with fetched data
    """
    columns_joined = ", ".join(columns)
    cursor.execute(f"SELECT {columns_joined} FROM {table}")
    rows = cursor.fetchall()
    result = []
    for row in rows:
        dict_row = {}
        for index, column in enumerate(columns):
            dict_row[column] = row[index]
        result.append(dict_row)
    return result


def fetchone(columns: List[str], table: str, param: str, param_value) -> tuple:
    """
    Returns a tuple with fetched data
    """
    columns_joined = ", ".join(columns)
    cursor.execute(f"SELECT {columns_joined} FROM {table} WHERE {param} = {param_value}")
    result = cursor.fetchone()

    return result


def delete(table: str, row_id: int) -> None:
    """
    Deletes a row from the database
    """
    row_id = int(row_id)
    cursor.execute(f"delete from {table} where id={row_id}")
    conn.commit()


def get_cursor():
    return cursor
