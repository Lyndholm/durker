from typing import Any, Dict, List, Tuple

import asyncpg


class DatabaseWrapper():
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def insert(self, table: str, column_values: Dict) -> None:
        """
        Adds data to the database
        """
        columns = ', '.join(column_values.keys())
        values = [tuple(column_values.values())]
        placeholders = [f'${i}' for i, _ in enumerate(column_values.keys(), 1)]
        placeholders = ', '.join(placeholders)
        await self.pool.executemany(
            f'INSERT INTO {table} '
            f'({columns}) '
            f'VALUES ({placeholders})',
            values)

    async def fetchall(self, columns: List[str], table: str) -> Dict[Any, Any]:
        """
        Returns a list of dicts with fetched data
        """
        columns_joined = ", ".join(columns)
        data = await self.pool.fetch(
            f'SELECT {columns_joined} '
            f'FROM {table}')

        result = []
        for i in data:
            dict_row = {}
            for key, value in i.values():
                dict_row[key] = value
            result.append(dict_row)

        return result

    async def fetchone(self, columns: List[str], table: str, param: str, param_value: Any) -> Tuple[Any]:
        """
        Returns a tuple with fetched data
        """
        columns_joined = ', '.join(columns)
        data = await self.pool.fetchrow(
            f'SELECT {columns_joined} '
            f'FROM {table} '
            f'WHERE {param} = {param_value}')
        result = tuple(data)

        return result

    async def field(self, query: str, *values) -> Any:
        """
        Returns the first element from fetchone() method
        """
        data = await self.pool.fetchrow(query, *tuple(values))
        data = tuple(data)

        return data[0]

    async def record(self, query: str, *values) -> Tuple:
        """
        Returns record from fetchone() method
        """
        data = await self.pool.fetchrow(query, *tuple(values))
        data = tuple(data)

        return data

    async def records(self, query: str, *values) -> List:
        """
        Returns records from fetchall() method
        """
        data = await self.pool.fetch(query, *tuple(values))
        data = [tuple(record) for record in data]

        return data
