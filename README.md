# REBOUND

*Full positioning, architecture, and metrics land on Day 9 (§29 of the locked spec). This file currently holds only setup.*

## Setup

Built and tested on **CPython 3.14.0 (Windows)**. No 3.15/UTF-8-mode assumptions — every text I/O path in this repo sets `encoding="utf-8"` explicitly, because on this interpreter `locale.getpreferredencoding(False)` is `cp1252`, not `utf-8` (PEP 686's UTF-8-by-default lands in 3.15, not 3.14). The fixture contains real Tamil and Hinglish text; an implicit-encoding `open()` call fails on the first non-ASCII case rather than on some rare edge input.

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest tests/ -v
```
