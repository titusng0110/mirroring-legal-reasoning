## Setup
Step 1: clone the repository
```
git clone https://github.com/titusng0110/mirroring-legal-reasoning.git
cd mirroring-legal-reasoning/
```
Step 2: create conda environment:
```
conda create -n mirror python=3.12.4
conda activate mirror
python -m pip install -U pip
```
Step 3: install python packages:
```
python -m pip install -r req.txt
```
Step 4: install pypandoc:
```
python install_pypandoc.py
```
Step 5: rename file ".env copy" to ".env" and put your keys and endpoints there.

## Data Processing
For HKLII cases (2019 onwards): (assume archive files extracted to data/)
```
python clean_hklii_cases.py data/path-to-cases-folder data/cases_your_name.csv
```
For HKLII cases (before 2019): (assume archive files extracted to data/)
```
python clean_hklii_cases_pre2019.py data/path-to-cases-folder data/cases_your_name.csv
```
For eLegislation (https://data.gov.hk/en-data/dataset/hk-doj-hkel-legislation-current): (assume archive files extracted to data/) 
```
python clean_legislation_xml.py data/path-to-legislation-folder data/legislation_your_name.csv
```
Generate vector embeddings:
```
python local_embed.py data/your-data.csv data/your-data.parquet
```
## Local Search
With Gradio as GUI:
```
python local_search_gui.py
```

## Chat
With Gradio as GUI:
```
python chat_gui.py
```
