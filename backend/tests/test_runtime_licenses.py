"""Nothing the backend runs is under the GPL or the AGPL (#823, #824).

The repository is MIT-licensed. Two of its runtime dependencies were not
compatible with shipping it closed or relicensed: html2text (GPL-3.0-or-later)
and ebooklib (AGPL-3.0-or-later), both on the export path. Both are gone, and
this keeps the next one from arriving unnoticed.

The packages are the ones `uv export --no-dev` lists, which is what the image
installs. The licence is what each installed package declares about itself.
"""

import re
import subprocess
from importlib import metadata
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

# GPL or AGPL, abbreviated or spelled out, but not LGPL: a library under the LGPL
# may be used by a program under another licence.
STRONG_COPYLEFT = re.compile(r"(?<![A-Za-z])A?GPL|Affero|(?<!Lesser )(?<!Library )General Public License")


def _runtime_packages() -> list[str]:
    exported = subprocess.run(
        ["uv", "export", "--frozen", "--no-dev", "--no-emit-project", "--no-hashes", "--format", "requirements-txt"],
        cwd=BACKEND, capture_output=True, text=True, check=True,
    ).stdout
    return [re.split(r"[=<>!~;\[\s]", line, maxsplit=1)[0] for line in exported.splitlines() if re.match(r"[A-Za-z0-9]", line)]


def _declared_licence(package: str) -> str:
    """What the package says its licence is: the expression or short name, and its classifiers.

    Not the long form of `License`, which for some packages is the whole licence text and
    mentions other licences in passing.
    """
    declared = metadata.metadata(package)
    short = declared.get("License-Expression") or (declared.get("License") or "").strip().splitlines()[:1]
    classifiers = [c for c in declared.get_all("Classifier") or [] if c.startswith("License ::")]
    return " | ".join([short if isinstance(short, str) else "".join(short), *classifiers])


def test_the_pattern_tells_the_gpl_from_the_lgpl():
    for copyleft in ["GPL-3.0-or-later", "AGPL-3.0-or-later", "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
                     "License :: OSI Approved :: GNU Affero General Public License v3", "MIT OR GPL-2.0",
                     "GNU General Public License v3 or later", "GNU Affero General Public License"]:
        assert STRONG_COPYLEFT.search(copyleft), copyleft
    for fine in ["MIT", "Apache-2.0", "BSD-3-Clause", "LGPL-3.0-or-later", "MPL-2.0",
                 "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
                 "GNU Lesser General Public License v2.1", "GNU Library General Public License"]:
        assert not STRONG_COPYLEFT.search(fine), fine


def test_no_runtime_dependency_is_under_the_gpl_or_the_agpl():
    packages = _runtime_packages()
    installed, not_here = {}, []
    for package in packages:
        try:
            installed[package] = _declared_licence(package)
        except metadata.PackageNotFoundError:
            not_here.append(package)  # another platform's wheel, such as pywin32

    assert len(packages) > 30, f"the export listed only {len(packages)} packages; this guard is close to vacuous"
    assert len(not_here) <= 3, f"not installed here, so not checked: {not_here}"
    copyleft = {package: licence for package, licence in installed.items() if STRONG_COPYLEFT.search(licence)}
    assert not copyleft, copyleft
