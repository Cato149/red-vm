from datetime import datetime
from typing import Optional, Dict, Any

from api.handlers.base import CommandHandlerInterface
from core.models import HardDrive
from core.protocol.base import Status, ManagerCommandType
from core.protocol.requests import (
    ConnectCommand, LogoutClientCommand, UpdateSpecsCommand,
    GetInfoCommand, AddDriveCommand, RemoveDriveCommand,
    ListVMsCommand, AddVMCommand, ListDrivesCommand
)
from core.protocol.responses import VMResponse, DriveResponse, VMListResponse, DefaultResponse, ListDrivesResponse
from services.server.vm_server import VMService
import logging

logger = logging.getLogger(__name__)


class CommandHandler(CommandHandlerInterface):
    def __init__(self, vm_service: VMService):
        self.vm_service = vm_service
        self.handlers = {
            ManagerCommandType.CONNECT: self.handle_connect,
            ManagerCommandType.LOGOUT: self.handle_logout,
            ManagerCommandType.UPDATE_SPECS: self.handle_update_specs,
            ManagerCommandType.GET_INFO: self.handle_get_info,
            ManagerCommandType.ADD_DRIVE: self.handle_add_drive,
            ManagerCommandType.REMOVE_DRIVE: self.handle_remove_drive,
            ManagerCommandType.LIST_VMS: self.handle_list_vms,
            ManagerCommandType.ADD_VM: self.handle_add_vm,
            ManagerCommandType.LIST_DRIVES: self.handle_list_drives
        }

    async def handle_command(self, command: Dict[str, Any], peer_key: Optional[str] = None):
        command_type = ManagerCommandType(command['command'])
        handler = self.handlers.get(command_type)
        if handler:
            return await handler(command)
        return DefaultResponse(status=Status.ERROR, message="Unknown command")

    async def handle_connect(self, data: Dict[str, Any]) -> VMResponse:
        try:
            command = ConnectCommand(**data)
            success = await self.vm_service.connect(
                vm_id=command.vm_id,
                host=command.host,
                port=command.port,
                username=command.username,
                password=command.password
            )
            if success:
                return VMResponse(
                    status=Status.OK,
                    is_connected=True,
                    last_connection=datetime.now()
                )
            return VMResponse(
                status=Status.ERROR,
                message="Connection failed",
                is_connected=False
            )
        except Exception as e:
            return VMResponse(
                status=Status.ERROR,
                message=str(e),
                is_connected=False
            )

    async def handle_logout(self, data: Dict[str, Any]) -> VMResponse:
        try:
            command = LogoutClientCommand(**data)
            success = await self.vm_service.logout(command.vm_id)
            if success:
                return VMResponse(
                    status=Status.OK,
                    vm_id=command.vm_id,
                    is_connected=False
                )
            return VMResponse(
                status=Status.ERROR,
                message="Disconnection failed",
                vm_id=command.vm_id,
                is_connected=True
            )
        except Exception as e:
            return VMResponse(status=Status.ERROR, message=str(e))

    async def handle_update_specs(self, data: Dict[str, Any]) -> VMResponse:
        try:
            command = UpdateSpecsCommand(**data)
            vm = await self.vm_service.update_info(
                command.vm_id,
                command.ram,
                command.cpu,
                command.hds
            )
            return VMResponse(
                status=Status.OK,
                vm_id=vm.specs.id,
                data=vm.specs,
                is_connected=vm.is_connected,
                last_connection=vm.last_connected
            )
        except Exception as e:
            return VMResponse(status=Status.ERROR, message=str(e))

    async def handle_get_info(self, data: Dict[str, Any]) -> VMResponse:
        try:
            command = GetInfoCommand(**data)
            vm = await self.vm_service.get_info(command.vm_id)
            return VMResponse(
                status=Status.OK,
                vm_id=vm.specs.id,
                data=vm.specs,
                is_connected=vm.is_connected,
                last_connection=vm.last_connected
            )
        except Exception as e:
            return VMResponse(status=Status.ERROR, message=str(e))

    async def handle_add_drive(self, data: Dict[str, Any]) -> DriveResponse:
        try:
            command = AddDriveCommand(**data)
            vm = await self.vm_service.update_info(
                command.vm_id,
                None,
                None,
                [HardDrive(size=command.size, id=0, vm_id=command.vm_id)]
            )
            new_drive = vm.specs.hard_drives[-1]
            return DriveResponse(
                status=Status.OK,
                drive_id=new_drive.id,
                drives=vm.specs.hard_drives,
                vm_id=command.vm_id
            )
        except Exception as e:
            return DriveResponse(status=Status.ERROR, message=str(e))

    async def handle_list_drives(self, data: Dict[str, Any]) -> ListDrivesResponse:
        try:
            command = ListDrivesCommand(**data)
            drives = await self.vm_service.list_drives(command.vm_id)

            return ListDrivesResponse(
                status=Status.OK,
                hds=drives
            )
        except Exception as e:
            return ListDrivesResponse(status=Status.ERROR, message=str(e))

    async def handle_remove_drive(self, data: Dict[str, Any]) -> DriveResponse:
        try:
            command = RemoveDriveCommand(**data)
            vm = await self.vm_service.get_info(command.drive_id)
            new_drives = [hd for hd in vm.specs.hard_drives if hd.id != command.drive_id]
            updated_vm = await self.vm_service.update_info(
                vm.specs.id,
                None,
                None,
                new_drives
            )
            return DriveResponse(
                status=Status.OK,
                drive_id=command.drive_id,
                drives=updated_vm.specs.hard_drives,
                vm_id=vm.specs.id
            )
        except Exception as e:
            return DriveResponse(status=Status.ERROR, message=str(e))

    async def handle_list_vms(self, data: Dict[str, Any]) -> VMListResponse:
        try:
            command = ListVMsCommand(**data)
            if command.list_type == 'connected':
                vms = await self.vm_service.get_connected()
            elif command.list_type == 'authenticated':
                vms = await self.vm_service.get_athenificated()
            else:
                vms = await self.vm_service.list_vms()

            vm_responses = [
                VMResponse(
                    status=Status.OK,
                    vm_id=vm.specs.id,
                    data=vm.specs,
                    is_connected=vm.is_connected,
                    last_connection=vm.last_connected
                ) for vm in vms
            ]
            return VMListResponse(status=Status.OK, vms=vm_responses)
        except Exception as e:
            return VMListResponse(status=Status.ERROR, message=str(e), vms=[])

    async def handle_add_vm(self, data: Dict[str, Any]) -> VMResponse:
        try:
            command = AddVMCommand(**data)
            default_drives = [HardDrive(size=4, id=0, vm_id=0)] if command.hds is None else command.hds

            vm = await self.vm_service.create(
                ram=command.ram,
                cpu=command.cpu,
                hds=default_drives
            )
            return VMResponse(
                status=Status.OK,
                vm_id=vm.specs.id,
                data=vm.specs,
                is_connected=vm.is_connected,
                last_connection=vm.last_connected
            )
        except Exception as e:
            return VMResponse(status=Status.ERROR, message=str(e))
