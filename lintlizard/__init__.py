import argparse
import subprocess
from typing import Iterable, Optional, Tuple

from attr import attrib, attrs

__version__ = '0.1.0'


Command = Tuple[str, ...]


@attrs(frozen=True)
class CommandTool:
    executable: str = attrib()
    run_params: Command = attrib(default=())
    fix_params: Optional[Command] = attrib(default=None)
    allow_specify_files: bool = attrib(default=True)

    def run_command(self) -> Command:
        return (self.executable,) + self.run_params

    @property
    def fixable(self):
        return self.fix_params is not None

    def fix_command(self) -> Command:
        if self.fix_params is None:
            raise RuntimeError('Command is not fixable')
        return (self.executable,) + self.fix_params

    def version_command(self) -> Command:
        return self.executable, '--version'


TOOLS = [
    CommandTool('flake8'),
    CommandTool('isort', run_params=('-c',), fix_params=tuple()),
    CommandTool('mypy', allow_specify_files=False),
    CommandTool('black', run_params=('--check',), fix_params=tuple()),
]


def execute_tools(fix: bool, files: Tuple[str, ...]) -> Iterable[bool]:
    tools = TOOLS
    if fix:
        tools = [tool for tool in tools if tool.fixable]
    for tool in tools:
        print('*' * 79)
        try:
            subprocess.run(args=tool.version_command(), check=True)
            cmd = (
                tool.fix_command()
                if fix and tool.fix_params is not None
                else tool.run_command()
            )
            subprocess.run(args=cmd + files, check=True)
        except subprocess.CalledProcessError:
            yield False
        else:
            yield True


def get_changed_files() -> Iterable[str]:
    try:
        subprocess.run(args=['git', '--version'], check=True)
        result = subprocess.run(
            args=[
                "git",
                "diff",
                "--name-only",
                "--cached",
                "--diff-filter=d",
                "HEAD",
                "--",
                "*.py",
            ],
            stdout=subprocess.PIPE,
        )
        return result.stdout.decode('utf8').strip().split('\n')
    except subprocess.CalledProcessError:
        raise Exception('Error encountered when determining changed files.')


def main() -> None:
    args = make_arg_parser().parse_args()
    files = args.files or []
    if args.changed:
        files.extend(get_changed_files())

    if not files:
        files = ['.']

    tool_results = list(execute_tools(fix=args.fix, files=tuple(files)))
    if not all(tool_results):
        exit(1)


def make_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fix', action='store_true')
    parser.add_argument('--changed', action='store_true')
    parser.add_argument('files', nargs='*', default=None)

    return parser


if __name__ == '__main__':
    main()
