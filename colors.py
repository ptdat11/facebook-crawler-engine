_grey = "\033[37m"
_blue = "\x1b[34;20m"
_yellow = "\x1b[33;20m"
_red = "\x1b[31;20m"
_bold = "\x1b[;1m"
_reset = "\x1b[0m"
_purple = "\x1b[35;20m"
_green = "\x1b[32;20m"
_bold_red = "\x1b[31;1m"

def grey(text : str):
    global _grey, _reset
    return f"{_grey}{text}{_reset}"

def blue(text: str):
    global _blue, _reset
    return f"{_blue}{text}{_reset}"

def yellow(text: str):
    global _yellow, _reset
    return f"{_yellow}{text}{_reset}"

def red(text: str):
    global _red, _reset
    return f"{_red}{text}{_reset}"

def bold(text: str):
    global _bold, _reset
    return f"{_bold}{text}{_reset}"

def purple(text: str):
    global _purple, _reset
    return f"{_purple}{text}{_reset}"

def green(text: str):
    global _green, _reset
    return f"{_green}{text}{_reset}"