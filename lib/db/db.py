import os
from typing import Dict, List

import psycopg2
from apscheduler.triggers.cron import CronTrigger

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


def field(command, *values):
    """
    Returns the first element from fetchone() method
    """
    cursor.execute(command, tuple(values))

    if (fetch := cursor.fetchone()) is not None:
        return fetch[0]


def column(command, *values):
    """
    Returns the first element from fetchall() method
    """
    cursor.execute(command, tuple(values))

    return [item[0] for item in cursor.fetchall()]


def execute(command, *values):
    """
    Executes a SQL query
    """
    cursor.execute(command, tuple(values))


def get_cursor():
    """
    Returns a DB connection cursor
    """
    return cursor


def commit():
    """
    Makes commit into DB
    """
    conn.commit()

def autosave(sched):
    """
    Scheduled method that makes commit to DB every 60 seconds
    """
    sched.add_job(commit, CronTrigger(second=0))

def close():
    """
    Closes DB cursor
    :return:
    """
    conn.close()


def scriptexec(path):
    """
    Executes a SQL script to build DB
    """
    with open(path, "r", encoding="utf-8") as script:
        cursor.executescript(script.read())
        conn.commit()
