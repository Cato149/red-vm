import logging
from typing import Optional, Type, Any

from asyncpg.connection import Connection
from asyncpg.transaction import Transaction

from db.repos import VirtualMachineRepository, HardDriveRepository

logger = logging.getLogger(__name__)


class UnitOfWork:
    def __init__(self, connection: Connection):
        self.connection = connection
        self._transaction: Optional[Transaction] = None
        self.vms = VirtualMachineRepository(connection)
        self.drives = HardDriveRepository(connection)

    async def __aenter__(self) -> 'UnitOfWork':
        logger.debug("Starting UnitOfWork transaction")
        self._transaction = self.connection.transaction()
        await self._transaction.start()
        return self

    async def __aexit__(self, exc_type: Optional[Type[BaseException]],
                        exc_val: Optional[BaseException],
                        exc_tb: Optional[Any]) -> None:
        if exc_type is not None:
            logger.debug(f"Rolling back transaction due to {exc_type.__name__}: {exc_val}")
            if self._transaction:
                await self._transaction.rollback()
        else:
            logger.debug("Committing transaction")
            if self._transaction:
                await self._transaction.commit()
