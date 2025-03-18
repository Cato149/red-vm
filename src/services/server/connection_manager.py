import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List

from core.models import VM, VMConnection
from core.protocol.requests import AuthCommand, LogoutCommand
import json
import core.log_cfg

logger = logging.getLogger(__name__)


class ConnectionManagerBase(ABC):
    _connected_vms: Dict[int, VM]

    @abstractmethod
    async def connect(self,
                      vm_id: int,
                      host: str,
                      port: int) -> VMConnection:
        pass

    @abstractmethod
    async def logout(self, vm_id: int) -> bool:
        pass

    @abstractmethod
    async def authenticate(self, vm_id: int, username: str, password: str):
        pass

    @abstractmethod
    async def get_connected(self) -> List[int]:
        pass

    @abstractmethod
    async def get_athenificated(self) -> List[int]:
        pass


class ConnectionManager(ConnectionManagerBase):
    def __init__(self):
        self._connected_vms: Dict[int, VMConnection] = {}

    async def connect(self,
                      vm_id: int,
                      host: str,
                      port: int) -> VMConnection:
        try:
            reader, writer = await asyncio.open_connection(host, port)
            connection = VMConnection(reader=reader, writer=writer)
            self._connected_vms[vm_id] = connection
            return connection
        except Exception as e:
            logger.error(f"Failed to connect to VM {vm_id}: {e}")
            raise ConnectionError(f"Failed to connect to VM {vm_id}: {e}")

    async def disconnect(self, vm: VM) -> bool:
        if not vm.connection:
            return False

        try:
            await vm.connection.close()
            del self._connected_vms[vm.specs.id]
            vm.connection = None
            return True
        except Exception as e:
            logger.error(f"Error disconnecting VM {vm.specs.id}: {e}")
            return False

    async def authenticate(self, vm_id: int, username: str, password: str) -> bool:
        vm = self._connected_vms[vm_id]
        if not vm:
            raise ConnectionError("VM not connected")

        r = AuthCommand(vm_id=vm_id, username=username, password=password)
        auth_result = await vm.send_command(r)
        auth_result = json.loads(auth_result)
        if auth_result['status'] == 'ok':
            vm.is_authenticated = True
            logger.info(f"VM {vm_id} authenticated")
            return True
        if auth_result['status'] == 'error':
            logger.error(f"VM {vm_id} authentication failed")
            return False
        return False

    async def logout(self, vm_id: int) -> bool:
        vm = self._connected_vms[vm_id]
        if not vm:
            raise ConnectionError("VM not connected")

        r = LogoutCommand()

        logout_result = await vm.send_command(r)
        logout_result = json.loads(logout_result)

        if logout_result['status'] == 'ok':
            vm.is_authenticated = False
            logger.info(f"VM {vm_id} logged out")
            return True
        return False

    async def get_connected(self) -> List[int]:
        return list(self._connected_vms.keys())

    async def get_athenificated(self) -> List[int]:
        return [id for id, vm in self._connected_vms.items() if vm.is_authenticated]
