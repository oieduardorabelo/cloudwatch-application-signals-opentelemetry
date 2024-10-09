import logging


class ProjectNameVersionFilter(logging.Filter):
    def __init__(
        self,
        project_name: str,
        project_version: str,
    ):
        super().__init__()
        self.project_name = project_name
        self.project_version = project_version

    def filter(self, record: logging.LogRecord) -> bool:
        record.project_name = self.project_name
        record.project_version = self.project_version
        return True
