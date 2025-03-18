import asyncio
import json
import logging
from typing import Optional, Dict, Any

from api.handlers.client.handler import ClientCommandHandler
from api.handlers.server.handler import CommandHandler
from core.protocol.base import Status
from core.protocol.responses import DefaultResponse
import core.log_cfg

logger = logging.getLogger(__name__)


class VMServer:
    def __init__(
            self,
            host: str,
            port: int,
            command_handler: CommandHandler | ClientCommandHandler):
        self.host = host
        self.port = port
        self.command_handler = command_handler
        self._server: Optional[asyncio.Server] = None
        self._clients: Dict[asyncio.StreamWriter, asyncio.StreamReader] = {}

    async def start(self):
        self._server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port
        )
        addr = self._server.sockets[0].getsockname()
        logger.info(f'Server started on {addr}')

        async with self._server:
            await self._server.serve_forever()

    async def stop(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info('Server stopped')

        for writer in self._clients.keys():
            writer.close()
            await writer.wait_closed()

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peer_name = writer.get_extra_info('peername')
        logger.info(f'New connection from {peer_name}')
        while True:
            try:
                data = await reader.read(1024)
                if not data:
                    break
                print(f"Received data from {peer_name}: {data.decode()}")
                message = json.loads(data.decode())
                result = await self.command_handler.handle_command(message, peer_name)

                writer.write(json.dumps(result.model_dump_json()).encode())
                await writer.drain()

            except Exception as e:
                print(f"Error handling client: {e}")
                break

        writer.close()
        await writer.wait_closed()

    async def _send_response(self, writer: asyncio.StreamWriter, response: Any):
        try:
            response_json = (
                response.model_dump_json()
                if hasattr(response, 'model_dump_json')
                else json.dumps(response)
            )
            print(f"Sending response to client: {response_json}")
            response_bytes = response_json.encode()

            writer.write(len(response_bytes).to_bytes(4, 'big'))
            writer.write(response_bytes)
            await writer.drain()

        except Exception as e:
            logger.exception("Error sending response")
            error_response = DefaultResponse(
                status=Status.ERROR,
                message=str(e)
            ).model_dump_json().encode()
            writer.write(len(error_response).to_bytes(4, 'big'))
            writer.write(error_response)
            await writer.drain()
