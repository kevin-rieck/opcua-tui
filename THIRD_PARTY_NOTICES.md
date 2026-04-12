# Third-Party Notices

This project is licensed under MIT (see `LICENSE`).

The application depends on third-party packages with their own licenses.
The runtime dependency set was reviewed from `uv tree --package opcua-tui-starter`
on 2026-04-12.

## Runtime Dependencies

| Package | Version | License |
| --- | --- | --- |
| asyncua | 1.1.8 | LGPL-3.0-or-later |
| aiofiles | 25.1.0 | Apache-2.0 |
| aiosqlite | 0.22.1 | MIT |
| cryptography | 46.0.6 | Apache-2.0 OR BSD-3-Clause |
| cffi | 2.0.0 | MIT |
| pycparser | 3.0 | BSD-3-Clause |
| pyOpenSSL | 26.0.0 | Apache-2.0 |
| python-dateutil | 2.9.0.post0 | BSD OR Apache-2.0 (dual license) |
| six | 1.17.0 | MIT |
| pytz | 2026.1.post1 | MIT |
| sortedcontainers | 2.4.0 | Apache-2.0 |
| typing_extensions | 4.15.0 | PSF-2.0 |
| textual | 0.89.1 | MIT |
| markdown-it-py | 4.0.0 | MIT |
| mdurl | 0.1.2 | MIT |
| platformdirs | 4.9.4 | MIT |
| rich | 14.3.3 | MIT |
| Pygments | 2.19.2 | BSD-2-Clause |

## Important Note on LGPL Dependency

`asyncua` is licensed under LGPL-3.0-or-later.

Keeping this project under MIT is allowed. However, when redistributing builds
that include `asyncua`, you should preserve third-party notices and include the
license text(s) required by upstream packages, including LGPL for `asyncua`.

If you modify `asyncua` itself and distribute that modified version, LGPL terms
for modified library distribution apply.
