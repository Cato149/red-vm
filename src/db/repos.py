from datetime import datetime
from typing import Optional, Any, Dict, List

from asyncpg.connection import Connection


# TODO: Mapping in models instead of dict
class VirtualMachineRepository:
    def __init__(self, connection: Connection):
        self.connection = connection

    async def add(self, ram: int, cpu: int) -> int:
        vm_id = await self.connection.fetchval(
            'INSERT INTO virtual_machines (ram, cpu, is_connected) VALUES ($1, $2, false) RETURNING id',
            ram, cpu
        )
        return vm_id

    async def get(self, vm_id: int) -> Optional[Dict[str, Any]]:
        row = await self.connection.fetchrow('SELECT * FROM virtual_machines WHERE id = $1', vm_id)
        return dict(row) if row else None

    async def update(self, vm_id: int, ram: int, cpu: int) -> None:
        await self.connection.execute(
            'UPDATE virtual_machines SET ram = $2, cpu = $3 WHERE id = $1',
            vm_id, ram, cpu
        )

    async def update_connection_time(self, vm_id: int) -> None:
        await self.connection.execute(
            '''
            UPDATE virtual_machines
            SET last_connected = $2
            WHERE id = $1
            ''',
            vm_id, datetime.now()
        )

    async def get_all(self) -> List[Dict[str, Any]]:
        rows = await self.connection.fetch('SELECT * FROM virtual_machines')
        return [dict(row) for row in rows]

    async def get_connected(self) -> List[Dict[str, Any]]:
        rows = await self.connection.fetch('SELECT * FROM virtual_machines WHERE is_connected = true')
        return [dict(row) for row in rows]


# ------ HardDrive -------


# TODO: Mapping in models instead of dict
class HardDriveRepository:
    def __init__(self, connection: Connection):
        self.connection = connection

    async def add(self, vm_id: int, size: int) -> int:
        drive_id = await self.connection.fetchval(
            'INSERT INTO hard_drives (vm_id, size) VALUES ($1, $2) RETURNING id',
            vm_id, size
        )
        return drive_id

    async def remove(self, drive_id: int) -> None:
        await self.connection.execute('DELETE FROM hard_drives WHERE id = $1', drive_id)

    async def get_for_vm(self, vm_id: int) -> List[Dict[str, Any]]:
        rows = await self.connection.fetch('SELECT * FROM hard_drives WHERE vm_id = $1', vm_id)
        return [dict(row) for row in rows]

    async def update(self, drive_id: int, size: int) -> None:
        print(f"Updating drive {drive_id} to size {size}")
        await self.connection.execute('UPDATE hard_drives SET size = $1 WHERE id = $2', size, drive_id)

    async def create_or_update(self):
        ...

    async def get_all(self) -> List[Dict[str, Any]]:
        rows = await self.connection.fetch(
            '''
            SELECT hd.*, vm.ram, vm.cpu
            FROM hard_drives hd
            LEFT JOIN virtual_machines vm ON hd.vm_id = vm.id
            '''
        )
        return [dict(row) for row in rows]
