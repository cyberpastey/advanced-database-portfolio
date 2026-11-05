# Actual runtime record - 5 November 2026
PostgreSQL: 17.11, Debian 17.11-1.pgdg13+2, Linux x86_64 (recorded in P1 verification.json).

PostgreSQL image: postgres:17, digest sha256:653186fe15006c099d2fb3bc1d8461c1dee9d036c43f2e5fdaf4f22e5e601876.

MongoDB image: mongo:8.0, digest sha256:b9924c330a8bbc5800fe9c69f04a84e221eca7b28fd049a0354147d9908fa142. Server version is recorded in P4 operations.json.

Execution drivers: psycopg 3.3.8, psycopg-binary 3.3.8, pymongo 4.19.0, Python 3.12 bundled runtime. Docker Engine 29.7.2, Docker Desktop 4.88.1, Linux/amd64 via WSL2. requirements.txt permits compatible driver versions; these are the versions used for the captured evidence. Compose pins major tags; use the digests above to reproduce these exact database images.

Drivers were installed into workspace work/python_deps; that machine-specific location is not part of the submission. A clean environment should install requirements.txt into a virtual environment.
