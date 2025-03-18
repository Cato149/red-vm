from core.protocol.requests import LogoutClientCommand
import typer
import asyncio
import json
from rich.table import Table
from rich.progress import Progress
from rich.panel import Panel
from rich.console import Console

from db.conn import DatabaseConnection
from api.server import VMServer
from services.server.vm_server import VMService
from api.handlers.server.handler import CommandHandler
from services.server.connection_manager import ConnectionManager
from core.protocol.requests import (
    AddDriveCommand,
    ConnectCommand,
    ListVMsCommand,
    AddVMCommand,
    GetInfoCommand,
    UpdateSpecsCommand,
    ListDrivesCommand
)
from core.protocol.base import ManagerCommandType
from core.protocol.base import Status
from core.models import HardDrive, VMSpecs
from services.client.vm_client import VMClientService
from api.handlers.client.handler import ClientCommandHandler
from core.protocol.responses import AuthResponse, VMListResponse, VMResponse, ListDrivesResponse
from core.config.config import Settings

cfg = Settings()
app = typer.Typer()
console = Console()
db_conn = DatabaseConnection(
    dsn=cfg.conn_str()
)
auth_manager = ConnectionManager()
vm_service = VMService(auth_manager, db_conn)
command_handler = CommandHandler(vm_service)


async def send_request(command: dict, host="localhost", port=cfg.port):
    reader, writer = await asyncio.open_connection(host, port)

    request_data = json.dumps(command).encode()
    writer.write(request_data)
    await writer.drain()

    response_data = await reader.read(4096)
    response = json.loads(response_data.decode())

    writer.close()
    await writer.wait_closed()

    return json.loads(response)


@app.command()
def server_start(
        host: str = typer.Option("localhost", help="Server host"),
        port: int = typer.Option(cfg.port, help="Server port"),
):
    server = VMServer(host, port, command_handler)
    typer.echo(f"Starting server on {host}:{port}")

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        asyncio.run(server.stop())


@app.command()
def server_stop():
    ...


@app.command()
def connect(
        vm_id: int = typer.Option(..., help="ID of the VM to connect to"),
        username: str = typer.Option(..., help="Username for connection"),
        password: str = typer.Option(..., help="Password for connection"),
        host: str = typer.Option(None, help="Host to connect to"),
        port: int = typer.Option(None, help="Port to connect to")):
    command = ConnectCommand(
        vm_id=vm_id,
        command=ManagerCommandType.CONNECT,
        username=username,
        password=password,
        host=host,
        port=port
    )
    result = asyncio.run(send_request(command.model_dump()))
    result = AuthResponse(**result)
    if result.status == Status.OK:
        console.print("[green]Successfully connected![/green]")
    else:
        console.print(f"[red]Connection failed: {result}[/red]")


@app.command()
def list_vms(
        list_type: str = typer.Option("all", help="Type of list (all/connected/authenticated)")):
    command = ListVMsCommand(
        command=ManagerCommandType.LIST_VMS,
        list_type=list_type
    )

    result = asyncio.run(send_request(command.model_dump()))
    result = VMListResponse(**result)

    if result.status == Status.OK:
        table = Table(title="Virtual Machines")
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("RAM (GB)", style="magenta")
        table.add_column("CPU", style="green")
        table.add_column("Hard Drives", style="yellow")
        table.add_column("Status", style="blue")
        table.add_column("Last Connected", style="blue")

        for vm in result.vms:
            drives = ", ".join([f"{hd.size}GB" for hd in vm.data.hard_drives]) if vm.data.hard_drives else "None"
            status = "🟢 Authenticated" if vm.is_connected else "🔴 Not Authenticated"
            last_conn = vm.last_connection.strftime("%Y-%m-%d %H:%M:%S") if vm.last_connection else "Never"

            table.add_row(
                str(vm.vm_id),
                str(vm.data.ram),
                str(vm.data.cpu),
                drives,
                status,
                last_conn
            )
        console.print(table)
    else:
        console.print(f"[red]Error: {result.message}[/red]")


@app.command()
def add_vm(
        ram: int = typer.Option(1, help="RAM size in GB"),
        cpu: int = typer.Option(1, help="Number of CPU cores"),
        drive_size: int = typer.Option(4, help="Size of initial drive in GB")):
    command = AddVMCommand(
        command=ManagerCommandType.ADD_VM,
        ram=ram,
        cpu=cpu,
        hds=[HardDrive(size=drive_size, id=0)]
    )

    with Progress() as progress:
        task = progress.add_task("[cyan]Creating VM...", total=100)
        result = asyncio.run(send_request(command.model_dump()))
        result = VMResponse(**result)
        progress.update(task, completed=100)

        if result.status == Status.OK:
            panel = Panel.fit(
                f"[green]Successfully created new VM[/green]\n"
                f"ID: {result.vm_id}\n"
                f"RAM: {result.data.ram}GB\n"
                f"CPU: {result.data.cpu} cores\n"
                f"Initial Drive: {result.data.hard_drives[0].size}GB\n"
                f"Status: {'Connected' if result.is_connected else 'Disconnected'}",
                title="VM Created"
            )
            console.print(panel)
        else:
            console.print(f"[red]Error: {result.message}[/red]")


