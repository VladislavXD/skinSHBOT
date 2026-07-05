# core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	token: str
	admin_id: int = 0

	# PostgreSQL database settings
	PGUSER: str = ""
	PGPASSWORD: str = ""
	PGHOST: str = ""
	PGPORT: int = 5432
	PGDATABASE: str = ""


	model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

	@property
	def db_url(self) -> str:
			if self.PGUSER and self.PGPASSWORD and self.PGHOST and self.PGDATABASE:
					return (
							f"postgres://{self.PGUSER}:{self.PGPASSWORD}"
							f"@{self.PGHOST}:{self.PGPORT}/{self.PGDATABASE}"
					)
			return "sqlite://db.sqlite3"


settings = Settings()