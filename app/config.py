import os
from pydantic import BaseModel, AnyHttpUrl, ValidationError
from dotenv import load_dotenv


class Settings(BaseModel):
    ext_api_base_url: AnyHttpUrl
    ext_api_token: str


def get_settings() -> Settings:
    load_dotenv()
    try:
        return Settings(
            ext_api_base_url=os.environ.get("EXT_API_BASE_URL", "http://localhost:8099"),
            ext_api_token=os.environ["EXT_API_TOKEN"],
        )
    except KeyError as exc:
        missing = str(exc)
        raise RuntimeError(f"Missing required environment variable: {missing}") from exc
    except ValidationError as exc:
        raise RuntimeError(f"Invalid configuration: {exc}") from exc

