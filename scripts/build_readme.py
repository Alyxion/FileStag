#!/usr/bin/env python3
"""Build README.md from template.

Generates two versions:
- README.md: For GitHub (relative paths)
- README_PYPI.md: For PyPI (absolute GitHub URLs)

Extracts version and other metadata from pyproject.toml.
"""

import re
import tomllib
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
TEMPLATE_FILE = PROJECT_DIR / "docs" / "README_template.md"
PYPROJECT_FILE = PROJECT_DIR / "pyproject.toml"

GITHUB_REPO = "scistag/filestag"
GITHUB_RAW_PREFIX = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/"
GITHUB_TREE_PREFIX = f"https://github.com/{GITHUB_REPO}/tree/main/"
GITHUB_BLOB_PREFIX = f"https://github.com/{GITHUB_REPO}/blob/main/"


def get_project_metadata() -> dict:
    """Extract metadata from pyproject.toml."""
    with open(PYPROJECT_FILE, "rb") as f:
        pyproject = tomllib.load(f)

    project = pyproject.get("project", {})
    version = project.get("version", "0.0.0")
    description = project.get("description", "")
    requires_python = project.get("requires-python", ">=3.12")

    # Extract minimum Python version from requires-python
    match = re.search(r">=?(\d+\.\d+)", requires_python)
    python_version = match.group(1) if match else "3.12"

    return {
        "VERSION": version,
        "PYTHON_VERSION": python_version,
        "DESCRIPTION": description,
    }


def build_readme(template: str, metadata: dict, for_pypi: bool = False) -> str:
    """Build README content from template.

    :param template: Template content
    :param metadata: Project metadata dict
    :param for_pypi: If True, use absolute GitHub URLs; otherwise relative paths
    :return: Processed README content
    """
    content = template

    # Replace metadata placeholders
    for key, value in metadata.items():
        content = content.replace(f"{{{{{key}}}}}", value)

    if for_pypi:
        # PyPI version: absolute URLs
        content = content.replace("{{ASSETS_PREFIX}}", GITHUB_RAW_PREFIX)
        content = content.replace("{{GITHUB_PREFIX}}", GITHUB_BLOB_PREFIX)
        content = content.replace("{{DOCS_PREFIX}}", GITHUB_TREE_PREFIX)
        content = content.replace("{{DOCS_SUFFIX}}", "")
    else:
        # GitHub version: relative paths
        content = content.replace("{{ASSETS_PREFIX}}", "")
        content = content.replace("{{GITHUB_PREFIX}}", "")
        content = content.replace("{{DOCS_PREFIX}}", "")
        content = content.replace("{{DOCS_SUFFIX}}", "/")

    return content


def main():
    """Build README files from template."""
    if not TEMPLATE_FILE.exists():
        print(f"Error: Template not found at {TEMPLATE_FILE}")
        return 1

    if not PYPROJECT_FILE.exists():
        print(f"Error: pyproject.toml not found at {PYPROJECT_FILE}")
        return 1

    template = TEMPLATE_FILE.read_text()
    metadata = get_project_metadata()

    print(f"Project version: {metadata['VERSION']}")
    print(f"Python version: {metadata['PYTHON_VERSION']}")

    # Build GitHub README
    readme_content = build_readme(template, metadata, for_pypi=False)
    readme_file = PROJECT_DIR / "README.md"
    readme_file.write_text(readme_content)
    print(f"Generated {readme_file}")

    # Build PyPI README
    pypi_content = build_readme(template, metadata, for_pypi=True)
    pypi_file = PROJECT_DIR / "README_PYPI.md"
    pypi_file.write_text(pypi_content)
    print(f"Generated {pypi_file}")

    return 0


if __name__ == "__main__":
    exit(main())
