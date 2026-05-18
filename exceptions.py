
class MissingRequiredEnvironmentVariable(RuntimeError):
    def __init__(self, required: list[str]):
        super().__init__("Environment variables '{}' is required".format(', '.join(required)))