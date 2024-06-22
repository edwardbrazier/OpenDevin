from dataclasses import dataclass

from opendevin.core.schema import ObservationType

from .observation import Observation


@dataclass
class FileReadObservation(Observation):
    """
    This data class represents the content of a file.
    """

    path: str
    observation: str = ObservationType.READ

    @property
    def message(self) -> str:
        return f'I read the file {self.path}.'


@dataclass
class FileWriteObservation(Observation):
    """
    This data class represents a file write operation
    """

    path: str
    observation: str = ObservationType.WRITE

    @property
    def message(self) -> str:
        return f'I wrote to the file {self.path}.'


@dataclass
class CodebasesLoadedObservation(Observation):
    """
    This data class represents findings from loading
    some codebases in XML format.
    """

    root_directory: str
    codebase_relative_paths: list[str]
    extensions: list[str] = []
    observation: str = ObservationType.CODEBASES_LOADED

    @property
    def message(self) -> str:
        return f'I loaded the files with extensions {self.extensions} from codebases from {self.codebase_relative_paths} in the root directory {self.root_directory}.'
