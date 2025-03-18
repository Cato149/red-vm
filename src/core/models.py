import asyncio
import json
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from core.protocol.base import BaseCommand


class VMConnection(BaseModel):
    reader: Optional[asyncio.StreamReader] = None
    writer: Optional[asyncio.StreamWriter] = None
    is_authenticated: bool = False

    async def close(self):
        if self.writer and not self.writer.is_closing():
            self.writer.close()
            await self.writer.wait_closed()
        self.reader = None
        self.writer = None
        self.is_authenticated = False

    async def send_command(self, command: BaseCommand) -> dict:
        if not self.writer or not self.reader:
            raise ConnectionError("No active connection")

        self.writer.write(command.model_dump_json().encode())
        await self.writer.drain()

        data = await self.reader.read(4096)

        if not data:
            raise ValueError("No data received from the server")

        decoded_data = data.decode("utf-8")
        try:
            return json.loads(decoded_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON received: {decoded_data}") from e

    model_config = {
        "arbitrary_types_allowed": True
    }


class HardDrive(BaseModel):
    vm_id: int = Field(0, description="ID of the VM to which the hard drive belongs")
    id: int = Field(0, description="Unique identifier for the hard drive", ge=0)
    size: int = Field(..., description="Size of the hard drive in GB", gt=0)


class VMSpecs(BaseModel):
    id: int = Field(0, description="Unique identifier for the VM", ge=0)
    ram: int = Field(..., description="Amount of RAM in GB", gt=0)
    cpu: int = Field(..., description="Number of CPU cores", gt=0)
    hard_drives: List[HardDrive]


class VM(BaseModel):
    specs: VMSpecs
    connection: Optional[VMConnection] = None
    is_connected: bool = False
    last_connected: Optional[datetime] = None
