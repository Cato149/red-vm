import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict
from typing import Optional

from core.models import HardDrive, VM, VMSpecs
from db.conn import DatabaseConnection
from services.server.connection_manager import ConnectionManagerBase
from core.protocol.requests import UpdateClientSpecs
import json

logger = logging.getLogger(__name__)


class VMServiceBase(ABC):
    auth_manager: ConnectionManagerBase
    db_conn: DatabaseConnection

    @abstractmethod
    async def create(self, ram: int, cpu: int, hds: List[HardDrive]) -> VM:
        """Create a new virtual machine

        Args:
            ram (int): Amount of RAM in GB
            cpu (int): Number of CPU cores
            hds (Set[HardDrive]): List of hard drives to attach

        Returns:
            VMSpecs: Specifications of created VM
        """
        pass

    @abstractmethod
    async def update_info(
            self,
            vm_id: int,
            ram: Optional[int],
            cpu: Optional[int],
            hds: Optional[List[HardDrive]]) -> VM:
        """Update virtual machine specifications

        Args:
            vm_id (int): ID of VM to update
            ram (Optional[int]): New RAM amount in GB
            cpu (Optional[int]): New CPU core count
            hds (Optional[List[HardDrive]]): New list of hard drives

        Returns:
            VMSpecs: Updated VM specifications
        """
        pass

    @abstractmethod
    async def get_info(self, vm_id: int) -> VM:
        """Get information about specific VM

        Args:
            vm_id (int): ID of VM to get info for

        Returns:
            VMSpecs: VM specifications
        """
        pass

    @abstractmethod
    async def list_vms(self) -> List[VM]:
        """Get list of all VMs

        Returns:
            List[VMSpecs]: List of all VM specifications
        """
        pass

    @abstractmethod
    async def delete_vm(self, vm_id: int) -> bool:
        """Delete a virtual machine

        Args:
            vm_id (int): ID of VM to delete

        Returns:
            bool: True if deleted successfully
        """
        pass

    @abstractmethod
    async def connect(self,
                      host: str,
                      port: int,
                      username: str,
                      password: str) -> bool:
        """Connect to a VM

        Args:
            host (str): VM hostname
            port (int): Port number
            username (str): Authentication username
            password (str): Authentication password

        Returns:
            bool: True if connected successfully
        """
        pass

    @abstractmethod
    async def logout(self, id: int) -> bool:
        """logout from a VM

        Args:
            id (int): ID of VM to disconnect from

        Returns:
            bool: True if disconnected successfully
        """
        pass

    @abstractmethod
    async def get_connected(self) -> List[VM]:
        """Get list of connected VMs

        Returns:
            List[VMSpecs]: List of specifications for connected VMs
        """
        pass

    @abstractmethod
    async def get_athenificated(self) -> List[VM]:
        """Get list of authenticated VMs

        Returns:
            List[VMSpecs]: List of specifications for authenticated VMs
        """
        pass


