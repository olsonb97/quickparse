class QuickparserError(Exception):
    def __init__(self, message=""):
        super().__init__(message)

class ParsingError(Exception):
    def __init__(self, message=""):
        super().__init__(message)