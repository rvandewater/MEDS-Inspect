# MEDS INSPECT 🕵️

MEDS (Medical Event Data Standard) is "the simplest possible standard for health AI" (https://medical-event-data-standard.github.io/).

But after building your own MEDS ETL you might be wondering:

- Is my ETL missing data?
- What codes are contained in my dataset?
- How does my data compare to other MEDS datasets?
- What preprocessing steps are still needed in order to train models?

.. and many more questions related to data exploration.

MEDS-Inspect is an interactive data visualization app that supports you in your data quest.

## Getting started

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
python src/app.py
```

This should start a locally hosted web app.

## More functionality

The MIMIC-IV MEDS demo is loaded by default but it can be replaced like this:

```bash
python src/app.py --file_path=path/to/your/favorite/meds/dataset
```

You can start the caching directly from the command line. Caching creates the folder `.meds-inspect-cache`

```bash
python src/cache_results.py --file_path=path/to/your/favorite/meds/dataset
```

Impression:
![Screenshot 2025-01-13 at 11-53-07 MEDS INSPECT](https://github.com/user-attachments/assets/03b81fdd-689c-4151-a522-b5b52db74e66)
