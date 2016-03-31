This repo contains various scripts to make modelling with Copasi easier. All Python scripts (except for `copasi.py`) can be called with -h or --help to get instructions.

Until now we have:

* **copasi.py** (python3; not for direct call)

	Contains the Copasi class that is used by many other scripts. This script is thought to be imported by other python scripts.

* **updateMCAOptimizationTarget.py** (python3, depends on copasi.py)

	Creates new Copasi files with changed targets for FCC optimization.

* **parallelCopasi.py** (python3, depends on copasi.py and GNU parallel)

	Copies a given Copasi file n times while changing the optimization output file name. Then sends every copy to GNU parallel for parallel execution.