@app.command()
def get_info(
        vm_id: int = typer.Option(..., help="VM ID")):
    command = GetInfoCommand(
        command=ManagerCommandType.GET_INFO,
        vm_id=vm_id
    )

    result = asyncio.run(send_request(command.model_dump()))
    result = VMResponse(**result)

    if result.status == Status.OK:
        table = Table(show_header=False, title=f"VM {vm_id} Information")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("ID", str(result.vm_id))
        table.add_row("RAM", f"{result.data.ram} GB")
        table.add_row("CPU", str(result.data.cpu))
        table.add_row("Status", "🟢 Authenticated" if result.is_connected else "🔴 Not Authenticated")
        table.add_row("Last Connected",
                      result.last_connection.strftime("%Y-%m-%d %H:%M:%S") if result.last_connection else "Never")

        drives_info = "\n".join([f"Drive {hd.id}: {hd.size}GB" for hd in result.data.hard_drives]) or "None"
        table.add_row("Hard Drives", drives_info)

        console.print(table)
    else:
        console.print(f"[red]Error: {result.message}[/red]")


@app.command()
def add_drive(
        vm_id: int = typer.Option(..., help="VM ID"),
        size: int = typer.Option(1, help="Drive size in GB")):
    command = AddDriveCommand(
        command=ManagerCommandType.ADD_DRIVE,
        vm_id=vm_id,
        size=size
    )

    with Progress() as progress:
        task = progress.add_task("[cyan]Adding drive...", total=100)
        result = asyncio.run(send_request(command.model_dump()))
        result = VMResponse(**result)
        progress.update(task, completed=100)

        if result.status == Status.OK:
            drives_table = Table(title="Updated Drives Configuration")
            drives_table.add_column("Drive ID", style="cyan")
            drives_table.add_column("Size", style="yellow")
            drives_table.add_column("VM ID", style="green")

            for drive in result.data.hard_drives:
                drives_table.add_row(
                    str(drive.id),
                    f"{drive.size}GB",
                    str(result.vm_id)
                )

            console.print(drives_table)
        else:
            console.print(f"[red]Error: {result.message}[/red]")


@app.command()
def logout(vm_id: int):
    command = LogoutClientCommand(vm_id=vm_id)

    try:
        result = asyncio.run(send_request(command.model_dump()))
        result = AuthResponse(**result)
        if result.status == Status.OK:
            console.print("[green]Logout successful[/green]")
        else:
            console.print(f"[red]Logout failed: {result.message}[/red]")
    except Exception as e:
        console.print(f"[red]Logout error: {str(e)}[/red]")


@app.command()
def update_vm(
        vm_id: int,
        ram: int | None = None,
        cpu: int | None = None):
    command = UpdateSpecsCommand(vm_id=vm_id, ram=ram, cpu=cpu)

    try:
        result = asyncio.run(send_request(command.model_dump()))
        result = VMResponse(**result)
        if result.status == Status.OK:
            console.print("[green]VM updated successfully[/green]")
        else:
            console.print(f"[red]VM update failed: {result.message}[/red]")
    except Exception as e:
        console.print(f"[red]VM update error: {str(e)}[/red]")


@app.command()
def list_drives(vm_id: int | None = None):
    command = ListDrivesCommand(vm_id=vm_id)

    try:
        result = asyncio.run(send_request(command.model_dump()))
        result = ListDrivesResponse(**result)
        if result.status == Status.OK:
            table = Table(title="Discs")
            table.add_column("ID", justify="right", style="cyan")
            table.add_column("VM ID", style="green")
            table.add_column("Volume (GB)", style="yellow")

            for drive in result.hds:
                table.add_row(str(drive.id), str(drive.vm_id), str(drive.size))
            console.print(table)
        else:
            console.print(f"[red]Drive listing failed: {result.message}[/red]")
    except Exception as e:
        console.print(f"[red]Drive listing error: {str(e)}[/red]")
        return []


@app.command(help="Update hard drive. \"0\" is default for creating a new drive")
def update_hd(vm_id: int, volume: int, id: int = 0):
    hd = HardDrive(vm_id=vm_id, id=id, size=volume)
    command = UpdateSpecsCommand(vm_id=vm_id, ram=None, cpu=None, hds=[hd])

    try:
        result = asyncio.run(send_request(command.model_dump()))
        result = VMResponse(**result)
        if result.status == Status.OK:
            console.print(f"[green]Drive updated successfully[/green]")
        else:
            console.print(f"[red]Drive update failed: {result.message}[/red]")
    except Exception as e:
        console.print(f"[red]Drive update error: {str(e)}[/red]")


# ----------- Client ------------

@app.command("start-client")
def start_client(
        vm_id: int = typer.Option(0, help="VM ID"),

        username: str = typer.Option("root", help="Логин для подключения"),
        password: str = typer.Option("root", help="Пароль для подключения"),
        ram: int = typer.Option(2, help="RAM в MB"),
        cpu: int = typer.Option(1, help="Количестыо ядер"),
        port: int = typer.Option(..., help="Порт для подключения"),
        drives: list[int] = typer.Option(None, help="Список объемов жестких дисков в GB")):
    initial_specs = VMSpecs(
        id=0,
        ram=ram,
        cpu=cpu,
        hard_drives=[HardDrive(size=4, id=0, vm_id=0)]
    )

    async def _start_vm():
        global vm_client

        if drives:
            for i, size in enumerate(drives, 1):
                initial_specs.hard_drives.append(HardDrive(size=size, id=vm_id * 10 + i))

        console.print(f"\nVM {vm_id} is starting on port {port}", style="green")
        console.print("Press Ctrl+C to stop", style="yellow")

        client_service = VMClientService(
            specs=initial_specs,
            username=username,
            password=password
        )

        client_handler = ClientCommandHandler(
            vm_service=client_service
        )
        client_server = VMServer(
            host="localhost",
            port=port,
            command_handler=client_handler
        )

        await client_server.start()

    try:
        asyncio.run(_start_vm())
    except KeyboardInterrupt:
        console.print("\nVM shutdown requested", style="yellow")
    except Exception as e:
        console.print(f"\nError: {e}", style="red")
    finally:
        console.print("VM stopped", style="green")
