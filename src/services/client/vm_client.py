import logging
from abc import ABC, abstractmethod
from typing import List

from core.models import HardDrive, VMSpecs
from services.client.auth import AuthClientService, AuthClientServiceBase

logger = logging.getLogger(__name__)


class VMClientServiceBase(ABC):
    """Base class for VM client services

    Provides interface for VM authentication, information retrieval and specification updates.
    Implementations handle client-side VM management and communication with server.
    """
    specs: VMSpecs
    auth_manager: AuthClientServiceBase

    @abstractmethod
    def auth(self, vm_id: int, username: str, password: str) -> bool:
        """Authenticate Server

        Args:
            vm_id (int): VM ID to authenticate
            username (str): Authentication username
            password (str): Authentication password

        Returns:
            bool: True if authentication successful, False otherwise
        """
        pass

    @abstractmethod
    async def get_info(self) -> VMSpecs:
        """Get current VM specifications

        Returns:
            VMSpecs: Current VM specifications
        """
        pass

    @abstractmethod
    async def update_specs(self, specs: VMSpecs) -> bool:
        """Update VM specifications

        Args:
            specs (VMSpecs): New VM specifications to apply

        Returns:
            bool: True if update successful, False otherwise
        """
        pass


class VMClientService(VMClientServiceBase):
    def __init__(self, specs: VMSpecs, username: str, password: str):
        self.specs = specs
        self.auth_manager = AuthClientService(
            username=username,
            password=password,
            authorized_servers=set()
        )
        logger.info("VM client service initialized")

    async def auth(self, vm_id: int, username: str, password: str, peer_key: str) -> bool:
        # TODO: Update disk id
        try:
            is_authenticated = await self.auth_manager.authenticate(
                username=username,
                password=password,
                peer=peer_key
            )
            if self.specs.id == 0:
                self.specs.id = vm_id
            if self.specs.id != vm_id:
                logger.warn(f"VM ID[{vm_id}] mismatch for {self.specs}")
                return False
            if is_authenticated:
                logger.info(f"Server {peer_key} successfully authenticated")
            else:
                logger.warning(f"Authentication failed for {peer_key}")
            print(f'authorized servers: {self.auth_manager.authorized_servers}')
            return is_authenticated

        except Exception as e:
            logger.error(f"Authentication error for {peer_key}: {e}")
            return False

    async def get_info(self, peer_key: str) -> VMSpecs | None:
        logger.info(f"Sending info to {peer_key}")
        if not await self.auth_manager.is_authorized(peer_key):
            logger.warning(f"Unauthorized access attempt from {peer_key}")
            return None
        return self.specs

    async def update_specs(
            self,
            peer_key: str,
            id: int | None = None,
            ram: int | None = None,
            cpu: int | None = None,
            hds: List[HardDrive] | None = None) -> bool:
        logger.info(f"Sending info to {peer_key}")
        if not await self.auth_manager.is_authorized(peer_key):
            logger.warning(f"Unauthorized update attempt from {peer_key}")
            return False

        try:
            if id is not None and self.specs.id != 0 and id != self.specs.id:
                logger.error("Cannot update specs with different VM ID")
                return False

            if id is not None:
                self.specs.id = id
            if ram is not None:
                self.specs.ram = ram
            if cpu is not None:
                self.specs.cpu = cpu
            if hds is not None:
                self.specs.hard_drives = hds

            logger.info("Successfully updated VM specifications")
            return True

        except Exception as e:
            logger.error(f"Error updating specs: {e}")
            return False

    async def logout(self, peer_key: str) -> bool:
        print(f'authorized servers: {self.auth_manager.authorized_servers}')
        print(peer_key + " try to logout")
        if peer_key in self.auth_manager.authorized_servers:
            print("Successfully logged out")
            self.auth_manager.authorized_servers.remove(peer_key)
            return True
        return False
