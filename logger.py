import logging
import colors

class ColoredLevelFormatter(logging.Formatter):
    fmt = f"[{colors._green}%(name)s{colors._reset}][{{0}}%(levelname)s{colors._reset}][{colors._purple}%(asctime)s{colors._reset}]: %(message)s"

    FORMATS = {
        logging.DEBUG: fmt.format(colors._grey),
        logging.INFO: fmt.format(colors._blue),
        logging.WARNING: fmt.format(colors._yellow),
        logging.ERROR: fmt.format(colors._red),
        logging.CRITICAL: fmt.format(colors._bold_red)
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(
            log_fmt,
            datefmt="%d-%m %H:%M:%S"
        )
        return formatter.format(record)

class Logger(logging.Logger):
    def __init__(
        self,
        name: str
    ) -> None:
        super().__init__(name, logging.INFO)
        formatter = ColoredLevelFormatter()
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        self.addHandler(console_handler)