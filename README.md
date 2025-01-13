# MEDS INSPECT 🕵️

MEDS (Medical Event Data Standard) is "the simplest possible standard for health AI" (https://medical-event-data-standard.github.io/). 

But after building your own MEDS ETL you might be wondering:
- Is my ETL missing data?
- What codes are contained in my dataset?
- How does my data compare to other MEDS datasets?

.. and many more questions related to data exploration. 

MEDS-Inspect is an interactive data visualization app that supports you in your data quest.

## Getting started

``
git clone https://github.com/rvandewater/MEDS-Inspect.git
cd MEDS-Inspect
``

``
conda create -n "meds-inspect" python=3.12  
``

``
conda activate meds-inspect
``

``
pip install -r requirements.txt
``

``
python src/meds-inspect/app.py
``
This should start a locally hosted web app

Impression:
![Screenshot 2025-01-13 at 11-53-07 MEDS INSPECT](https://github.com/user-attachments/assets/03b81fdd-689c-4151-a522-b5b52db74e66)
