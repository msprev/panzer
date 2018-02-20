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

class BadArgsFormat(PanzerError):
    """ args field for item in run list has incorrect format """
    pass

class NoArgsAllowed(PanzerError):
    """ no command line arguments allowed to be passed to lua filters """
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

class StrictModeError(PanzerError):
    """
    An error on `---strict` mode that causes panzer to exit
    - On `--strict` mode: exception raised if any error of level 'ERROR' or
    above is logged
    - Without `--strict` mode: exception never raised
    """
    pass
