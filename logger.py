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
    fmt = "[{2}%(name)s{1}][{0}%(levelname)s{1}][{3}%(asctime)s{1}]: %(message)s"

    FORMATS = {
        logging.DEBUG: fmt.format(grey, reset, green, purple),
        logging.INFO: fmt.format(blue, reset, green, purple),
        logging.WARNING: fmt.format(yellow, reset, green, purple),
        logging.ERROR: fmt.format(red, reset, green, purple),
        logging.CRITICAL: fmt.format(bold_red, reset, green, purple)
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