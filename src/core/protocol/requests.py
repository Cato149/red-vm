from typing import Optional, List

from pydantic import Field

from core.models import HardDrive
from core.protocol.base import BaseCommand
from core.protocol.base import ClientCommandType
from core.protocol.base import ManagerCommandType


# -------------------Server-------------------
class ConnectCommand(BaseCommand):
    command: ManagerCommandType = ManagerCommandType.CONNECT
    vm_id: int
    username: str
    password: str
    host: str = Field('localhost', min_length=1)
    port: int = Field(9000, gt=0)


class LogoutClientCommand(BaseCommand):
    command: ManagerCommandType = ManagerCommandType.LOGOUT
    vm_id: int


class UpdateSpecsCommand(BaseCommand):
    command: ManagerCommandType = ManagerCommandType.UPDATE_SPECS
    vm_id: int
    ram: Optional[int] = Field(None, gt=0)
    cpu: Optional[int] = Field(None, gt=0)
    hds: Optional[List[HardDrive]] = None


class GetInfoCommand(BaseCommand):
    command: ManagerCommandType = ManagerCommandType.GET_INFO
    vm_id: int


class AddDriveCommand(BaseCommand):
    command: ManagerCommandType = ManagerCommandType.ADD_DRIVE
    vm_id: int
    size: int = Field(1, gt=0)


class RemoveDriveCommand(BaseCommand):
    command: ManagerCommandType = ManagerCommandType.REMOVE_DRIVE
    drive_id: int


class ListVMsCommand(BaseCommand):
    command: ManagerCommandType = ManagerCommandType.LIST_VMS
    list_type: Optional[str] = 'all'


class ListDrivesCommand(BaseCommand):
    command: ManagerCommandType = ManagerCommandType.LIST_DRIVES
    vm_id: int | None = None


class AddVMCommand(BaseCommand):
    command: ManagerCommandType = ManagerCommandType.ADD_VM
    ram: int = Field(1, gt=0)
    cpu: int = Field(1, gt=0)
    hds: Optional[List[HardDrive]] = None


# ------------------- Client -----------------
class AuthCommand(BaseCommand):
    command: ClientCommandType = ClientCommandType.AUTH
    vm_id: int
    username: str
    password: str


# TODO: For the future mostly... In this iteration is for updating ID on cleient
class UpdateClientSpecs(BaseCommand):
    command: ClientCommandType = ClientCommandType.UPDATE
    id: Optional[int] = 0
    ram: Optional[int] = Field(1, gt=0)
    cpu: Optional[int] = Field(1, gt=0)
    hds: Optional[List[HardDrive]] = None


class LogoutCommand(BaseCommand):
    command: ClientCommandType = ClientCommandType.LOGOUT
