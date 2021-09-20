from typing import TYPE_CHECKING, List

from cleo.helpers import option

from poetry_workspace.commands.workspace.workspace import WorkspaceCommand

if TYPE_CHECKING:
    from cleo.io.io import IO
    from poetry.core.packages.package import Package
    from poetry.poetry import Poetry

_FORMATS = (
    "topological",
    "json",
    "tree",
)


class WorkspaceListCommand(WorkspaceCommand):
    name = "workspace list"
    description = "Lists workspace projects and their dependencies."
    help = """
The <info>workspace list</> command lists projects in the workspace's dependency
graph. Use flags to optionally select a subset of projects, and to output
their dependencies, reverse dependencies, and whether to include projects
external to the workspace in the dependency list."""

    options = [
        option("output", "o", f"Output format ({', '.join(_FORMATS)}).", flag=False, default=_FORMATS[0]),
        option("show-external", None, "Show external dependencies in the output."),
    ] + WorkspaceCommand.options

    def __init__(self):
        super().__init__()

        # Used for json and tree output formats.
        self._project_tree = {}

    @property
    def output(self) -> str:
        return self.option("output")

    def pre_handle(self) -> int:
        if self.output not in _FORMATS:
            self.line("unknown output format", style="error")
            return 1
        return 0

    def handle_each(self, poetry: "Poetry", _io: "IO") -> int:
        package = poetry.package
        if self.output == "topological":
            self.line(package.name)
            return 0

        def get_tree(package: "Package") -> dict:
            return {dep.name: get_tree(dep) for dep in self.graph.dependencies(package)}

        self._project_tree[package.name] = get_tree(package)
        return 0

    def post_handle(self) -> int:
        if self.output == "json":
            import json

            self.line(json.dumps(self._project_tree, indent=2))
        elif self.output == "tree":
            for project_name, tree in self._project_tree.items():
                self.write_tree(project_name, tree, 0, False)
                self.line("")

        return 0

    def write_tree(self, project_name: str, tree: dict, levels: int, last_item: bool) -> None:
        for level in range(levels):
            if level != levels - 1:
                self.io.write("│   ")
            elif not last_item:
                self.io.write("├── ")
            else:
                self.io.write("└── ")

        self.line(project_name)
        for i, (dep_name, dep_tree) in enumerate(tree.items()):
            self.write_tree(dep_name, dep_tree, levels + 1, i == len(tree) - 1)

    def selected_projects(self, *args) -> List["Package"]:
        projects = super().selected_projects(self.option("show-external"))
        if self.output in ("json", "tree"):
            projects = sorted(projects, key=lambda project: project.name)
        return projects
