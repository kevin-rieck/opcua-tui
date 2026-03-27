import logging

from opcua_tui.infrastructure.logging_config import setup_logging
from opcua_tui.ui.textual_app import run

logger = logging.getLogger(__name__)


def main() -> None:
    log_file = setup_logging()
    logger.info("Application startup", extra={"operation": "startup", "log_file": str(log_file)})
    run()


if __name__ == "__main__":
    main()
