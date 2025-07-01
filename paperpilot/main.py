import uvicorn

from paperpilot.api.app import create_app
from paperpilot.core.config import settings


def main() -> None:
    app = create_app()
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
