import ast
from pathlib import Path

ROOT = Path(__file__).parents[2]
SRC = ROOT / "src" / "rag"


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def python_files(directory: str) -> list[Path]:
    return list((SRC / directory).rglob("*.py"))


def violations(directory: str, forbidden: tuple[str, ...]) -> list[str]:
    result = []
    for path in python_files(directory):
        for module in imported_modules(path):
            if module.startswith(forbidden):
                result.append(f"{path.relative_to(SRC)} -> {module}")
    return result


def test_use_cases_only_enter_business_dependencies_through_services() -> None:
    assert (
        violations(
            "use_cases",
            (
                "rag.use_cases",
                "rag.repositories",
                "rag.resources",
                "rag.api",
                "rag.worker",
            ),
        )
        == []
    )


def test_services_do_not_reach_outward_or_skip_to_resources() -> None:
    assert (
        violations(
            "services",
            ("rag.use_cases", "rag.resources", "rag.api", "rag.worker"),
        )
        == []
    )


def test_repositories_only_use_service_contracts_and_types() -> None:
    result = violations(
        "repositories",
        ("rag.use_cases", "rag.api", "rag.worker"),
    )
    for path in python_files("repositories"):
        for module in imported_modules(path):
            if module.startswith("rag.services.") and not (
                ".interfaces." in module or ".types." in module
            ):
                result.append(f"{path.relative_to(SRC)} -> {module}")
    assert result == []


def test_worker_handlers_delegate_to_use_cases() -> None:
    assert (
        violations(
            "worker/handlers",
            ("rag.repositories", "rag.resources", "rag.api"),
        )
        == []
    )


def test_removed_layer_names_are_not_imported() -> None:
    result = []
    for root in (ROOT / "src", ROOT / "tests", ROOT / "alembic"):
        for path in root.rglob("*.py"):
            for module in imported_modules(path):
                if module.startswith(
                    ("rag.core", "rag.interfaces", "rag.infrastructure")
                ):
                    result.append(f"{path.relative_to(ROOT)} -> {module}")
    assert result == []


def test_dataclasses_live_in_service_type_packages() -> None:
    result = []
    for path in python_files("."):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if any(
            isinstance(node, ast.Name) and node.id == "dataclass"
            for node in ast.walk(tree)
        ) and not (path.is_relative_to(SRC / "services") and "types" in path.parts):
            result.append(str(path.relative_to(SRC)))
    assert result == []
