# Third-party dependency license review

Reviewed 2026-10-27 against the upstream project license/metadata links below. The repository does not vendor Python packages, wheels, Python runtimes, or their source. Runtime dependencies are installed by the user; CI installs them on the runner.

| Direct dependency | Use | Upstream license | Review |
|---|---|---|---|
| Pillow | Bitmap rendering and PNG preview | MIT-CMU | Permissive; retain notices if redistributed. |
| python-barcode | Code128 preview rendering | MIT | Permissive; retain notice if redistributed. |
| qrcode | QR preview rendering | BSD 3-Clause, with upstream historical MIT notice retained in its LICENSE | Permissive; preserve upstream license file if bundling. |
| pywin32 (Windows optional) | `win32print` RAW spooler API only | `win32/License.txt` BSD-style terms; other pywin32 components may have different licenses | This project does not bundle pywin32. If bundling the complete distribution, review every included component/license file. |
| pytest (development) | Software tests | MIT | Development-only dependency. |
| actions/checkout, actions/setup-python | CI workflow | MIT | CI-only actions; neither is vendored into the application. |

Sources: [Pillow LICENSE](https://github.com/python-pillow/Pillow/blob/main/LICENSE), [python-barcode metadata and license](https://github.com/WhyNotHugo/python-barcode/blob/main/pyproject.toml), [python-barcode LICENSE](https://github.com/WhyNotHugo/python-barcode/blob/main/LICENCE), [qrcode LICENSE](https://github.com/lincolnloop/python-qrcode/blob/main/LICENSE), [pywin32 win32 module license](https://raw.githubusercontent.com/mhammond/pywin32/main/win32/License.txt), [pytest license](https://github.com/pytest-dev/pytest/blob/main/doc/en/license.rst), [checkout license](https://github.com/actions/checkout/blob/main/LICENSE), [setup-python license](https://github.com/actions/setup-python/blob/main/LICENSE).

Scope limit: version ranges are not a lockfile, so a future resolved environment may add or change transitive dependencies. Before shipping an installer or bundled runtime, resolve and archive the exact package/license inventory (including pywin32 module files) and re-review it. This engineering inventory is not legal advice.

## R3 clean-install inventory

Validated in a fresh project-local `.venv` using Python 3.12.13 and `pip install -r requirements.txt` on Windows (2026-10-27). The resolved environment was:

| Package | Resolved version | Role | License evidence / note |
|---|---:|---|---|
| Pillow | 12.3.0 | Direct runtime | MIT-CMU; wheel includes its `dist-info/licenses/LICENSE`. |
| python-barcode | 0.16.1 | Direct runtime | MIT; wheel includes `LICENCE`. |
| qrcode | 8.2 | Direct runtime | BSD (upstream license file); wheel includes `dist-info/LICENSE`. |
| pywin32 | 312 | Windows direct runtime | Mixed-license distribution. The RAW path uses `win32print` under `win32/License.txt` (BSD-style terms), while the complete wheel also carries other component notices, including LGPL-2.1 for `adodbapi` and separate Pythonwin/Scintilla notices. Do not strip notices or redistribute a partial wheel. |
| pytest | 9.1.1 | Direct development | MIT; wheel includes its license file. |
| colorama | 0.4.6 | Transitive (Windows) | BSD 3-Clause. |
| iniconfig | 2.3.1 | Transitive (pytest) | MIT. |
| packaging | 26.3 | Transitive (pytest) | Apache-2.0 OR BSD-2-Clause; both license texts are present in the wheel. |
| pluggy | 1.7.0 | Transitive (pytest) | MIT. |
| Pygments | 2.21.0 | Transitive (pytest) | BSD-2-Clause. |

`pip` 25.0.1 was the venv bootstrap tool and is not declared by the project. No dependency wheel, runtime, `site-packages`, or generated environment is part of the candidate Git tree. The project is distributed as source, with user-installed requirements; no wheel, installer, or bundled runtime is built here. The version ranges in `requirements.txt` remain intentionally unpinned, so this inventory documents the tested resolution and is not a future lockfile.

Resolved-license source references: [Pillow MIT-CMU](https://github.com/python-pillow/Pillow/blob/main/LICENSE), [python-barcode LICENSE](https://github.com/WhyNotHugo/python-barcode/blob/main/LICENCE), [qrcode LICENSE](https://github.com/lincolnloop/python-qrcode/blob/main/LICENSE), [pywin32 license scope](https://github.com/mhammond/pywin32/blob/main/README.md), [pywin32 win32 license](https://github.com/mhammond/pywin32/blob/main/win32/License.txt), [pytest MIT](https://github.com/pytest-dev/pytest/blob/main/doc/en/license.rst), [Colorama BSD-3-Clause](https://github.com/tartley/colorama/blob/master/pyproject.toml), [iniconfig MIT](https://github.com/pytest-dev/iniconfig/blob/main/LICENSE), [packaging dual license](https://github.com/pypa/packaging/blob/main/LICENSE), [pluggy MIT](https://github.com/pytest-dev/pluggy/blob/main/LICENSE), [Pygments BSD-2-Clause](https://github.com/pygments/pygments/blob/master/LICENSE).
