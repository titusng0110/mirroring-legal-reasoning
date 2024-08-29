from bs4 import BeautifulSoup
import tiktoken
import glob
import argparse
import csv
import re

def get_title(soup):
    title = ""
    if soup.find("shortTitle"):
        title = " ".join(soup.find("shortTitle").get_text().split()) + " " + " ".join(soup.find("docName").get_text().split()) + "\n"
    elif soup.find("docTitle"):
        title = " ".join(soup.find("docTitle").get_text().split()) + " " + " ".join(soup.find("docName").get_text().split()) + "\n"
    else:
        full_text = " ".join(str(soup).split())
        match = re.search(r"This Ordinance may be cited as the (.+?)\.", full_text)
        if match:
            title = match.group(1) + " " + " ".join(soup.find("docName").get_text().split()) + "\n"
        else:
            title = input("Cannot extract name of Ordinance, manually enter name: ") + " " + " ".join(soup.find("docName").get_text().split()) + "\n"
    return title

def get_description(soup, encoding, limit=100):
    description = None
    if soup.find("longTitle"):
            if len(encoding.encode(" ".join(soup.find("longTitle").get_text().split()))) < limit:
                description = " ".join(soup.find("longTitle").get_text().split()) + "\n"
    return description

def add_metadata_to_cleaned_sections(soup, title, description, cleaned_sections):
    for count, ele in enumerate(cleaned_sections):
        parent_string = ""
        for j in reversed(ele['parents']):
            parent = soup.find(id=j)
            num = parent.find("num")
            heading = parent.find("heading")
            if num and not heading:
                parent_string += " ".join(num.get_text().split()) + "\n"
            elif heading and not num:
                parent_string += " ".join(heading.get_text().split()) + "\n"
            elif num and heading:
                parent_string += " ".join(num.get_text().split()) + " " + " ".join(heading.get_text().split()) + "\n"
        if description:
            cleaned_sections[count]['heading'] = title + description + parent_string + cleaned_sections[count]['heading']
        else:
            cleaned_sections[count]['heading'] = title + parent_string + cleaned_sections[count]['heading']
    return cleaned_sections

def parse_and_clean_section(section):
    section_data = {
        "heading": "",
        "text": "",
        "parents": [],
        "subsections": []
    }
    # build parent stack
    temp = section
    while not temp.parent is None and temp.parent.name != "main":
        if 'id' in temp.parent.attrs:
            section_data['parents'].append(temp.parent.attrs['id'])
        temp = temp.parent
    # build child list
    for subsection in section.find_all('subsection'):
        section_data['subsections'].append(" ".join([" ".join(i.split()) for i in subsection.stripped_strings])) 
        subsection.decompose()
    # seperate num and heading
    num = section.find("num")
    heading = section.find("heading")
    if num and heading:
        section_data['heading'] = "".join(num.get_text().split()) + " " + " ".join(heading.get_text().split()) + "\n"
        num.decompose()
        heading.decompose()
    elif num:
        section_data["heading"] = "".join(num.get_text().split()) + " "
        num.decompose()
    # rest of section
    section_data['text'] = " ".join([" ".join(i.split()) for i in section.stripped_strings])
    return section_data

def create_chunks(cleaned_sections, encoding, limit=512):
    chunks = []
    def split_text(text, n):
        words = text.split()
        return [' '.join(words[i:i+n]) for i in range(0, len(words), n)]
    def split_large_text(text, heading):
        for divisor in range(2, len(text.split())):
            splits = split_text(text, len(text.split()) // divisor)
            if all(len(encoding.encode(heading + " " + split)) <= limit for split in splits):
                return [heading + " " + split for split in splits]
        return [text]  # If we can't split it, return it as is
    for section in cleaned_sections:
        section_text = section['text']
        heading = section['heading']
        if len(encoding.encode(heading + " " + section_text)) > limit:
            # If section text is already over the limit, split it
            for split in split_large_text(section_text, heading):
                chunks.append({'content': split})
            # Separately process subsections
            for subsection in section['subsections']:
                if len(encoding.encode(heading + " " + subsection)) > limit:
                    for split in split_large_text(subsection, heading):
                        chunks.append({'content': split})
                else:
                    chunks.append({'content': heading + " " + subsection})
        else:
            # Use the original logic if section text is not over the limit
            current_chunk = heading + " " + section_text
            for subsection in section['subsections']:
                if len(encoding.encode(heading + " " + subsection)) > limit:
                    # If subsection is over limit, split it
                    for split in split_large_text(subsection, heading):
                        if len(encoding.encode(current_chunk + " " + split.replace(heading, ""))) <= limit:
                            current_chunk += " " + split.replace(heading, "")
                        else:
                            chunks.append({'content': current_chunk})
                            current_chunk = split
                else:
                    # Original logic for subsections <= limit
                    potential_chunk = current_chunk + " " + subsection
                    if len(encoding.encode(potential_chunk)) <= limit:
                        current_chunk = potential_chunk
                    else:
                        chunks.append({'content': current_chunk})
                        current_chunk = heading + " " + subsection
            # Add the last chunk for this section
            if current_chunk:
                chunks.append({'content': current_chunk})
    return chunks

def add_metadata_to_chunks(file_name, title, chunks):
    for count, ele in enumerate(chunks):
        chunks[count]['id'] = f"{file_name.split("/")[-2]}_{count+1}"
        chunks[count]['title'] = f"{title.strip()} Extract {count+1}"
    return chunks

def write_to_csv(result, output_file):
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "title", "content"])
        writer.writeheader()
        for item in result:
            writer.writerow(item)

def main():
    files = glob.glob(f"{args.directory}*/*.xml")
    # files = glob.glob(f"data/legislation_02082024/cap_26_en_c/cap_26_20180920000000_en_c.xml")
    encoding = tiktoken.encoding_for_model(model_name="gpt-4")
    result = []
    for file_name in files:
        # Read and parse XML
        with open(file_name, "r") as f:
            soup = BeautifulSoup(f, 'xml')
        # Remove ineffective legislation
        if (soup.find("docStatus").get_text() == "Repealed"
            or soup.find("docStatus").get_text() == "Not adopted as the Laws of the HKSAR"
            or soup.find("docStatus").get_text() == "Omitted as expired"
            or soup.find("docStatus").get_text() == "Not yet in operation"):
            continue
        # Process
        print("Processing", file_name)
        title = get_title(soup)
        description = get_description(soup, encoding)
        sections = soup.find_all('section')
        cleaned_sections = [parse_and_clean_section(i) for i in sections]
        cleaned_sections = add_metadata_to_cleaned_sections(soup, title, description, cleaned_sections)
        chunks = create_chunks(cleaned_sections, encoding)
        chunks = add_metadata_to_chunks(file_name, title, chunks)
        result += chunks
    write_to_csv(result, args.output_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process xml files from the specified directory.")
    parser.add_argument("directory", type=str, help="Directory containing xml files to process")
    parser.add_argument("output_file", type=str, help="Output CSV file")
    args = parser.parse_args()
    main()

