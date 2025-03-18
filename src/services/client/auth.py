import logging
from abc import ABC
from abc import abstractmethod
import core.log_cfg

logger = logging.getLogger(__name__)


class AuthClientServiceBase(ABC):
    authorized_servers: set[str]

    @abstractmethod
    async def authenticate(self, username: str, password: str, peer: str) -> bool:
        pass

    @abstractmethod
    async def is_authorized(self, peer: str) -> bool:
        pass

    @abstractmethod
    async def remove_authorization(self, peer: str):
        pass


class AuthClientService(AuthClientServiceBase):
    def __init__(self, username: str, password: str, authorized_servers: set[str]):
        self.username = username
        self.password = password
        self.authorized_servers = authorized_servers

    async def authenticate(self, username: str, password: str, peer: str) -> bool:
        logger.info(f"Authenticating {username} from {peer}")
        if check := username == self.username and self.password == password:
            self.authorized_servers.add(str(peer))
        logging.log(logging.INFO, f"Authorization status: {check}")
        return check

    async def is_authorized(self, peer: str) -> bool:
        logging.log(logging.INFO, f"Checking authorization for {peer}")
        logging.log(logging.DEBUG, f"Authorized hosts: {self.authorized_servers}")
        return str(peer) in self.authorized_servers

    async def remove_authorization(self, peer: str):
        logging.log(logging.INFO, f"Removing authorization for {peer}")
        if str(peer) in self.authorized_servers:
            self.authorized_servers.remove(str(peer))
