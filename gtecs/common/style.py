"""Text colour and style functions."""


def rtxt(text):
    """Print red coloured text."""
    return '\033[31;1m' + str(text) + '\033[0m'


def gtxt(text):
    """Print green coloured text."""
    return '\033[32;1m' + str(text) + '\033[0m'


def ytxt(text):
    """Print yellow coloured text."""
    return '\033[33;1m' + str(text) + '\033[0m'


def btxt(text):
    """Print blue coloured text."""
    return '\033[34;1m' + str(text) + '\033[0m'


def ptxt(text):
    """Print purple coloured text."""
    return '\033[35;1m' + str(text) + '\033[0m'


def boldtxt(text):
    """Print bold text."""
    return '\033[1m' + str(text) + '\033[0m'


def undltxt(text):
    """Print underlined text."""
    return '\033[4m' + str(text) + '\033[0m'


def errortxt(message):
    """Print text prepended with a bold red ERROR."""
    return rtxt(boldtxt('ERROR')) + ': ' + str(message)
