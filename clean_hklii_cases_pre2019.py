import glob
import argparse
from langchain_text_splitters import RecursiveCharacterTextSplitter
import csv
from bs4 import BeautifulSoup

def write_to_csv(result, output_file):
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "title", "content"])
        writer.writeheader()
        for item in result:
            writer.writerow(item)

def splitData(case):
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        model_name="gpt-4",
        chunk_size=1000,
        chunk_overlap=400
    )
    texts = text_splitter.split_text(case)
    return texts

def main(): 
    files = glob.glob(f"{args.directory}/*.html")
    # files = glob.glob(f"data/legalData/legalData/db/eng/HKCA/data/1997_468.html")
    result = []
    for file_name in files:
        if int(file_name.split("/")[-1].split("_")[0]) < 1997 or int(file_name.split("/")[-1].split("_")[0]) > 2018:
            continue
        # Read and parse XML
        with open(file_name, "r") as f:
            soup = BeautifulSoup(f, 'html.parser')
        form = soup.find("form")
        caseno = soup.find("caseno")
        parties = soup.find("parties")
        if form and parties:
            print(f"Processing {file_name}")
            id = file_name.split("/")[-3] + "_" + file_name.split("/")[-1].replace(".html", "")
            if caseno and caseno.get_text(strip=True) != "":
                title = " ".join([" ".join(i.split()) for i in caseno.stripped_strings]) + " " + " ".join([" ".join(i.split()) for i in parties.stripped_strings])
            else:
                first_p = form.find('p', recursive=True)
                title = " ".join([" ".join(i.split()) for i in first_p.stripped_strings]) + " " + " ".join([" ".join(i.split()) for i in parties.stripped_strings])

            content = " ".join([" ".join(i.split()) for i in form.stripped_strings])
            split_content = splitData(content)
            for count, ele in enumerate(split_content):
                result.append({
                    "id": id + f"_{count+1}",
                    "title": title +  f" Extract {count+1}",
                    "content": ele
                })
    write_to_csv(result, args.output_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process html files from the specified directory.")
    parser.add_argument("directory", type=str, help="Directory containing html files to process")
    parser.add_argument("output_file", type=str, help="Output CSV file")
    args = parser.parse_args()
    main()
