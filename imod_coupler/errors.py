class ConfigError(RuntimeError):
    """An error encountered during reading the config file

    Args:
        msg (str): The message displayed to the user on error
    """

    def __init__(self, msg: str):
        super().__init__("%s" % (msg,))
