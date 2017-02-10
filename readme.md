This repo contains various scripts to make modelling with Copasi easier. All Python scripts (except for `copasi.py`) can be called with -h or --help to get instructions.

* **copasi.py** (python3; not for direct call)

	Contains the Copasi class that is used by many other scripts. This script is thought to be imported by other python scripts.

* **updateMCAOptimizationTarget.py** (python3, depends on copasi.py)

	Creates new Copasi files with changed targets for FCC optimization.

* **extractFluxConcFromResults.py** (python3)

	Extracts species concentrations and reaction fluxes from steady state results.

* **extractMCAOptimizationResults.py** (python3)

	Extracts results from MCA optimizations.

* **parallelCopasi.py** (python3, depends on copasi.py and GNU parallel)

	Copies a given Copasi file n times while changing the optimization output file name. Then sends every copy to GNU parallel for parallel execution.
