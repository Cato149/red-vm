import logging
from typing import Dict, Any

from core.protocol.base import Status, ClientCommandType
from core.protocol.requests import AuthCommand, UpdateClientSpecs, LogoutCommand
from core.protocol.responses import AuthResponse, VMInfoResponse, DefaultResponse
from services.client.vm_client import VMClientService

logger = logging.getLogger(__name__)


class ClientCommandHandler:
    def __init__(self, vm_service: VMClientService):
        self.vm_service = vm_service
        self.handlers = {
            ClientCommandType.AUTH: self.handle_auth,
            ClientCommandType.UPDATE: self.handle_update,
            ClientCommandType.LOGOUT: self.handle_logout
        }

    async def handle_command(self, command: Dict[str, Any], peer_key: str):
        try:
            command_type = ClientCommandType(command['command'])
            handler = self.handlers.get(command_type)
            if handler:
                return await handler(command, peer_key)
            return DefaultResponse(status=Status.ERROR, message="Unknown command")
        except Exception as e:
            logger.error(f"Error handling command: {e}")
            return DefaultResponse(status=Status.ERROR, message=str(e))

    async def handle_auth(self, command: Dict[str, Any], peer_key: str) -> AuthResponse:
        try:
            auth_command = AuthCommand(**command)
            is_authenticated = await self.vm_service.auth(
                vm_id=auth_command.vm_id,
                username=auth_command.username,
                password=auth_command.password,
                peer_key=peer_key
            )

            if is_authenticated:
                specs = await self.vm_service.get_info(peer_key)
                if specs:
                    return AuthResponse.success(specs)
            return AuthResponse.failed()
        except Exception as e:
            logger.error(f"Auth error: {e}")
            return AuthResponse.failed()

    async def handle_logout(self, command: Dict[str, Any], peer_key: str) -> AuthResponse:
        try:
            logout_command = LogoutCommand(**command)
            success = await self.vm_service.logout(
                peer_key=str(peer_key),
            )

            if success:
                print(f"logout status: {success}")
                return AuthResponse.logged_out()
            return AuthResponse.failed()
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return AuthResponse.failed(msg=str(e))

    async def handle_update(self, command: Dict[str, Any], peer_key: str) -> VMInfoResponse:
        try:
            update_command = UpdateClientSpecs(**command)
            success = await self.vm_service.update_specs(
                peer_key=peer_key,
                id=update_command.id,
                ram=update_command.ram,
                cpu=update_command.cpu,
                hds=update_command.hds
            )

            if success:
                specs = await self.vm_service.get_info(peer_key)
                if specs:
                    return VMInfoResponse(status=Status.OK, data=specs)
            return VMInfoResponse(
                status=Status.ERROR,
                message="Failed to update specs"
            )
        except Exception as e:
            logger.error(f"Update error: {e}")
            return VMInfoResponse(status=Status.ERROR, message=str(e))
