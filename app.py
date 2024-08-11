from openai import AzureOpenAI
from dotenv import load_dotenv
import os
import local_search
import json
import threading

load_dotenv(override=True)

client = AzureOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("OPENAI_API_ENDPOINT")
)
model = os.getenv("OPENAI_API_DEPLOYMENT_NAME")

thread = threading.Thread(target=local_search.loadDB, args=({
    "cfa": "data/hkcfa_1997_2024.parquet",
    "ca": "data/hkca_1997_2023.parquet",
    "cfi": "data/hkcfi_1997_2024.parquet",
    "legislation": "data/legislation_02082024_xml.parquet"
},))
thread.start()

class Issue:
    def __init__(self, user_input, area, issue):
        self.user_input = user_input
        self.area = area
        self.issue = issue
        self.consolidated_position = ""
    
    def get_user_input(self):
        return self.user_input
    
    def get_area(self):
        return self.area
    
    def get_issue(self):
        return self.issue
    
    def set_consolidated_position(self, consolidated_position):
        self.consolidated_position = consolidated_position
    
    def get_consolidated_position(self):
        return self.consolidated_position

def get_response(messages):
    print("[SYSTEM]")
    print(messages[0]['content'])
    print("[USER]")
    print(messages[1]['content'])
    completion = client.chat.completions.create(
        model = model,
        messages = messages
    )
    chat_response = completion.choices[0].message.content
    print("[ASSISTANT]")
    print(chat_response)
    print()
    return chat_response

def initial_analyse(user_input):
    table_of_contents = {
        "Contract Law": "TOC/Chitty on Contracts 35 Edition.txt",
        "Trust Law": "TOC/Lewin on Trusts 20 Edition.txt",
        "Tort Law": "TOC/Tort Law in Hong Kong 5 Edition.txt",
        "Civil Procedure" : "TOC/Hong Kong Civil Procedure 2024.txt",
        "Land Law": "TOC/Land Law in Hong Kong 5 Edition.txt",
        "Business Associations": "TOC/Law of Companies in Hong Kong 4 Edition.txt",
        "Commercial Law": "TOC/Goode and McKendrick on Commercial Law 6 Edition.txt",
        "Equity": "TOC/Snell's Equity 34 Edition.txt"
    }
    messages = [
        {"role": "system", "content": "You are an intelligent and logical lawyer specialising in Hong Kong law. Hong Kong law is a common law system similar to UK (England and Wales) law. Legislation in Hong Kong is referred to as Ordinances instead of Acts. Case law is mainly the same."},
        {
            "role" : "user",
            "content": 'The scenario:\n' + user_input + '\nPotential areas of law:\n' + ", ".join(table_of_contents.keys()) + '\nInstruction:\nBased on the above information, select at most three areas of law from the potential areas of law related to the scenario. Output in JSON format.\nExample:\n```json\n{\n    "areas": [\n        "Land Law",\n        "Tort Law",\n        "Commercial Law"\n    ]\n}\n```'
        }
    ]
    chat_response = get_response(messages)
    areas = json.loads(chat_response.replace("```json", "").replace("```", "").strip())
    issues = []
    for area in areas['areas']:
        f = open(table_of_contents[area], "r")
        messages = [
            {"role": "system", "content": "You are an intelligent and logical lawyer specialising in Hong Kong law. Hong Kong law is a common law system similar to UK (England and Wales) law. Legislation in Hong Kong is referred to as Ordinances instead of Acts. Case law is mainly the same."},
            {
                "role" : "user",
                "content": 'Table of contents of a leading textbook in the area of law:\n'.replace("the area of law", area) + f.read() + '\nThe scenario:\n' + user_input + '\nInstruction:\nBased on the above information only, identify all potential legal issues within the area of law arising from the scenario. There can be an unlimited number of potential legal issues. Output in JSON format.\nExample:\n```json\n{\n    "issues": [\n        "Whether GHI has a duty of care to ensure the elevator operates safely",\n        "If GHI has a duty of care to ensure the elevator operates safely, what is the standard of care",\n        "Whether GHI has breached its duty of care to ensure the elevator operates safely",\n        "Whether GHI has statutory duty of occupier\'s liability",\n        "Whether ABC is contributory negligent when operating the elevator"\n    ]\n}\n```'.replace("the area of law", area)
            }
        ]
        f.close()
        chat_response = get_response(messages)
        temp_issues = json.loads(chat_response.replace("```json", "").replace("```", "").strip())
        for issue in temp_issues['issues']:
            issues.append(Issue(user_input=user_input, area=area, issue=issue))

    return issues


