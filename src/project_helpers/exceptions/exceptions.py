from project_helpers.error import Error


class ErrorException(Exception):
    def _init_(self, error: Error, message=None, statusCode=500, fields=None):
        self.error = error
        self.message = message
        self.statusCode = statusCode
        self.fields = fields
