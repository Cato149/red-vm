import os

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DB(BaseModel):
    # WARN: Default values for easy sturtup (not good idea in a prod apps)
    user: str = 'username'
    password: str = 'password'
    name: str = 'red_vm'
    host: str = '0.0.0.0'
    port: int = 5432


class Settings(BaseSettings):
    # TIP: You can add `env_path` in env variables to add path to cfg file
    model_config = SettingsConfigDict(env_file=os.getenv("env_path"), env_file_encoding='utf-8')

    # VM Server config
    host: str = Field(default="localhost")
    port: int = Field(default=8888)

    db: DB = DB()

    def conn_str(self):
        return f"postgresql://{self.db.user}:{self.db.password}@{self.db.host}:{self.db.port}/{self.db.name}"
