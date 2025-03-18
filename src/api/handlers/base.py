from typing import TypeVar, Optional

from core.protocol.base import BaseCommand, BaseResponse

ReqT = TypeVar('ReqT', bound=BaseCommand)
RespT = TypeVar('RespT', bound=BaseResponse)


class CommandHandlerInterface:
    async def handle_command(self, command: BaseCommand, peer_key: Optional[str] = None) -> BaseResponse:
        raise NotImplementedError
