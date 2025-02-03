# 🕵️ MEDS-Inspect

[![PyPI - Version](https://img.shields.io/pypi/v/MEDS-Inspect)](https://pypi.org/project/MEDS-Inspect/)
[![Documentation Status](https://readthedocs.org/projects/meds-inspect/badge/?version=latest)](https://meds-inspect.readthedocs.io/en/latest/?badge=latest)
[![codecov](https://codecov.io/gh/rvandewater/MEDS-Inspect/graph/badge.svg?token=E7H6HKZV3O)](https://codecov.io/gh/rvandewater/MEDS-Inspect)
[![tests](https://github.com/rvandewater/MEDS-Inspect/actions/workflows/tests.yaml/badge.svg)](https://github.com/rvandewater/MEDS-Inspect/actions/workflows/tests.yml)
[![code-quality](https://github.com/rvandewater/MEDS-Inspect/actions/workflows/code-quality-main.yaml/badge.svg)](https://github.com/rvandewater/MEDS-Inspect/actions/workflows/code-quality-main.yaml)
![python](https://img.shields.io/badge/-Python_3.12-blue?logo=python&logoColor=white)
![Static Badge](https://img.shields.io/badge/MEDS-0.3.3-blue)
[![license](https://img.shields.io/badge/License-MIT-green.svg?labelColor=gray)](https://github.com/rvandewater/MEDS-Inspect#license)
[![PRs](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/rvandewater/MEDS-Inspect/pulls)
[![contributors](https://img.shields.io/github/contributors/rvandewater/MEDS-Inspect.svg)](https://github.com/rvandewater/MEDS-Inspect/graphs/contributors)

MEDS (Medical Event Data Standard) is "the simplest possible standard for health AI" (https://medical-event-data-standard.github.io/).

But after building your own MEDS ETL you might be wondering:

- Is my ETL missing data?
- What codes are contained in my dataset?
- How does my data compare to other MEDS datasets?
- What preprocessing steps are still needed in order to train models?

.. and many more questions related to data exploration.

MEDS-Inspect is an interactive data visualization app that supports you in your data quest.

## Getting started

```bash
pip install MEDS-Inspect
```

Then start a server with the following:

```bash
MEDS_Inspect --port=8060 --file_path="path/to/your/meds/dataset"
```

This will start a local web app that you can access in your browser. Running this command without a file path will
default to the MIMIC-IV Demo data in MEDS

You should also be able to enter an arbitrary filepath from the GUI.

## Getting started (development)

Clone repository:

```bash
git clone https://github.com/rvandewater/MEDS-Inspect.git
cd MEDS-Inspect
```

Create environment:

```bash
conda create -n "meds-inspect" python=3.12
conda activate meds-inspect
```

Install requirements:

```bash
pip install -r requirements.txt
```

Launch app:

```bash
python src/MEDS_Inspect/__main__.py
```

This should start a locally hosted web app.

## Functionality

You can start the caching directly from the command line. Caching creates the folder `.meds-inspect-cache`

```bash
python MEDS_Inspect_cache path/to/your/favorite/meds/dataset
```

Impression:
![Screenshot 2025-01-13 at 11-53-07 MEDS INSPECT](https://github.com/user-attachments/assets/03b81fdd-689c-4151-a522-b5b52db74e66)
