from datetime import datetime
from typing import Optional, List

from core.models import VMSpecs, HardDrive
from core.protocol.base import BaseResponse
from core.protocol.base import Status


# -------VM Server--------


class VMResponse(BaseResponse):
    vm_id: Optional[int] = None
    data: Optional[VMSpecs] = None
    last_connection: Optional[datetime] = None
    is_connected: bool = False


class VMListResponse(BaseResponse):
    vms: List[VMResponse]


class DriveResponse(BaseResponse):
    drive_id: Optional[int] = None
    drives: Optional[List[HardDrive]] = None
    vm_id: Optional[int] = None


class ListDrivesResponse(BaseResponse):
    hds: List[HardDrive] = []


# -------VM Client--------


class AuthResponse(BaseResponse):
    specs: Optional[VMSpecs] = None

    @classmethod
    def failed(cls, msg: Optional[str] = None) -> 'AuthResponse':
        return cls(status=Status.ERROR, message=f'Field. {msg}')

    @classmethod
    def success(cls, specs: VMSpecs) -> 'AuthResponse':
        return cls(status=Status.OK, message='Authentication successful', specs=specs)

    @classmethod
    def logged_out(cls):
        return cls(status=Status.OK, message='Logged out successfully')


class VMInfoResponse(BaseResponse):
    data: Optional[VMSpecs] = None


class DefaultResponse(BaseResponse):
    pass