def formulate_query(issue, option):
    database_info = {
        "legislation": "all Hong Kong ordinances and subsidiary legislation in effect",
        "cfa": "all Hong Kong Court of Final Appeal cases from 1997 to 2024",
        "ca": "all Hong Kong Court of Appeal cases from 1997 to 2023",
        "cfi": "all Hong Kong Court of First Instance cases from 1997 to 2024"
    }
    examples = {
        "legislation": 'Example 1:\n```json\n{"query": "What is considered driving in excess of speed limit?"}\n```\nExample 2:\n```json\n{"query": "What are the implied undertakings as to quality or fitness for a sales of good?"}\n```',
        "cfa": 'Example 1:\n```json\n{"query": "What is the legal principle of common intention constructive trust?"}\n```\nExample 2:\n```json\n{"query": "What are the circumstances where rescission will be barred as an equitable remedy under contract law?"}\n```',
        "ca": 'Example 1:\n```json\n{"query": "What is the legal principle of common intention constructive trust?"}\n```\nExample 2:\n```json\n{"query": "What are the circumstances where rescission will be barred as an equitable remedy under contract law?"}\n```',
        "cfi": 'Example 1:\n```json\n{"query": "What is the legal principle of common intention constructive trust?"}\n```\nExample 2:\n```json\n{"query": "What are the circumstances where rescission will be barred as an equitable remedy under contract law?"}\n```'
    }
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {
            "role" : "user",
            "content": 'The scenario:\n' + issue.get_user_input() + "\nThe area of law:\n" + issue.get_area() + "\nThe legal issue:\n" + issue.get_issue() + '\nInstruction:\nBased on the scenario, generate a query string for researching on the legal issue by performing vector search of a legal database. The legal database contains ' + database_info[option] + '. Here are some questions for thought. What is the legal principle related to the legal issue? What might be specific about Hong Kong law that you will want to search regarding the legal issue? The query string generated shall encapsulate the semantic meaning of the question you want to search. Expand abbreviations (CICT becomes Common Intention Constructive Trust) and remove specific information (Peter becomes Landlord, truck becomes vehicle) to enhance the effect of vector search. As the database only contains Hong Kong law, do NOT include "Hong Kong" in your query. Output in JSON format.\n' + examples[option]
        }
    ]
    chat_response = get_response(messages)
    query = json.loads(chat_response.replace("```json", "").replace("```", "").strip())
    query['option'] = option
    return query

def retrieve(query):
    return local_search.search(database=query['option'], query=query['query'], k=10, bigk=100)

def legal_reason_legislation(issue, result):
    # identify legal rule from search results, if cannot identify, reformulate query, if still cannot, discard
    # identify the conditions of the legal rule
    # identify the type and consequence of the legal rule
    # identify the exceptions to the legal rule
    # application of the legal rule
    pass

def legal_reason_cases(issue, result):
    # After reading the results, which two cases do you think are the most relevant to the legal issue? if cannot decide, reformulate query, if still cannot, discard
    # get neibouring paragraphs of the two cases and ask it to identify legal rule? if cannot decide, reformulate query, if still cannot, discard
    # identify legal rule from search results, if cannot identify, reformulate query, if still cannot, discard
    # identify the conditions of the legal rule
    # identify the type and consequence of the legal rule
    # identify the exceptions to the legal rule
    # application of the legal rule
    pass

def consolidate_positions(issue, positions):
    pass

def generate_answer():
    pass

def main():
    user_input = input()
    issues = initial_analyse(user_input)
    # for issue in issues:
    #     queries = []
    #     queries.append(formulate_query(issue, option = "legislation"))
    #     queries.append(formulate_query(issue, option = "cfa"))
    #     queries.append(formulate_query(issue, option = "ca"))
    #     queries.append(formulate_query(issue, option = "cfi"))
    #     thread.join()
    #     for query in queries:
    #         result = retrieve(query)
    #     positions = []
    #         if result['option'] == "legislation":
    #             positions.append(legal_reason_legislation(issue, result))
    #         else:
    #             positions.append(legal_reason_cases(issue, result))
    #     issue.set_consolidated_position(consolidate_positions(issue, positions))
    # generate_answer(issues)


if __name__ == "__main__":
    main()



