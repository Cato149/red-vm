import logging
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator

import asyncpg
from asyncpg.pool import Pool

from db.uow import UnitOfWork
import core.log_cfg
logger = logging.getLogger(__name__)


class DatabaseConnection:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[Pool] = None

    async def connect(self) -> Pool:
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.dsn)
            async with self.pool.acquire() as conn:
                await self._create_tables(conn)
        return self.pool

    async def disconnect(self) -> None:
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def _create_tables(self, conn) -> None:
        vm_stmt = """
        CREATE TABLE IF NOT EXISTS virtual_machines (
            id SERIAL PRIMARY KEY,
            ram INTEGER NOT NULL,
            cpu INTEGER NOT NULL,
            is_connected BOOLEAN DEFAULT FALSE,
            last_connected TIMESTAMP NULL
        );

        CREATE TABLE IF NOT EXISTS hard_drives (
            id SERIAL PRIMARY KEY,
            vm_id INTEGER REFERENCES virtual_machines ON DELETE CASCADE,
            size INTEGER NOT NULL
        );
        """
        await conn.execute(vm_stmt)
        logger.info("tables created")

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[UnitOfWork, None]:
        if not self.pool:
            logger.error("Not connected to database")
            raise RuntimeError("Not connected to database")

        async with self.pool.acquire() as connection:
            uow = UnitOfWork(connection)
            async with uow as unit:
                yield unit
