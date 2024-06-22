import os
from pathlib import Path

from opendevin.core.config import config
from opendevin.core.logger import opendevin_logger as logger
from opendevin.events.observation import (
    CodebasesLoadedObservation,
    ErrorObservation,
    FileReadObservation,
    FileWriteObservation,
    Observation,
)


def resolve_path(file_path, working_directory):
    # Expand any '~' in the path to the user's home directory
    path_in_sandbox = Path(file_path).expanduser()

    # Apply working directory
    if not path_in_sandbox.is_absolute():
        path_in_sandbox = Path(working_directory) / path_in_sandbox

    # Sanitize the path with respect to the root of the full sandbox
    # (deny any .. path traversal to parent directories of the sandbox)
    abs_path_in_sandbox = path_in_sandbox.resolve()

    # If the path is outside the workspace, deny it
    if not abs_path_in_sandbox.is_relative_to(config.workspace_mount_path_in_sandbox):
        raise PermissionError(f'File access not permitted: {file_path}')

    # Get path relative to the root of the workspace inside the sandbox
    path_in_workspace = abs_path_in_sandbox.relative_to(
        Path(config.workspace_mount_path_in_sandbox)
    )

    # Get path relative to host
    path_in_host_workspace = (
        Path(config.workspace_base).expanduser() / path_in_workspace
    )

    return path_in_host_workspace


def read_lines(all_lines: list[str], start=0, end=-1):
    start = max(start, 0)
    start = min(start, len(all_lines))
    end = -1 if end == -1 else max(end, 0)
    end = min(end, len(all_lines))
    if end == -1:
        if start == 0:
            return all_lines
        else:
            return all_lines[start:]
    else:
        num_lines = len(all_lines)
        begin = max(0, min(start, num_lines - 2))
        end = -1 if end > num_lines else max(begin + 1, end)
        return all_lines[begin:end]


async def read_file(path, workdir, start=0, end=-1) -> Observation:
    try:
        whole_path = resolve_path(path, workdir)
    except PermissionError:
        return ErrorObservation(
            f"You're not allowed to access this path: {path}. You can only access paths inside the workspace."
        )

    try:
        with open(whole_path, 'r', encoding='utf-8') as file:
            lines = read_lines(file.readlines(), start, end)
    except FileNotFoundError:
        return ErrorObservation(f'File not found: {path}')
    except UnicodeDecodeError:
        return ErrorObservation(f'File could not be decoded as utf-8: {path}')
    except IsADirectoryError:
        return ErrorObservation(f'Path is a directory: {path}. You can only read files')
    code_view = ''.join(lines)
    return FileReadObservation(path=path, content=code_view)


def insert_lines(
    to_insert: list[str], original: list[str], start: int = 0, end: int = -1
):
    """
    Insert the new content to the original content based on start and end
    """
    new_lines = [''] if start == 0 else original[:start]
    new_lines += [i + '\n' for i in to_insert]
    new_lines += [''] if end == -1 else original[end:]
    return new_lines


async def write_file(path, workdir, content, start=0, end=-1) -> Observation:
    insert = content.split('\n')

    try:
        whole_path = resolve_path(path, workdir)
        if not os.path.exists(os.path.dirname(whole_path)):
            os.makedirs(os.path.dirname(whole_path))
        mode = 'w' if not os.path.exists(whole_path) else 'r+'
        try:
            with open(whole_path, mode, encoding='utf-8') as file:
                if mode != 'w':
                    all_lines = file.readlines()
                    new_file = insert_lines(insert, all_lines, start, end)
                else:
                    new_file = [i + '\n' for i in insert]

                file.seek(0)
                file.writelines(new_file)
                file.truncate()
        except FileNotFoundError:
            return ErrorObservation(f'File not found: {path}')
        except IsADirectoryError:
            return ErrorObservation(
                f'Path is a directory: {path}. You can only write to files'
            )
        except UnicodeDecodeError:
            return ErrorObservation(f'File could not be decoded as utf-8: {path}')
    except PermissionError:
        return ErrorObservation(f'Malformed paths not permitted: {path}')
    return FileWriteObservation(content='', path=path)


async def load_codebases_xml(
    codebase_locations: list[str], working_directory: str, extensions: list[str]
) -> Observation:
    """
    Load the codebase XML representation from the given directories and their subdirectories
    that match the specified file extensions.

    Args:
        codebase_locations (List[str]): A list of directory paths to search for files, relative to root_directory.
        working_directory (str): working directory.
        extensions (List[str]): A list of file extension strings to include (e.g., ['py', 'txt']).

    Preconditions:
        - The codebase_locations list contains valid directory paths.
        - The codebase_locations paths are inside the workspace.
        - The extensions list contains valid file extension strings.

    Side effects:
        None

    Exceptions:
        None

    Returns:
        str: The XML representation of the codebase.
        guarantees: The returned string will be a valid XML representation of the codebase.
    """
    print(
        f'Loading codebase from locations {codebase_locations} with extensions {extensions}'
    )

    codebase_xml = '<codebase>\n'

    encodings = ['utf-8', 'cp1252', 'iso-8859-1']

    for path in codebase_locations:
        print(
            f'Resolving path {path} with respect to working directory {working_directory}.'
        )

        try:
            whole_path_codebase = resolve_path(path, working_directory)
        except PermissionError:
            return ErrorObservation(
                f"You're not allowed to access this path: {path}. You can only access paths inside the workspace."
            )

        print(f'Loading codebase from path {whole_path_codebase}')

        codebase_xml += '<codebase_subfolder>\n'

        try:
            # Walk through the directory and subdirectories recursively
            for root_path, _, files in os.walk(whole_path_codebase):
                print(f'Loading files from {root_path}')

                if '__pycache__' not in root_path:
                    for file_name in files:
                        # Check whether it is a file or directory
                        # is_file = os.path.isfile(os.path.join(root, file_name))

                        if (
                            # is_file and
                            any(file_name.endswith(f'.{ext}') for ext in extensions)
                            or extensions == []
                        ):
                            print(f'Loading file {file_name}; abs')
                            file_path_absolute = os.path.join(root_path, file_name)
                            file_path_relative = os.path.relpath(
                                file_path_absolute, working_directory
                            )

                            file_loaded = False
                            for encoding in encodings:
                                try:
                                    with open(
                                        file_path_absolute, 'r', encoding=encoding
                                    ) as file:
                                        contents = file.read()
                                        codebase_xml += (
                                            f'<file>\n'
                                            f'<path>{file_path_relative}</path>\n'
                                            f'<content>{contents}</content>\n'
                                            f'</file>\n'
                                        )
                                        file_loaded = True
                                        break
                                except (OSError, IOError) as e:
                                    logger.error(
                                        f'Error reading file {file_path_absolute} with encoding {encoding}: {e}'
                                    )

                            if not file_loaded:
                                logger.error(
                                    f'Failed to load file {file_path_absolute} with any encoding.'
                                )
        except FileNotFoundError:
            return ErrorObservation(f'File not found: {path}')
        except UnicodeDecodeError:
            return ErrorObservation(f'File could not be decoded as utf-8: {path}')

        codebase_xml += '</codebase_subfolder>\n'

    codebase_xml += '</codebase>\n'

    return CodebasesLoadedObservation(
        content=codebase_xml,
        codebase_relative_paths=codebase_locations,
        root_directory=working_directory,
        extensions=extensions,
    )