class VMService(VMServiceBase):
    def __init__(self, auth_manager: ConnectionManagerBase, db_conn: DatabaseConnection):
        self.auth_manager = auth_manager
        self.db_conn = db_conn
        self._vms: Dict[int, VM] = {}
        self._initialized = False

    async def initialize(self):
        if not self._initialized:
            await self.db_conn.connect()
            self._initialized = True

    async def shutdown(self):
        if self._initialized:
            await self.db_conn.disconnect()
            self._initialized = False

    async def _ensure_initialized(self):
        if not self._initialized:
            await self.initialize()

    async def create(self, ram: int, cpu: int, hds: List[HardDrive]) -> VM:
        await self._ensure_initialized()
        async with self.db_conn.transaction() as uow:
            vm_id = await uow.vms.add(ram, cpu)

            for hd in hds:
                await uow.drives.add(vm_id, hd.size)

            drives = await uow.drives.get_for_vm(vm_id)
            hds_with_ids = [HardDrive(id=d['id'], size=d['size']) for d in drives]

            specs = VMSpecs(id=vm_id, ram=ram, cpu=cpu, hard_drives=hds_with_ids)
            vm = VM(specs=specs)
            self._vms[vm_id] = vm

            return vm

    # TODO: Refactor this method - TO BIG!!!
    async def update_info(
            self,
            vm_id: int,
            ram: Optional[int],
            cpu: Optional[int],
            hds: Optional[List[HardDrive]]) -> VM:
        await self._ensure_initialized()
        vm = self._vms[vm_id]
        if not vm.connection:
            logger.error(f"VM with id {vm_id} not authenticated")
            raise ValueError(f"VM with id {vm_id} not authenticated")

        async with self.db_conn.transaction() as uow:
            vm_data = await uow.vms.get(vm_id)
            if not vm_data:
                logger.error(f"VM with id {vm_id} not found")
                raise ValueError(f"VM with id {vm_id} not found")

            if ram is not None or cpu is not None:
                await uow.vms.update(
                    vm_id,
                    ram if ram is not None else vm_data['ram'],
                    cpu if cpu is not None else vm_data['cpu']
                )

            if hds is not None:

                for hd in hds:
                    if hd.id == 0:
                        logger.info(f"Adding hard drive {hd.id} for VM {vm_id}")
                        await uow.drives.add(vm_id, hd.size)
                    else:
                        logger.info(f"Updating hard drive {hd.id} for VM {vm_id}")
                        await uow.drives.update(hd.id, hd.size)

            vm_data = await uow.vms.get(vm_id)
            drives = await uow.drives.get_for_vm(vm_id)
            hds_updated = [HardDrive(id=d['id'], size=d['size']) for d in drives]

            specs = VMSpecs(
                id=vm_id,
                ram=vm_data['ram'],
                cpu=vm_data['cpu'],
                hard_drives=hds_updated
            )

            r = UpdateClientSpecs(id=None, ram=ram, cpu=cpu, hds=hds_updated)
            auth_result = await vm.connection.send_command(r)
            auth_result = json.loads(auth_result)
            if auth_result['status'] == 'ok':
                if vm:
                    self._vms[vm_id].specs = specs
                else:
                    self._vms[vm_id] = VM(specs=specs)

                return self._vms[vm_id]
            else:
                raise ValueError(f"Failed to update VM specs: {auth_result['message']}")

    async def get_info(self, vm_id: int) -> VM:
        await self._ensure_initialized()
        async with self.db_conn.transaction() as uow:
            vm_data = await uow.vms.get(vm_id)
            if not vm_data:
                raise ValueError(f"VM with id {vm_id} not found")

            drives = await uow.drives.get_for_vm(vm_id)
            hds = [HardDrive(id=d['id'], size=d['size']) for d in drives]

            specs = VMSpecs(
                id=vm_id,
                ram=vm_data['ram'],
                cpu=vm_data['cpu'],
                hard_drives=hds
            )

            if vm_id in self._vms:
                self._vms[vm_id].specs = specs
            else:
                self._vms[vm_id] = VM(specs=specs)

            return self._vms[vm_id]

    async def list_vms(self) -> List[VM]:
        await self._ensure_initialized()
        async with self.db_conn.transaction() as uow:
            vms_data = await uow.vms.get_all()
            vms = []

            for vm_data in vms_data:
                drives = await uow.drives.get_for_vm(vm_data['id'])
                hds = [HardDrive(id=d['id'], size=d['size']) for d in drives]

                specs = VMSpecs(
                    id=vm_data['id'],
                    ram=vm_data['ram'],
                    cpu=vm_data['cpu'],
                    hard_drives=hds
                )
                if vm_data['id'] in self._vms:
                    self._vms[vm_data['id']].specs = specs
                    self._vms[vm_data['id']].last_connected = vm_data['last_connected']
                    vms.append(self._vms[vm_data['id']])
                else:
                    vm = VM(specs=specs)
                    vm.last_connected = vm_data['last_connected']
                    self._vms[vm_data['id']] = vm
                    vms.append(vm)

            return vms

    async def delete_vm(self, vm_id: int) -> bool:
        await self._ensure_initialized()
        async with self.db_conn.transaction() as uow:
            if vm_id in self._vms:
                vm = self._vms[vm_id]
                if vm.is_connected:
                    await self.disconnect(vm_id)
                del self._vms[vm_id]

            drives = await uow.drives.get_for_vm(vm_id)
            for drive in drives:
                await uow.drives.remove(drive['id'])

            # TODO: Add VM deletion from database
            return True

    async def connect(self, vm_id: int, host: str, port: int, username: str, password: str) -> bool:
        await self._ensure_initialized()
        async with self.db_conn.transaction() as uow:
            try:
                vm = await self.get_info(vm_id) if vm_id != 0 else None
                if vm is None:
                    vm = await self.create(ram=1, cpu=1, hds=[HardDrive(size=4, vm_id=0, id=0)])
                    vm_id = vm.specs.id

                logging.debug(f"Connecting to VM {vm_id}")
                connection = await self.auth_manager.connect(vm_id, host, port)
                auth_result = await self.auth_manager.authenticate(vm_id=vm_id, username=username, password=password)

                if not auth_result:
                    logging.error(f"Authentication failed for VM {vm_id}")
                    await connection.close()
                    return False

                vm.connection = connection
                vm.is_connected = True
                vm.last_connected = datetime.now()
                self._vms[vm_id] = vm

                await uow.vms.update_connection_time(vm_id)

                logger.info(f"Connected to VM {vm_id}")
                return True

            except Exception as e:
                logger.error(f"Connection failed: {e}")
                return False

    async def logout(self, vm_id: int) -> bool:
        print("logging out")
        if vm_id not in self._vms:
            return False

        vm = self._vms[vm_id]
        if not vm.is_connected:
            print("VM is not connected")
            return False
        print("sending logout request")
        result = await self.auth_manager.logout(vm_id)
        if result:
            print("Logged out successfully")
            vm.is_connected = False

        return result

    async def get_connected(self) -> List[VM]:
        vm_ids = await self.auth_manager.get_connected()
        return [await self.get_info(vm_id) for vm_id in vm_ids]

    async def get_athenificated(self) -> List[VM]:
        vm_ids = await self.auth_manager.get_athenificated()
        return [await self.get_info(vm_id) for vm_id in vm_ids]

    async def list_drives(self, vm_id: int | None = None) -> List[HardDrive]:
        await self._ensure_initialized()
        async with self.db_conn.transaction() as uow:
            drives_list = []

            if vm_id is None:
                drives = await uow.drives.get_all()
            else:
                drives = await uow.drives.get_for_vm(vm_id)

            if drives is None:
                return []

            for d in drives:
                dieve_specs = HardDrive(**d)
                drives_list.append(dieve_specs)

            return drives_list
