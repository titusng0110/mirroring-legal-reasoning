### Setup
Step 1: clone the repository
```
git clone https://github.com/HKUGenAI/CLIC-chat3.0.git
cd CLIC-chat3.0/
```
Step 2: put legalData*.tar.gz into data/ and unzip them

Step 3: create conda environment:
```
conda create -n casesRAG python=3.12.4
conda activate casesRAG
```
Step 4: install python packages:
```
pip install -r req.txt
```
Step 5: install pypandoc:
```
python install_pypandoc.py
```
Step 6: rename file ".env copy" to ".env" and put your keys and endpoints there.

### Data Processing (uses remote embedding)
For HKLII cases: (assume archive files extracted)
```
chmod u+x process_hklii_cases.sh
./process_hklii_cases.sh data/legalData_2019_2020/eng
./process_hklii_cases.sh data/legalData_2021_2022/eng
./process_hklii_cases.sh data/legalData_2023_2024/en
python merge_parquets.py data/hkc*.parquet --output data/hklii_cases_DDMMYYYY.parquet
```
For eLegislation: (assume rtf files in data/legislation_DDMMYYYY)
```
python clean_legislation.py data/legislation_DDMMYYYY data/legislation_DDMMYYYY.csv
python remote_embed.py data/legislation_DDMMYYYY.csv data/legislation_DDMMYYYY.parquet
```

### Local Search (still uses remote embedding)
With Gradio as GUI:
```
python local_search_gui.py
```

### RAG (uses remote embedding)
With Gradio as GUI:
```
python rag_gui.py
```