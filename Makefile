# Development environment setup for django-snodas.
# Targets are designed for macOS ARM64 with Homebrew.
#
# Quick start on a new machine:
#   make setup
#   source .venv/bin/activate
#   # then follow the printed instructions

.PHONY: help setup install-prereqs install-gdal create-venv install-deps start-db stop-db dev

VENV         := .venv
PYTHON_VERSION := 3.12

help:
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "  setup        Full dev environment setup (run once on a new machine)"
	@echo "  create-conf  Create project.conf (run once after setup)"
	@echo "  start-db     Start PostGIS via Colima + Docker"
	@echo "  stop-db      Stop PostGIS"
	@echo "  dev          Start PostGIS and the development server"
	@echo ""

# ----------------------------------------------------------------------------
# Full setup
# ----------------------------------------------------------------------------

setup: install-prereqs install-gdal create-venv install-deps
	@echo ""
	@echo "============================================================"
	@echo "Python environment ready."
	@echo ""
	@echo "Remaining one-time steps:"
	@echo ""
	@echo "1. Activate the venv:"
	@echo "     source .venv/bin/activate"
	@echo ""
	@echo "2. Create project config:"
	@echo "     make create-conf"
	@echo ""
	@echo "3. Start PostGIS and create the database:"
	@echo "     make start-db"
	@echo "     snodas createdb"
	@echo ""
	@echo "4. Initialize the raster DB (get DEM from django-snodas-data repo):"
	@echo "     snodas createrasterdb --dem <path-to-dem.tif>"
	@echo ""
	@echo "5. Load data:"
	@echo "     snodas loadpourpoint <path-to-pourpoint.geojson>"
	@echo "     ./bin/snodas-download.bash <YYYY-MM-DD> /tmp/snodas.tar"
	@echo "     snodas loadraster /tmp/snodas.tar --skip-legacy-db"
	@echo ""
	@echo "6. Run the dev server:"
	@echo "     snodas runserver"
	@echo "============================================================"
	@echo ""

# ----------------------------------------------------------------------------
# Individual setup steps
# ----------------------------------------------------------------------------

install-prereqs:
	@echo "--- Checking prerequisites ---"
	@command -v brew >/dev/null 2>&1 || \
		(echo "Error: Homebrew is required. Install from https://brew.sh" && exit 1)
	@command -v uv >/dev/null 2>&1 || \
		(echo "Installing uv..." && brew install uv)
	@command -v colima >/dev/null 2>&1 || \
		(echo "Installing colima..." && brew install colima)
	@command -v docker >/dev/null 2>&1 || \
		(echo "Installing docker CLI..." && brew install docker)
	@command -v docker-compose >/dev/null 2>&1 || \
		(echo "Installing docker-compose..." && brew install docker-compose)
	@echo "Prerequisites OK"
	@echo ""

install-gdal:
	@echo "--- Installing GDAL ---"
	@if brew list gdal >/dev/null 2>&1; then \
		echo "GDAL already installed (version: $$(gdal-config --version))"; \
	else \
		echo "Installing GDAL via Homebrew (this may take a few minutes)..."; \
		brew install gdal; \
	fi
	@echo ""

create-venv:
	@echo "--- Creating virtualenv ---"
	@if [ ! -d "$(VENV)" ]; then \
		uv venv --python $(PYTHON_VERSION); \
	else \
		echo "Virtualenv already exists at $(VENV)/"; \
	fi
	@echo ""

install-deps: create-venv
	@echo "--- Installing Python dependencies ---"
	@# numpy and setuptools must be present before building GDAL from source.
	@# numpy is needed to compile the _gdal_array extension.
	uv pip install pip setuptools numpy
	@echo ""
	@# Build GDAL Python bindings from source against the Homebrew GDAL.
	@# --no-binary gdal      forces a source build (the PyPI wheel is broken on ARM64)
	@# --no-build-isolation  lets the build use the venv's numpy (needed for _gdal_array)
	@GDAL_VER=$$(gdal-config --version) && \
	echo "Building gdal==$${GDAL_VER} from source against Homebrew GDAL..." && \
	uv pip install "gdal==$${GDAL_VER}" \
		--no-binary gdal \
		--no-cache-dir \
		--no-build-isolation
	@echo ""
	@# Patch rpath on all osgeo .so files so they can locate libgdal at runtime.
	@# The GDAL Python build system does not embed the rpath automatically.
	@GDAL_LIBDIR=$$(gdal-config --prefix)/lib && \
	echo "Patching rpath on osgeo extensions → $${GDAL_LIBDIR}" && \
	find $(VENV)/lib/python*/site-packages/osgeo/ -name "*.so" -print0 | \
		xargs -0 -I{} sh -c "install_name_tool -add_rpath '$${GDAL_LIBDIR}' '{}' 2>/dev/null; exit 0"
	@echo ""
	@# Install the project and remaining dependencies via pyproject.toml.
	@# GDAL is already installed above so pip will not reinstall it.
	uv pip install -e .
	@echo ""
	@echo "Python dependencies installed successfully."

# ----------------------------------------------------------------------------
# Daily use
# ----------------------------------------------------------------------------

create-conf:
	@echo "--- Creating project.conf ---"
	@test ! -f project.conf || (echo "project.conf already exists. Delete it to recreate." && exit 1)
	@GDAL_LIBDIR=$$(gdal-config --prefix)/lib && \
	GEOS_LIBDIR=$$(brew --prefix geos)/lib && \
	$(VENV)/bin/python -c "\
gdal_lib='$${GDAL_LIBDIR}/libgdal.dylib'; \
geos_lib='$${GEOS_LIBDIR}/libgeos_c.dylib'; \
import getpass, secrets, string, sys; \
pw = getpass.getpass('Enter a password for the database user: '); \
pw2 = getpass.getpass('Confirm password: '); \
sys.exit('Passwords do not match') if pw != pw2 else None; \
key = ''.join(secrets.choice(string.ascii_letters + string.digits + '!@#%^&*()-_=+') for _ in range(50)); \
open('project.conf', 'w').write( \
'# This file contains SECRET information!\n' \
'# DO NOT commit this file.\n\n' \
'ADDITIONAL_SETTINGS_FILES: []\n' \
'CONDA_ENV_NAME: snodas-dev\n' \
'DATABASE_HOST: localhost\n' \
'DATABASE_NAME: snodas_dev\n' \
f'DATABASE_PASSWORD: {chr(39)}{pw}{chr(39)}\n' \
'DATABASE_PORT: 5432\n' \
'DATABASE_USER: snodas_dev\n' \
'DEBUG: true\n' \
'DEPLOYMENT_TYPE: development\n' \
'PROJECT_NAME: snodas-dev\n' \
f'SECRET_KEY: {chr(39)}{key}{chr(39)}\n' \
'SITE_DOMAIN_NAME: snodas.geog.pdx.edu\n' \
'SNODAS_RASTERDB: .raster-db\n' \
'SUBDOMAINS: []\n' \
f'GDAL_LIBRARY_PATH: {gdal_lib}\n' \
f'GEOS_LIBRARY_PATH: {geos_lib}\n' \
); \
print('project.conf created successfully.')"
	@echo ""

start-db:
	@echo "--- Starting PostGIS ---"
	colima start 2>/dev/null || true
	@echo "Waiting for Docker daemon..."
	@for i in $$(seq 1 30); do \
		docker info >/dev/null 2>&1 && break; \
		sleep 1; \
	done
	docker-compose up -d

stop-db:
	docker-compose down

dev: start-db
	$(VENV)/bin/snodas runserver

