# TSPL Label Desk

A small Windows desk for quickly composing, previewing, calibrating, and printing custom TSPL labels locally.

![TSPL Label Desk interface](docs/images/label-desk.jpg)

**Quick pick. Live preview. Paper calibration.** Choose a saved product or location and preset dimensions, or switch to free text. The same previewed label content is used for output.

## Quick start (Windows)

1. Install Python 3.10+ yourself.
2. Double-click `setup.cmd`. It creates `.venv` inside this project and installs the declared Python packages there only.
3. Double-click `start.cmd`, then open [http://127.0.0.1:8630](http://127.0.0.1:8630).

The default backend saves TSPL files under `.runtime-data/outbox` and never contacts a printer. Windows RAW output is opt-in with `--backend windows`; set the queue in Printer Profile before choosing output. LAN access is disabled unless explicitly started with `--lan --host 0.0.0.0` and requires the temporary token printed to the console.

## Printer verification

The included generic profile is **UNVERIFIED**. Sanitized 203 DPI output is compared with legacy software fixtures; 300 DPI is software-tested. No printer/firmware combination is claimed compatible without documented physical output and measurement. Software tests do not replace a hardware test.

## Quick labels and configuration

The bundled product and warehouse examples are generic. Edit `profiles/quick-label-templates.json` to define one to three preset dimensions per template. Maintain selectable products in Model Management. User settings are stored locally under `.runtime-data` and are not part of the source package. Profile calibration is authoritative; `paper.json` is maintained as a compatibility mirror.

## More information

- [Windows run, stop, and diagnosis](docs/windows.md)
- [Compatibility tests and evidence](docs/compatibility.md)
- [Compatibility status matrix](docs/compatibility-matrix.md)
- [Dependency license inventory](docs/licenses.md)

## Development

Run `python -m pytest -q`. The UI is static HTML/CSS/JavaScript and needs no Node build. `setup.cmd` does not install Python or Windows components and does not modify global Python packages.

## License

MIT; see [LICENSE](LICENSE) and the [dependency license inventory](docs/licenses.md).
