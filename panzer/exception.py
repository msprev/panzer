# Exception classes

class PanzerError(Exception):
    """ base class for all panzer exceptions """
    pass

class PanzerSetupError(PanzerError):
    """ error in the setup phase """
    pass

class PanzerBadASTError(PanzerError):
    """ malformatted AST encountered (e.g. C or T fields missing) """
    pass

class PanzerKeyError(PanzerError):
    """ looked for metadata field, did not find it """
    pass

class PanzerTypeError(PanzerError):
    """ looked for value of a type, encountered different type """
    pass

class PanzerInternalError(PanzerError):
    """ function invoked with invalid parameters """
    pass

