# Windows install, run, stop, and diagnose

The application targets Python 3.10+ and uses a static HTML/CSS/JavaScript UI. There is no Node build.

```powershell
.\setup.cmd
.\.venv\Scripts\Activate.ps1
python src\app.py
```

`setup.cmd` creates a project-local virtual environment if needed and installs dependencies only into that environment. It does not install Python or modify system/global packages.

Open `http://127.0.0.1:8630/`. The default `file` backend writes `.runtime-data/outbox/*.tspl`; it never calls a printer. Profiles, model list, and paper measurements are kept under `.runtime-data` and excluded by `.gitignore`.

For a printer, install the Windows driver yourself and start `python src\app.py --backend windows`. Save the exact queue name under Printer Profile. Only pressing **Save / print** submits a Windows RAW spooler job. The test suite uses a mocked spooler and does not enumerate or print to real queues.

LAN is disabled by default. For a trusted LAN, start `python src\app.py --lan --host 0.0.0.0`. The server prints local URLs and an ephemeral bearer token; enter the token into the page. Token-protect API reads and writes, request-size limits, origin checks, bounded concurrent requests, socket timeout, and print rate limiting are enabled. Use Windows Firewall to limit access to a trusted subnet; do not port-forward this service.

`start.cmd` opens the service in a separate console. Close that console or run `stop.cmd` to stop only Python processes whose command line points to this project's `src\app.py`. `diagnose.cmd` reports required optional modules and whether port 8630 is listening; it does not print configuration values.

Use `python -m pytest -q --basetemp=reports\.pytest-tmp` to run tests with temporary test data inside this project tree.
