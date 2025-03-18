from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_serializer


class Status(Enum):
    OK = 'ok'
    ERROR = 'error'


class ManagerCommandType(Enum):
    CONNECT = 'connect'
    LOGOUT = 'logout'
    UPDATE_SPECS = 'update_specs'
    GET_INFO = 'get_info'
    ADD_DRIVE = 'add_drive'
    REMOVE_DRIVE = 'remove_drive'
    LIST_VMS = 'list_vms'
    LIST_DRIVES = 'list_drives'
    ADD_VM = 'add_vm'


class ClientCommandType(Enum):
    AUTH = 'auth'
    LOGOUT = 'logout'
    UPDATE = 'update'


class BaseCommand(BaseModel):
    command: Enum

    @field_serializer('command')
    def serialize_enum(self, command: Enum) -> str:
        return command.value


class BaseResponse(BaseModel):
    status: Status
    message: Optional[str] = None

    @field_serializer('status')
    def serialize_enum(self, command: Enum) -> str:
        return command.value
