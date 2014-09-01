""" Exception classes for panzer """

class PanzerError(Exception):
    """ base class for all panzer exceptions """
    pass

class SetupError(PanzerError):
    """ error in the setup phase """
    pass

class BadASTError(PanzerError):
    """ malformatted AST encountered (e.g. C or T fields missing) """
    pass

class MissingField(PanzerError):
    """ looked for metadata field, did not find it """
    pass

class WrongType(PanzerError):
    """ looked for value of a type, encountered different type """
    pass

class InternalError(PanzerError):
    """ function invoked with invalid parameters """
    pass

