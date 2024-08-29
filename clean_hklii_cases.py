import glob
import re
import traceback
import argparse
import pypandoc
from langchain_text_splitters import RecursiveCharacterTextSplitter
import csv


def cleanDataOnce(case):
    case = case[case.index("You are here:") :]
    case = case[case.index("------------------------------------------------------------------------") :]
    case = case.replace("|", "")
    case = re.sub(" +", " ", case)
    return case


def getTitle(case):
    return case[case.index("-\n") + 2 : case.index(")\n") + 1].replace("\n", "")

def splitData(case):
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        model_name="gpt-4",
        chunk_size=1000,
        chunk_overlap=400
    )
    texts = text_splitter.split_text(case)
    return texts

def cleanDataTwice(case):
    if case.find("IN THE") == -1:
        return None
    elif case.find("1.") == -1: # unparagraphed case
        return case[case.index("IN THE") :]
    else:
        return case[case.index("1.") :]

def processFiles(directory):
    result = []
    files = glob.glob(f"{directory}/*.html")
    for file_name in files:
        try:
            case = pypandoc.convert_file(file_name, "plain")
            case = cleanDataOnce(case)
            title = getTitle(case)
            case = cleanDataTwice(case)
            if case == None:
                print(f"Skipped conversion of {file_name} for lack of content.")
                print(pypandoc.convert_file(file_name, "plain"))
                continue
            chunks = splitData(case)
            for count, ele in enumerate(chunks):
                result.append({
                    "id": file_name[file_name.index("hk") : file_name.index(".")].replace("/", "_") + f"_{count + 1}",
                    "title": title + f" Extract {count + 1}",
                    "content": ele
                })
        except (ValueError, RuntimeError):
            print("Error converting", file_name)
            print(traceback.format_exc())
    return result


def writeToCSV(result, output_file):
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "title", "content"])
        writer.writeheader()
        for item in result:
            writer.writerow(item)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process HTML files from the specified directory.")
    parser.add_argument("directory", type=str, help="Directory containing HTML files to process")
    parser.add_argument("output_file", type=str, help="Output CSV file")
    args = parser.parse_args()
    result = processFiles(args.directory)
    writeToCSV(result, args.output_file)
