# pysatgeo

[![PyPI version](https://img.shields.io/pypi/v/pysatgeo.svg)](https://pypi.org/project/pysatgeo/)

`pysatgeo` is a lightweight Python package for raster and vector geospatial
processing.

## What It Covers

The package is intentionally small and organized by topic:

- `pysatgeo.raster` for raster processing workflows
- `pysatgeo.vector` for vector utilities
- `pysatgeo.raster_analysis` for normalization, clustering, and reclassification
- `pysatgeo.terrain` for DEM-related helpers
- `pysatgeo.sampling` for point generation and raster sampling
- `pysatgeo.ranking` for simple ranking and AHP calculations

## Current Shape Of The Repo

This repository was originally broader and more experimental. The current
cleanup focuses on:

- keeping only maintained modules in the package
- exposing a consistent top-level import experience
- documenting the modules that still belong in the public API
- backing the core behavior with automated tests

## Where To Start

Start with:

- `Installation` if you want to set up an environment
- `Usage` if you want working examples
- `API Reference` if you want function-by-function documentation
