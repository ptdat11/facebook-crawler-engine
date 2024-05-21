import logging

class ColoredLevelFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    blue = "\x1b[34;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    purple = "\x1b[35;20m"
    green = "\x1b[32;20m"
    fmt = f"[{green}%(name)s{reset}][{{0}}%(levelname)s{reset}][{purple}%(asctime)s{reset}]: %(message)s"

    FORMATS = {
        logging.DEBUG: fmt.format(grey),
        logging.INFO: fmt.format(blue),
        logging.WARNING: fmt.format(yellow),
        logging.ERROR: fmt.format(red),
        logging.CRITICAL: fmt.format(bold_red)
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