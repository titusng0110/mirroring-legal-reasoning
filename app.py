from openai import AzureOpenAI
from dotenv import load_dotenv
import os
import local_search
import json
import threading
import re
import time

load_dotenv(override=True)

client = AzureOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("OPENAI_API_ENDPOINT")
)
model = os.getenv("OPENAI_API_DEPLOYMENT_NAME")

thread = threading.Thread(target=local_search.loadDB, args=({
    "cases": "data/hklii.parquet",
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

def get_response(messages, temperature=0.2, top_p=0.2):
    print("[SYSTEM]")
    print(messages[0]['content'])
    print("[USER]")
    print(messages[1]['content'])
    completion = client.chat.completions.create(
        model = model,
        messages = messages,
        temperature = temperature,
        top_p = top_p
    )
    chat_response = completion.choices[0].message.content
    tries = 1
    while chat_response is None and tries < 3:
        time.sleep(5)
        completion = client.chat.completions.create(
            model = model,
            messages = messages,
            temperature = temperature,
            top_p = top_p
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
    # messages = [
    #     {"role": "system", "content": "You are an intelligent and logical lawyer specialising in Hong Kong law. Hong Kong law is a common law system similar to UK (England and Wales) law. Legislation in Hong Kong is referred to as Ordinances instead of Acts. Case law is mainly the same."},
    #     {
    #         "role" : "user",
    #         "content": 'The scenario:\n' + user_input + '\nPotential areas of law:\n' + ", ".join(table_of_contents.keys()) + '\nInstruction:\nBased on the above information, select at most three areas of law from the potential areas of law related to the scenario. Output in JSON format.\nExample:\n```json\n{\n    "areas": [\n        "Land Law",\n        "Tort Law",\n        "Commercial Law"\n    ]\n}\n```'
    #     }
    # ]
    # chat_response = get_response(messages)
    # areas = json.loads(re.search(r'```json(.*?)```', chat_response, re.DOTALL).group(1))
    areas = {"areas": ["Contract Law"]}
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
        temp_issues = json.loads(re.search(r'```json(.*?)```', chat_response, re.DOTALL).group(1))
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
    query = json.loads(re.search(r'```json(.*?)```', chat_response, re.DOTALL).group(1))
    query['option'] = option
    return query

def retrieve(query):
    thread.join()
    return local_search.search(database=query['option'], query=query['query'], k=10, bigk=100)

def legal_reason_legislation(issue, result):
    # identify relevant sections from search results, if cannot, discard (assume bad search results / no such legal rule)
    # Deductive reasoning:
    #   major premise: identify the rule of law: if [conditions], then [consequences], unless [exception] (assumption: the rule of law is captured within search results)
    #   minor premise: facts of the current case fits/not fit [conditions], is/is not [exception] (assumption: interpretation of statute by plain wording)
    #   conclusion: is/is not [consequence]
    # Identify major premise
    messages = [
        {"role": "system", "content": "You are an intelligent and logical lawyer specialising in Hong Kong law. Hong Kong law is a common law system similar to UK (England and Wales) law. Legislation in Hong Kong is referred to as Ordinances instead of Acts. Case law is mainly the same."},
        {
            "role" : "user",
            "content": 'The search results:\n' + json.dumps(result[1:], indent=4) + '\nThe scenario:\n' + issue.get_user_input() + "\nThe area of law:\n" + issue.get_area() + "\nThe legal issue:\n" + issue.get_issue() + '\nInstruction:\nBased only on the search results, identify all rules of law that correspond to the legal issue specific to the scenario by answering these 4 questions: 1. What are the conditions of the rule? Include conditions from the parent section. 2. What is the consequence of the rule? 3. What are the exceptions to this rule? Include exceptions from the parent section. 4. What is the citation of the relevant section the legal rule is from?\nStrictly follow the format (JSON) of the following examples.\nExample output (irrelevant):\n```json\n[]\n```\nExample legal issue:\nWhat are the differences for remedies of innocent, negligent, and fraudulent misrepresentations?\nExample search results:\nMisrepresentation Ordinance Cap. 284 To amend the law relating to innocent misrepresentations. 3. Damages for misrepresentation (1) Where a person has entered into a contract after a misrepresentation has been made to him by another party thereto and as a result thereof he has suffered loss, then, if the person making the misrepresentation would be liable to damages in respect thereof had the misrepresentation been made fraudulently, that person shall be so liable notwithstanding that the misrepresentation was not made fraudulently, unless he proves that he had reasonable grounds to believe and did believe up to the time the contract was made that the facts represented were true. (2) Where a person has entered into a contract after a misrepresentation has been made to him otherwise than fraudulently, and he would be entitled, by reason of the misrepresentation, to rescind the contract, then, if it is claimed, in any proceedings arising out of the contract, that the contract ought to be or has been rescinded the court or arbitrator may declare the contract subsisting and award damages in lieu of rescission, if of opinion that it would be equitable to do so, having regard to the nature of the misrepresentation and the loss that would be caused by it if the contract were upheld, as well as to the loss that rescission would cause to the other party.\nExample output:\n```json\n[\n    {\n        "Conditions": "If (1) a person has entered into a contract after a misrepresentation; and (2) the misrepresentation has been made to him by another party; and (3) he has suffered loss as a result of the misrepresentation; and (4) if the misrepresentation had been made fraudulently, the person making the misrepresentation would be liable to damages",\n        "Consequences": "Then (1) the person making the misrepresentation shall still be liable to damages even though the misrepresentation was not made fraudulently",\n        "Exceptions": "Unless (1) the person making the misrepresentation proves that he had reasonable grounds to believe that the facts represented were true; and (2) the person making the misrepresentation did believe up to the time the contract was made that the facts represented were true",\n        "Citation": "Misrepresentation Ordinance Cap. 284 Section 3 Subsection 1"\n    }\n    {\n        "Conditions": "If (1) a person has entered into a contract; and (2) he entered into a contract after a misrepresentation has been made to him; and (3) the misrepresentation was not made to him fraudulently; and (4) he would be entitled, by reason of the misrepresentation, to rescind the contract; and (5) if it is claimed in any proceedings arising out of the contract that the contract ought to be or has been rescinded; and (6) the court or arbitrator is of opinion that it would be equitable to do so, having regard to the nature of the misrepresentation and the loss that would be caused by it if the contract were upheld, as well as to the loss that rescission would cause to the other party",\n        "Consequences": "Then (1) the court or arbitrator may declare the contract subsisting and award damages in lieu of rescission",\n        "Exceptions": "Unless none",\n        "Citation": "Misrepresentation Ordinance Cap. 284 Section 3 Subsection 2"\n    }\n]\n```'
        }
    ]
    chat_response = get_response(messages)
    major_premise = json.loads(re.search(r'```json(.*?)```', chat_response, re.DOTALL).group(1))
    if len(major_premise) == 0:
        return None
    # Restate major premise + minor premise + conclusion
    messages = [
        {"role": "system", "content": "You are an intelligent and logical lawyer specialising in Hong Kong law. Hong Kong law is a common law system similar to UK (England and Wales) law. Legislation in Hong Kong is referred to as Ordinances instead of Acts. Case law is mainly the same."},
        {
            "role": "user",
            "content": 'The major premise:\n' + json.dumps(major_premise, indent=4) + '\nThe scenario:\n' + issue.get_user_input() + "\nThe area of law:\n" + issue.get_area() + "\nThe legal issue:\n" + issue.get_issue() + '\nInstruction:\nInterpret the legal framework in the major premise using plain meaning. Determine if the scenario facts satisfy all conditions and avoid exceptions in the major premise by substituting the facts into the premise. Output the minor premise and the conclusion that answers the legal issue. You must make a decision. Strictly follow the output format of the following example.\nExample scenario:\nEmma, unaware of any defect, sold her vintage car to Jack, claiming it had never been in an accident, which was untrue. Jack, unaware of the misrepresentation, quickly sold the car to Lucy. When Lucy discovered the truth, she claimed damages from Jack. Jack sought rescission from Emma.\nExample legal issue:\nWhether rescission is available to Jack as a remedy to misrepresentation\nExample major premise:\n[\n    {\n        "Conditions": "If (1) a person has entered into a contract after a misrepresentation; and (2) the misrepresentation has been made to him by another party; and (3) he has suffered loss as a result of the misrepresentation; and (4) if the misrepresentation had been made fraudulently, the person making the misrepresentation would be liable to damages",\n        "Consequences": "Then (1) the person making the misrepresentation shall still be liable to damages even though the misrepresentation was not made fraudulently",\n        "Exceptions": "Unless (1) the person making the misrepresentation proves that he had reasonable grounds to believe that the facts represented were true; and (2) the person making the misrepresentation did believe up to the time the contract was made that the facts represented were true",\n        "Citation": "Misrepresentation Ordinance Cap. 284 Section 3 Subsection 1"\n    }\n    {\n        "Conditions": "If (1) a person has entered into a contract; and (2) he entered into a contract after a misrepresentation has been made to him; and (3) the misrepresentation was not made to him fraudulently; and (4) he would be entitled, by reason of the misrepresentation, to rescind the contract; and (5) if it is claimed in any proceedings arising out of the contract that the contract ought to be or has been rescinded; and (6) the court or arbitrator is of opinion that it would be equitable to do so, having regard to the nature of the misrepresentation and the loss that would be caused by it if the contract were upheld, as well as to the loss that rescission would cause to the other party",\n        "Consequences": "Then (1) the court or arbitrator may declare the contract subsisting and award damages in lieu of rescission",\n        "Exceptions": "Unless none",\n        "Citation": "Misrepresentation Ordinance Cap. 284 Section 3 Subsection 2"\n    }\n]\nExample output:\n### Relevant law:\n\nMisrepresentation Ordinance Cap. 284 Section 3 Subsection 1 and 2\n\n### Major Premise:\n\n1. Misrepresentation Ordinance Cap. 284 Section 3 Subsection 1\n   \n   Conditions:\n   - A person has entered into a contract after a misrepresentation\n   - The misrepresentation has been made to him by another party\n   - He has suffered loss as a result of the misrepresentation\n   - If the misrepresentation had been made fraudulently, the person making the misrepresentation would be liable to damages\n\n   Consequences:\n   - The person making the misrepresentation shall still be liable to damages even though the misrepresentation was not made fraudulently\n\n   Exceptions:\n   - The person making the misrepresentation proves that he had reasonable grounds to believe that the facts represented were true\n   - The person making the misrepresentation did believe up to the time the contract was made that the facts represented were true\n\n2. Misrepresentation Ordinance Cap. 284 Section 3 Subsection 2\n\n   Conditions:\n   - A person has entered into a contract\n   - He entered into a contract after a misrepresentation has been made to him\n   - The misrepresentation was not made to him fraudulently\n   - He would be entitled, by reason of the misrepresentation, to rescind the contract\n   - It is claimed in any proceedings arising out of the contract that the contract ought to be or has been rescinded\n   - The court or arbitrator is of opinion that it would be equitable to do so, having regard to:\n     * The nature of the misrepresentation\n     * The loss that would be caused by it if the contract were upheld\n     * The loss that rescission would cause to the other party\n\n   Consequences:\n   - The court or arbitrator may declare the contract subsisting and award damages in lieu of rescission\n\n   Exceptions:\n   - None\n\n### Minor Premise:\n\n1. Misrepresentation Ordinance Cap. 284 Section 3 Subsection 1:\n- Jack has entered into a contract with Emma after a misrepresentation.\n- The misrepresentation was made to him by Emma.\n- Jack has suffered loss in the form of damage claimed from his client.\n- If Emma had made the misrepresentation fraudulently, Emma would have been liable to damages.\n- However, Emma has reasonable grounds to believe her claim is true, and Emma did believe her claim was true.\n- Therefore, this section does not apply.\n\n2. Misrepresentation Ordinance Cap. 284 Section 3 Subsection 2:\n- Jack has entered into a contract of sale of a car.\n- Emma claiming the car has never been an accident is a misrepresentation.\n- Jack has entered into the contract after this misrepresentation has been made to him.\n- Emma did not make this misrepresentation fraudulently.\n- Jack would have been entitled, by reason of misrepresentation to rescind the contract, but he is barred from rescission because an innocent third party is involved. Jack tries to sought rescission from Emma.\n- Balancing the nature of the misrepresentation,\n  * it is a innocent misrepresentation but it is material and might affect the value of the car;\n  * the loss that would be suffered by Jack if the contract was upheld is minimal because he has already sold the car to Lucy; and\n  * the loss to Anna a rescission would cause would be large as the car may decrease in value and Anna has to reimburse Jack in full value.\n- Therefore, this section applies and the court would declare the contract subsisting and award Jack damages, which is the amount Lucy claims from him, in lieu of rescission.\n\n### Conclusion:\n\nMisrepresentation Ordinance Cap. 284 Section 3 Subsection 2 applies, and the court would declare the contract subsisting and award Jack damages, which is the amount Lucy claims from him, in lieu of rescission.'
        }
    ]
    chat_response = get_response(messages)
    return {"option": "Deductive reasoning: legislation", "content": chat_response}

def legal_reason_cases_deductive(issue, result):
    # After reading the results, which three cases do you think are the most relevant to the legal issue?
    messages = [
        {"role": "system", "content": "You are an intelligent and logical lawyer specialising in Hong Kong law. Hong Kong law is a common law system similar to UK (England and Wales) law. Legislation in Hong Kong is referred to as Ordinances instead of Acts. Case law is mainly the same."},
        {
            "role" : "user",
            "content": 'The search results:\n' + json.dumps(result[1:], indent=4) + '\nThe scenario:\n' + issue.get_user_input() + "\nThe area of law:\n" + issue.get_area() + "\nThe legal issue:\n" + issue.get_issue() + '\nInstruction:\nBased on the search results, choose three chunks of search results most relevant to the legal issue specific to the scenario. The three most relevant chunks should be from different cases. Output in JSON format.\nExample:\n```json\n{\n   "chunks":["chunk_id_1","chunk_id_2", "chunk_id_3"]\n}\n```'
        }
    ]
    chat_response = get_response(messages)
    chunks = json.loads(re.search(r'```json(.*?)```', chat_response, re.DOTALL).group(1))
    # get neibouring paragraphs of the three cases and ask it to identify legal rule? if cannot identify, discard (assume bad search results / no such legal rule)
    judgments = []
    for chunk in chunks['chunks']:
        texts = []
        # get previous 4 chunks
        for i in range(int(chunk.split('_')[-1]) - 1, 0, -1):
            texts.append(local_search.get_content(result[0]['option'], "_".join(chunk.split('_')[:-1]) + '_' + str(i)))
            if len(texts) == 4:
                break
        texts.reverse()
        # current chunk
        texts.append(local_search.get_content(result[0]['option'], chunk))
        # get subsequent 4 chunks after current chunk
        for i in range(int(chunk.split('_')[-1]) + 1, int(chunk.split('_')[-1]) + 5):
            texts.append(local_search.get_content(result[0]['option'], "_".join(chunk.split('_')[:-1]) + '_' + str(i)))
        texts = [text for text in texts if not text is None]
        context = " ".join(texts)
        citation = local_search.get_title(result[0]['option'], chunk)
        citation = citation[:citation.index('Extract')]
        judgments.append({"context": context, "citation": citation})
    # Deductive reasoning:
    #   major premise: identify the rule of law: if [conditions], then [consequences], unless [exception]
    #   minor premise: facts of the current case fits/not fit [conditions], is/is not [exception]
    #   conclusion: is/is not [consequence]
    major_premises = []
    for judgment in judgments:
        messages = [
            {"role": "system", "content": "You are an intelligent and logical lawyer specialising in Hong Kong law. Hong Kong law is a common law system similar to UK (England and Wales) law. Legislation in Hong Kong is referred to as Ordinances instead of Acts. Case law is mainly the same."},
            {
                "role" : "user",
                "content": 'Excerpt of ' + judgment['citation'] + ':\n' + judgment['context'] + '\nThe scenario:\n' + issue.get_user_input() + "\nThe area of law:\n" + issue.get_area() + "\nThe legal issue:\n" + issue.get_issue() + '\nInstruction:\nBased only on the excerpt of the judgment, identify the rule of law that corresponds to the legal issue specific to the scenario. You should abstract the facts into intermediate legal concepts when identifying the rule of law. Answer these 4 questions to identify the rule of law: 1. What are the conditions of the rule? 2. What is the consequence of the rule? 3. What are the exceptions to this rule? 4. What is the citation of where the legal rule is from (the current case)? If you cannot extract a rule of law relevant to the legal issue of the scenario, output an empty list.\nStrictly follow the format (JSON) of the following examples.\nExample output (irrelevant):\n```json\n[]\n```\nExample legal issue:\nWhether ABC\'s action results in a promissory estoppel\nExample excerpt of BETWEEN LUO XING JUAN ANGELA Petitioner (Respondent) and THE ESTATE OF HUI SHUI SEE, WILLY, DECEASED 1 st Respondent (1 st Appellant) HUI MI CHI 2 nd Respondent (2 nd Appellant) GLORY RISE LIMITED (in liquidation):\n 55. A promissory estoppel may be said to arise where (i) the parties are in a relationship involving enforceable or exercisable rights, duties or powers; (ii) one party (“ the promisor ”), by words or conduct, conveys or is reasonably understood to convey a clear and unequivocal promise or assurance to the other (“ the promisee ”) that the promisor will not enforce or exercise some of those rights, duties or powers; and (iii) the promisee reasonably relies upon that promise and is induced to alter his or her position on the faith of it, so that it would be inequitable or unconscionable for the promisor to act inconsistently with the promise. [53]\n56. While it is necessary for the purposes of exposition to identify the separate elements of the doctrine, it should be borne in mind that when applying them to the facts, each element does not exist in its own watertight compartment to be kept separate from the others. Each element acquires its meaning and content in the context of the other elements. This was emphasised by Robert Walker LJ in Gillett v Holt [54] in relation to proprietary estoppel in the following terms:\n    “... the doctrine of proprietary estoppel cannot be treated as subdivided into three or four watertight compartments. ... [The] quality of the relevant assurances may influence the issue of reliance, ... reliance and detriment are often intertwined, and ... whether there is a distinct need for a ‘mutual understanding’ may depend on how the other elements are formulated and understood. Moreover the fundamental principle that equity is concerned to prevent unconscionable conduct permeates all the elements of the doctrine. In the end the court must look at the matter in the round.”\n57. Thus in the present case, the meaning of the words or conduct constituting the promise or assurance has to be understood in the light of the parties’ particular relationship and especially in the light of the legal rights or powers exercisable, and known to be exercisable, by the promisor. As the learned authors of Spencer Bower put it, one should put in focus “not simply the actions of the promisor but the proper interpretation to be placed on those actions given the shared background and knowledge of the parties.” [55]\nExample output:\n```json\n[\n   {\n      "Conditions": "If (1) the parties are in a relationship involving enforceable or exercisable rights, duties or powers; and (2) one party (“ the promisor ”), by words or conduct, conveys or is reasonably understood to convey a clear and unequivocal promise or assurance to the other (“ the promisee ”) that the promisor will not enforce or exercise some of those rights, duties or powers; and (iii) the promisee reasonably relies upon that promise and is induced to alter his or her position on the faith of it, so that it would be inequitable or unconscionable for the promisor to act inconsistently with the promise; and (4) having regard the shared background and knowledge of the parties",\n      "Consequences": "Then (1) a promissory estoppel may arise",\n      "Exceptions": "Unless (1) it is inequitable to do so",\n      "Citation": "Luo Xing Juan Angela v The Estate of Hui Shui See, Willy"\n   }\n]\n```'
            }
        ]
        chat_response = get_response(messages)
        major_premise = json.loads(re.search(r'```json(.*?)```', chat_response, re.DOTALL).group(1))
        major_premises.extend(major_premise)
    if len(major_premises) > 0:
        # Minor premise
        messages = [
            {"role": "system", "content": "You are an intelligent and logical lawyer specialising in Hong Kong law. Hong Kong law is a common law system similar to UK (England and Wales) law. Legislation in Hong Kong is referred to as Ordinances instead of Acts. Case law is mainly the same."},
            {
                "role" : "user",
                "content": 'The major premise:\n' + json.dumps(major_premises, indent=4) + '\nThe scenario:\n' + issue.get_user_input() + "\nThe area of law:\n" + issue.get_area() + "\nThe legal issue:\n" + issue.get_issue() + '\nInstruction:\nInterpret the legal framework in the major premise using plain meaning. Determine if the scenario facts satisfy all conditions and avoid exceptions in the major premise by substituting the facts into the premise. Output the minor premise and the conclusion that answers the legal issue. You must make a decision. Strictly follow the output format of the following example.\nExample scenario:\nEmma, unaware of any defect, sold her vintage car to Jack, claiming it had never been in an accident, which was untrue. Jack, unaware of the misrepresentation, quickly sold the car to Lucy. When Lucy discovered the truth, she claimed damages from Jack. Jack sought rescission from Emma.\nExample legal issue:\nWhether rescission is available to Jack as a remedy to misrepresentation\nExample major premise:\n[\n\t{\n    \t"Conditions": "If (1) a person has entered into a contract after a misrepresentation; and (2) the misrepresentation has been made to him by another party; and (3) he has suffered loss as a result of the misrepresentation; and (4) if the misrepresentation had been made fraudulently, the person making the misrepresentation would be liable to damages",\n    \t"Consequences": "Then (1) the person making the misrepresentation shall still be liable to damages even though the misrepresentation was not made fraudulently",\n    \t"Exceptions": "Unless (1) the person making the misrepresentation proves that he had reasonable grounds to believe that the facts represented were true; and (2) the person making the misrepresentation did believe up to the time the contract was made that the facts represented were true",\n    \t"Citation": "Misrepresentation Ordinance Cap. 284 Section 3 Subsection 1"\n\t}\n\t{\n    \t"Conditions": "If (1) a person has entered into a contract; and (2) he entered into a contract after a misrepresentation has been made to him; and (3) the misrepresentation was not made to him fraudulently; and (4) he would be entitled, by reason of the misrepresentation, to rescind the contract; and (5) if it is claimed in any proceedings arising out of the contract that the contract ought to be or has been rescinded; and (6) the court or arbitrator is of opinion that it would be equitable to do so, having regard to the nature of the misrepresentation and the loss that would be caused by it if the contract were upheld, as well as to the loss that rescission would cause to the other party",\n    \t"Consequences": "Then (1) the court or arbitrator may declare the contract subsisting and award damages in lieu of rescission",\n    \t"Exceptions": "Unless none",\n    \t"Citation": "Misrepresentation Ordinance Cap. 284 Section 3 Subsection 2"\n\t}\n]\nExample output:\n### Relevant law:\n\nMisrepresentation Ordinance Cap. 284 Section 3 Subsection 1 and 2\n\n### Major Premise:\n\n1. Misrepresentation Ordinance Cap. 284 Section 3 Subsection 1\n   \n   Conditions:\n   - A person has entered into a contract after a misrepresentation\n   - The misrepresentation has been made to him by another party\n   - He has suffered loss as a result of the misrepresentation\n   - If the misrepresentation had been made fraudulently, the person making the misrepresentation would be liable to damages\n\n   Consequences:\n   - The person making the misrepresentation shall still be liable to damages even though the misrepresentation was not made fraudulently\n\n   Exceptions:\n   - The person making the misrepresentation proves that he had reasonable grounds to believe that the facts represented were true\n   - The person making the misrepresentation did believe up to the time the contract was made that the facts represented were true\n\n2. Misrepresentation Ordinance Cap. 284 Section 3 Subsection 2\n\n   Conditions:\n   - A person has entered into a contract\n   - He entered into a contract after a misrepresentation has been made to him\n   - The misrepresentation was not made to him fraudulently\n   - He would be entitled, by reason of the misrepresentation, to rescind the contract\n   - It is claimed in any proceedings arising out of the contract that the contract ought to be or has been rescinded\n   - The court or arbitrator is of opinion that it would be equitable to do so, having regard to:\n     * The nature of the misrepresentation\n     * The loss that would be caused by it if the contract were upheld\n     * The loss that rescission would cause to the other party\n\n   Consequences:\n   - The court or arbitrator may declare the contract subsisting and award damages in lieu of rescission\n\n   Exceptions:\n   - None\n\n### Minor Premise:\n\n1. Misrepresentation Ordinance Cap. 284 Section 3 Subsection 1:\n- Jack has entered into a contract with Emma after a misrepresentation.\n- The misrepresentation was made to him by Emma.\n- Jack has suffered loss in the form of damage claimed from his client.\n- If Emma had made the misrepresentation fraudulently, Emma would have been liable to damages.\n- However, Emma has reasonable grounds to believe her claim is true, and Emma did believe her claim was true.\n- Therefore, this section does not apply.\n\n2. Misrepresentation Ordinance Cap. 284 Section 3 Subsection 2:\n- Jack has entered into a contract of sale of a car.\n- Emma claiming the car has never been an accident is a misrepresentation.\n- Jack has entered into the contract after this misrepresentation has been made to him.\n- Emma did not make this misrepresentation fraudulently.\n- Jack would have been entitled, by reason of misrepresentation to rescind the contract, but he is barred from rescission because an innocent third party is involved. Jack tries to sought rescission from Emma.\n- Balancing the nature of the misrepresentation,\n  * it is a innocent misrepresentation but it is material and might affect the value of the car;\n  * the loss that would be suffered by Jack if the contract was upheld is minimal because he has already sold the car to Lucy; and\n  * the loss to Anna a rescission would cause would be large as the car may decrease in value and Anna has to reimburse Jack in full value.\n- Therefore, this section applies and the court would declare the contract subsisting and award Jack damages, which is the amount Lucy claims from him, in lieu of rescission.\n\n### Conclusion:\n\nMisrepresentation Ordinance Cap. 284 Section 3 Subsection 2 applies, and the court would declare the contract subsisting and award Jack damages, which is the amount Lucy claims from him, in lieu of rescission.\n'
            }
        ]
        chat_response = get_response(messages)
        return {"option": "Deductive Reasoning: " + result[0]['option'], "content": chat_response}
    else:
        return None

def legal_reason_cases_analogy(issue, option="cases"):
    # Reasoning by analogy:
    #   formulate query string for vector search
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {
            "role" : "user",
            "content": 'The scenario:\n' + issue.get_user_input() + "\nThe area of law:\n" + issue.get_area() + "\nThe legal issue:\n" + issue.get_issue() + '\nInstruction:\nPreviously, you looked for cases relevant to the legal issue but found no results. Now, generate a query string to perform vector search for relevant case law that is different from the actual facts of the scenario, but has similar fact patterns that can be used for reasoning by analogy. Expand abbreviations (CICT becomes Common Intention Constructive Trust) and remove specific information (Peter becomes Landlord, truck becomes vehicle) to enhance the effect of vector search. As the database only contains Hong Kong cases, do NOT include "Hong Kong" in your query. Follow the format of the example output.\nExample output:\nI was told I could not find relevant cases for exclusive jurisdiction clauses. An arbitration clause is not an exclusive jurisdiction clause. However, they have similar fact patterns: they are both clauses that govern the forum of dispute. This is suitable for reasoning by analogy. Therefore, I suggest the following query:\n```json\n{"query": "when should a winding up petition be stayed due to a bona fide dispute regarding a debt which is governed by arbitration clause"}\n```'
        }
    ]
    chat_response = get_response(messages, temperature=0.6, top_p=0.7)
    query = json.loads(re.search(r'```json(.*?)```', chat_response, re.DOTALL).group(1))
    query['option'] = option
    result = retrieve(query)
    #   Select the most relevant case
    messages = [
        {"role": "system", "content": "You are an intelligent and logical lawyer specialising in Hong Kong law. Hong Kong law is a common law system similar to UK (England and Wales) law. Legislation in Hong Kong is referred to as Ordinances instead of Acts. Case law is mainly the same."},
        {
            "role" : "user",
            "content": 'The search results:\n' + json.dumps(result, indent=4) + '\nThe scenario:\n' + issue.get_user_input() + "\nThe area of law:\n" + issue.get_area() + "\nThe legal issue:\n" + issue.get_issue() + '\nInstruction:\nAmong the search results, choose one chunk most relevant to the legal issue specific to the scenario for legal reasoning by analogy. If all chunks are irrelevant (not even a slight potential for analogy), output an empty dict. Use JSON format.\nExample (irrelevant):\n```json\n{}\n```\nExample:\n```json\n{\n   "chunk": "chunk_id"\n}\n```'
        }
    ]
    chat_response = get_response(messages)
    chunks = json.loads(re.search(r'```json(.*?)```', chat_response, re.DOTALL).group(1))
    if chunks == {}:
        return None
    # get neibouring paragraphs of the case
    chunk = chunks['chunk']
    texts = []
    # get previous 4 chunks
    for i in range(int(chunk.split('_')[-1]) - 1, 0, -1):
        texts.append(local_search.get_content(result[0]['option'], "_".join(chunk.split('_')[:-1]) + '_' + str(i)))
        if len(texts) == 4:
            break
    texts.reverse()
    # current chunk
    texts.append(local_search.get_content(result[0]['option'], chunk))
    # get subsequent 4 chunks after current chunk
    for i in range(int(chunk.split('_')[-1]) + 1, int(chunk.split('_')[-1]) + 5):
        texts.append(local_search.get_content(result[0]['option'], "_".join(chunk.split('_')[:-1]) + '_' + str(i)))
    texts = [text for text in texts if not text is None]
    context = " ".join(texts)
    citation = local_search.get_title(result[0]['option'], chunk)
    if citation is None:
        return None
    citation = citation[:citation.index('Extract')]
    judgment = {"context": context, "citation": citation}
    # 1. Citing Precedent: Begin by referencing a relevant previous court case, which we'll call precedent p. Clearly state the outcome, o, that was reached in this precedent. This establishes the foundation of your argument by showing a prior legal decision that is relevant to the current case. For example, you might say: "In the case of ABC v GHI (precedent p), the court ruled that... (outcome o)."

    # 2. Identifying Shared Legal Concepts: Next, identify and present a set of intermediate legal concepts (ILCs), which we'll call i. These ILCs should be associated with specific fact patterns, referred to as i*. Crucially, demonstrate that these ILCs and their associated fact patterns are present in both the precedent case p and the current case c. This similarity is key to your argument, as it establishes a connection between the two cases. You might state: "Both in ABC v GHI and in our current case, we see the following legal concepts and fact patterns..."

    # 3. Proposing a Legal Rule: Based on the shared ILCs and fact patterns, propose a legal rule. This rule should be stated as: "If the fact pattern i* is present, then outcome o should follow." Argue that this rule is justified in the precedent case p because the positive effects (E+) of outcome o on the underlying values and principles of the law outweigh the negative effects (E-) in that case. You could say: "This suggests a general rule that when we see [fact pattern i*], the court should decide [outcome o]. This rule was justified in ABC v GHI because..."

    messages = [
        {"role": "system", "content": "You are an intelligent and logical lawyer specialising in Hong Kong law. Hong Kong law is a common law system similar to UK (England and Wales) law. Legislation in Hong Kong is referred to as Ordinances instead of Acts. Case law is mainly the same."},
        {
            "role" : "user",
            "content": 'Excerpt of ' + judgment['citation'] + ' (precedent):\n' + judgment['context'] + '\nThe scenario (current case):\n' + issue.get_user_input() + "\nThe area of law:\n" + issue.get_area() + "\nThe legal issue:\n" + issue.get_issue() + '\nInstruction:\nStep 1. Citing Precedent: Begin by referencing' + judgment['citation'] + ', which we\'ll call precedent p. Briefly state the facts of p. Then clearly state the outcome, o, that was reached in this precedent. This establishes the foundation of your argument by showing a prior legal decision that is relevant to the current case. For example, you might say: "In the case of ABC v GHI (precedent p), [brief facts], the court ruled that... (outcome o)."\nStep 2. Identifying Shared Legal Concepts: Next, identify and present a set of intermediate legal concepts (ILCs), which we\'ll call i. These ILCs should be associated with specific fact patterns, referred to as i*. Crucially, demonstrate that these ILCs and their associated fact patterns are present in both the precedent case p and the current case c. This similarity is key to your argument, as it establishes a connection between the two cases. You might state: "Both in ABC v GHI and in our current case, we see the following legal concepts and fact patterns..."\nStep 3. Proposing a Legal Rule: Based on the shared ILCs and fact patterns, propose a legal rule. This rule should be stated as: "If the fact pattern i* is present, then outcome o should follow." Argue that this rule is justified in the precedent case p because the positive effects (E+) of outcome o on the underlying values and principles of the law outweigh the negative effects (E-) in that case. You could say: "This suggests a general rule that when we see [fact pattern i*], the court should decide [outcome o]. This rule was justified in ABC v GHI because..."\nFollow the instructions of Step 1 to 3 and give detailed explanation where necessary. Use the format of the example below. Terminate after finishing Step 3.\nExample output:\n### Step 1: Outcome of Precedent (ABC v GHI)\nIn the case of ABC v GHI (precedent p), [brief facts], the court ruled that [outcome o].\n### Step 2: Shared Legal Concepts\nBoth in ABC v GHI and in our current case, we see the following legal concepts and fact patterns:\n- [legal concept 1]: [fact pattern 1]\n- [legal concept 2]: [fact pattern 2]\n- [legal concept 3]: [fact pattern 3]\n- [legal concept 4]: [fact pattern 4]\n### Step 3: Extraction of legal rule from Precedent (ABC v GHI)\nThis suggests a general rule that when we see [fact pattern i*], the court should decide [outcome o]. This rule was justified in ABC v GHI because [policy arguments for outcome o on underlying values specific to p]'
        }
    ]
    chat_response = get_response(messages)
    analysis = chat_response

    # 4. Applying the Rule to the Current Case: Finally, argue that this same rule should apply to the current case c. Contend that because the fact pattern i* is present in case c, the outcome o should also be applied here. To justify this application, assert that, just as in the precedent case, the positive effects (E+) of outcome o on the underlying values and principles of the law in case c would outweigh any negative effects (E-). You might conclude: "Given that our current case shares the same crucial fact pattern i*, we submit that the court should reach the same outcome o. This decision would be justified because, as in ABC v GHI, it would have the following positive effects..."
    
    messages = [
        {"role": "system", "content": "You are an intelligent and logical lawyer specialising in Hong Kong law. Hong Kong law is a common law system similar to UK (England and Wales) law. Legislation in Hong Kong is referred to as Ordinances instead of Acts. Case law is mainly the same."},
        {
            "role" : "user",
            "content": 'Excerpt of ' + judgment['citation'] + ' (precedent):\n' + judgment['context'] + '\nThe scenario (current case):\n' + issue.get_user_input() + "\nThe area of law:\n" + issue.get_area() + "\nThe legal issue:\n" + issue.get_issue() + "\nPrevious Steps:\n" + analysis + '\nInstruction:\nStep 4. Applying the Rule to the Current Case: Finally, argue that this same rule should apply to the current case c. Contend that because the fact pattern i* is present in case c, the outcome o should also be applied here. To justify this application, assert that, just as in the precedent case, the positive effects (E+) of outcome o on the underlying values and principles of the law in case c would outweigh any negative effects (E-). You might conclude: "Given that our current case shares [the same crucial fact pattern i*], we submit that the court should reach [the same outcome o]. This decision would be justified because, as in ABC v GHI, it would have the following positive effects..."\nFollow the instructions of Step 4 and give detailed explanation where necessary. Use the format of the example below. Terminate after finishing Step 4. Do not repeat the previous steps.\nExample output:\n### Step 4: Applying the Rule to the Current Case\nIn the current case, the same legal concepts and fact patterns as the precedent (ABC v GHI) is present:\n- [legal concept 1]: [fact pattern 1]\n- [legal concept 2]: [fact pattern 2]\n- [legal concept 3]: [fact pattern 3]\n- [legal concept 4]: [fact pattern 4]\nGiven that our current case shares [fact patterns i*], we submit that the court should reach [outcome o]. This decision would be justified because, as in ABC v GHI, it would have [policy arguments for outcome o on underlying values specific to current case]'
        }
    ]
    chat_response = get_response(messages)
    analysis += "\n\n" + chat_response

    # 5. Distinction Due to Missing Feature in Current Case: Begin by identifying an intermediate legal concept (ILC) m that was present in the precedent case p. Argue that this concept m was crucial in justifying the outcome o in p, as it ensured that the positive effects on underlying legal values outweighed the negative effects. Then, point out that this crucial concept m is absent in the current case c. For example, "In the precedent case ABC v GHI, the court's decision was significantly influenced by factor m. This factor was key in ensuring that the benefits of the ruling outweighed any potential drawbacks. However, in our current case, this crucial factor m is notably absent."

    # 6. Distinction Due to Missing Feature in Precedent Case: Identify an intermediate legal concept (ILC) m that is present in the current case c but was absent in the precedent case p. Argue that the presence of m in the current case either conflicts with the shared fact pattern i* or significantly alters the balance of positive and negative effects. You could state, "Our current case involves an important factor [m] that was not present in ABC v GHI. This factor [conflicts with/significantly alters] the situation described by [i*]. Because of [m], applying the same outcome in our case would have more negative consequences than positive ones, unlike in ABC v GHI."

    messages = [
        {"role": "system", "content": "You are an intelligent and logical lawyer specialising in Hong Kong law. Hong Kong law is a common law system similar to UK (England and Wales) law. Legislation in Hong Kong is referred to as Ordinances instead of Acts. Case law is mainly the same."},
        {
            "role" : "user",
            "content": 'Excerpt of ' + judgment['citation'] + ' (precedent):\n' + judgment['context'] + '\nThe scenario (current case):\n' + issue.get_user_input() + "\nThe area of law:\n" + issue.get_area() + "\nThe legal issue:\n" + issue.get_issue() + "\nPrevious Steps:\n" + analysis + '\nInstruction:\nStep 5. Distinction Due to Missing Feature in Current Case: Begin by identifying an intermediate legal concept (ILC) m that was present in the precedent case p. Argue that this concept m was crucial in justifying the outcome o in p, as it ensured that the positive effects on underlying legal values outweighed the negative effects. Then, point out that this crucial concept m is absent in the current case c. For example, "In the precedent case ABC v GHI, the court\'s decision was significantly influenced by [factor m]. [Factor m] was key in ensuring that the benefits of the ruling [benefits] outweighed any potential drawbacks [drawbacks] because [reasons]. However, in our current case, this crucial [factor m] is notably absent as [explanation]." If you cannot identify the Distinctions in Step 5, skip to Step 6.\nStep 6. Distinction Due to Missing Feature in Precedent Case: Identify an intermediate legal concept (ILC) m that is present in the current case c but was absent in the precedent case p. Argue that the presence of m in the current case either conflicts with the shared fact pattern i* or significantly alters the balance of positive and negative effects. You could state, "Our current case involves an important factor [m] that was not present in ABC v GHI. This factor [conflicts with/significantly alters] the situation described by [i*]. Because of [m], applying the same outcome in our case would have more negative consequences than positive ones, unlike in ABC v GHI." If you cannot identify the Distinctions in Step 6, terminate your answer.\nFollow the instructions of Step 5 to 6 and give detailed explanation where necessary. Use the format of the examples below. Terminate after finishing Step 6. Do not repeat previous steps.\nExample output (cannot identify distinctions):\n### Step 5: Distinction Due to Missing Feature in Current Case\nSkipped\n### Step 6: Distinction Due to Missing Feature in Precedent Case\nSkipped\nExample output:\n### Step 5: Distinction Due to Missing Feature in Current Case\nIn the precedent case [ABC v GHI], the court\'s decision was significantly influenced by [factor m]. [Factor m] was key in ensuring that the benefits of the ruling [benefits] outweighed any potential drawbacks [drawbacks] because [reasons]. However, in our current case, this crucial [factor m] is notably absent as [explanation].\n### Step 6: Distinction Due to Missing Feature in Precedent Case\nOur current case involves an important factor [m] that was not present in [ABC v GHI]. This factor [conflicts with/significantly alters] the situation described by [i*] because [reasons]. Due to [m], applying the same [outcome o] in our case would have more negative consequences such as [negative consequences] than positive ones, unlike in [ABC v GHI] because [explanation].'
        }
    ]
    chat_response = get_response(messages)
    analysis += "\n\n" + chat_response

    # 7. Argument from Undesirable Consequence: Propose an alternative rule that includes both the shared fact pattern i* and the missing feature m. State this rule as: "If both i* and m are present, then outcome o should follow." Argue that omitting m from this rule would lead to an undesirable consequence q, or conversely, that including m prevents this undesirable outcome. If possible, support this argument by referencing explicit statements in the precedent case p that highlight the relevance of m to the decision. You might say, "We propose that the correct rule from ABC v GHI should be stated as 'When both [i*] and [m] are present, the court should decide [o].' Omitting [m] from this rule could lead to [undesirable consequence q]. Indeed, the opinion in ABC v GHI explicitly states that [m] was crucial to their decision."

    # 8. Distinction from Non-occurring Undesirable Consequence: Hypothesize about the purpose behind the rule established in the precedent case p. Suggest that this rule was created to prevent a specific undesirable consequence u. Then, demonstrate that this undesirable consequence u is not a risk in the current case c. Argue that because the purpose of the precedent's rule doesn't apply to the current case, the rule itself shouldn't apply. For instance, "The rule established in ABC v GHI was clearly designed to prevent [undesirable consequence u]. However, in our current case, there's no risk of [u] occurring. Therefore, applying the precedent's rule here would be misguided, as the very purpose it serves is not relevant to our situation."
    
    messages = [
        {"role": "system", "content": "You are an intelligent and logical lawyer specialising in Hong Kong law. Hong Kong law is a common law system similar to UK (England and Wales) law. Legislation in Hong Kong is referred to as Ordinances instead of Acts. Case law is mainly the same."},
        {
            "role" : "user",
            "content": 'Excerpt of ' + judgment['citation'] + ' (precedent):\n' + judgment['context'] + '\nThe scenario (current case):\n' + issue.get_user_input() + "\nThe area of law:\n" + issue.get_area() + "\nThe legal issue:\n" + issue.get_issue() + "\nPrevious Steps:\n" + analysis + '\nInstruction:\nStep 7. Argument from Undesirable Consequence: Propose an alternative rule that includes both the shared fact pattern i* and the missing feature m. State this rule as: "If both i* and m are present, then outcome o should follow." Argue that omitting m from this rule would lead to an undesirable consequence q, or conversely, that including m prevents this undesirable outcome. If possible, support this argument by referencing explicit statements in the precedent case p that highlight the relevance of m to the decision. You might say, "We propose that the correct rule from ABC v GHI should be stated as \'When both [i*] and [m] are present, the court should decide [o].\' Omitting [m] from this rule could lead to [undesirable consequence q]. (If applicable: Indeed, the opinion in ABC v GHI [quote] explicitly states that [m] was crucial to their decision.)" If you cannot propose an alternative rule in Step 7, skip to Step 8.\nStep 8. Distinction from Non-occurring Undesirable Consequence: Hypothesize about the purpose behind the rule established in the precedent case p. Suggest that this rule was created to prevent a specific undesirable consequence u. Then, demonstrate that this undesirable consequence u is not a risk in the current case c. Argue that because the purpose of the precedent\'s rule doesn\'t apply to the current case, the rule itself shouldn\'t apply. For instance, "The rule established in ABC v GHI was clearly designed to prevent [undesirable consequence u]. However, in our current case, there\'s no risk of [u] occurring. Therefore, applying [the precedent\'s rule] here would be misguided, as the very purpose it serves is not relevant to our situation." If you cannot identify the undesirable consequence in Step 8, terminate your answer.\nFollow the instructions of Step 7 to 8 and give detailed explanation where necessary. Use the format of the examples below. Terminate after finishing Step 8. Do not repeat previous steps.\nExample output (cannot answer):\n### Step 7: Argument from Undesirable Consequence\nSkipped\n### Step 8: Distinction from Non-occurring Undesirable Consequence\nSkipped\nExample output:\n### Step 7: Argument from Undesirable Consequence\nWe propose that the correct rule from [ABC v GHI] should be stated as \'When both [i*] and [m] are present, the court should decide [o].\' Omitting [m] from this rule could lead to [undesirable consequence q]. (If applicable: Indeed, the opinion in ABC v GHI [quote] explicitly states that [m] was crucial to their decision.)\n\n### Step 8: Distinction from Non-occurring Undesirable Consequence\nThe rule established in ABC v GHI was clearly designed to prevent [undesirable consequence u]. However, in our current case, there\'s no risk of [u] occurring. Therefore, applying [the precedent\'s rule] here would be misguided, as the very purpose it serves is not relevant to our situation.'
        }
    ]
    chat_response = get_response(messages)
    analysis += "\n\n" + chat_response

    # 9. Downplaying Significance of Distinction: When faced with a distinction between your current case and a precedent, specifically the absence of an intermediate legal concept (ILC) m in your case, focus on the potential consequences of requiring this distinction. Argue that if m were to be required for the analogy to the precedent p, it would lead to an undesirable outcome. Alternatively, highlight the beneficial consequences if m were not required. For example, you might say: "While it's true that our case lacks factor m, which was present in the precedent case ABC v GHI, requiring this factor for all similar cases would lead to [undesirable consequence]. Conversely, not requiring m would allow for [desirable outcome], which better aligns with the underlying principles of the law in this area."

    # 10. Feature Substitution: When your current case lacks an intermediate legal concept (ILC) m that was present in a relevant precedent, identify another ILC n that is present in your case but absent in the precedent. Argue that n effectively compensates for the absence of m. Demonstrate how the presence of n, combined with the shared fact pattern i*, justifies the same outcome as the precedent by showing that the positive effects on legal values still outweigh the negative effects. You might argue: "Although our case lacks factor m, which was present in ABC v GHI, we have the additional factor n. This factor n, when considered alongside the shared circumstances i*, serves a similar function to m in the precedent case. Given the presence of n, we submit that the reasoning in ABC v GHI still applies, as the positive effects on [relevant legal values] would still outweigh any potential negative consequences, just as they did in the precedent case."

    messages = [
        {"role": "system", "content": "You are an intelligent and logical lawyer specialising in Hong Kong law. Hong Kong law is a common law system similar to UK (England and Wales) law. Legislation in Hong Kong is referred to as Ordinances instead of Acts. Case law is mainly the same."},
        {
            "role" : "user",
            "content": 'Excerpt of ' + judgment['citation'] + ' (precedent):\n' + judgment['context'] + '\nThe scenario (current case):\n' + issue.get_user_input() + "\nThe area of law:\n" + issue.get_area() + "\nThe legal issue:\n" + issue.get_issue() + "\nPrevious Steps:\n" + analysis + '\nInstruction:\nStep 9. Downplaying Significance of Distinction: When faced with a distinction between your current case and a precedent, specifically the absence of an intermediate legal concept (ILC) m in your case, focus on the potential consequences of requiring this distinction. Argue that if m were to be required for the analogy to the precedent p, it would lead to an undesirable outcome. Alternatively, highlight the beneficial consequences if m were not required. For example, you might say: "While it\'s true that our case lacks [factor m], which was present in the precedent case [ABC v GHI], requiring this factor for all similar cases of [fact pattern i*] would lead to [undesirable consequence]. Conversely, not requiring [m] would allow for [desirable outcome], which better aligns with the underlying principles of the law in this area [explanation of relation to underlying principles]." If you cannot think of an argument, skip to Step 10.\nStep 10. Feature Substitution: When your current case lacks an intermediate legal concept (ILC) m that was present in a relevant precedent, identify another ILC n that is present in your case but absent in the precedent. Argue that n effectively compensates for the absence of m. Demonstrate how the presence of n, combined with the shared fact pattern i*, justifies the same outcome as the precedent by showing that the positive effects on legal values still outweigh the negative effects. You might argue: "Although our case lacks [factor m], which was present in ABC v GHI, we have the additional [factor n]. This [factor n], when considered alongside [the shared circumstances i*], serves a similar function to [m] in the precedent case. Given the presence of [n], we submit that the reasoning in [ABC v GHI] still applies, as the positive effects on [relevant legal values] would still outweigh any potential negative consequences, just as they did in the precedent case." If you cannot identify another ILC, terminate your answer.\nFollow the instructions of Step 9 to 10 and give detailed explanation where necessary. Use the format of the examples below. Terminate after finishing Step 10. Do not repeat previous steps.\nExample output (cannot answer):\n### Step 9: Downplaying Significance of Distinction\nSkipped\n\n### Step 10: Feature Substitution\nSkipped\nExample output:\n### Step 9: Downplaying Significance of Distinction\nWhile it\'s true that our case lacks [factor m], which was present in the precedent case [ABC v GHI], requiring this factor for all similar cases of [fact pattern i*] would lead to [undesirable consequence]. Conversely, not requiring [m] would allow for [desirable outcome], which better aligns with the underlying principles of the law in this area [explanation of relation to underlying principles].\n\n### Step 10: Feature Substitution\nAlthough our case lacks [factor m], which was present in ABC v GHI, we have the additional [factor n]. This [factor n], when considered alongside [the shared circumstances i*], serves a similar function to [m] in the precedent case. Given the presence of [n], we submit that the reasoning in [ABC v GHI] still applies, as the positive effects on [relevant legal values] would still outweigh any potential negative consequences, just as they did in the precedent case.'
        }
    ]
    chat_response = get_response(messages)
    analysis += "\n\n" + chat_response

    # 11. Conclusion: Having read through the original argument by analogy (Step 1 to 4), the rebuttal arguments (Step 5-8), and the surrebuttal arguments (Step 9 to 10), be neutral and determine the merits and flaws of all the arguments and make a final decision to the legal issue. Assess whether the proposed rules and their applications are supported by the facts and legal principles involved. Make a final decision on the legal issue by balancing these considerations, striving for a decision that aligns with legal precedent while also serving justice and legal consistency. Conclude with a clear and reasoned statement that explains why the decision was reached, highlighting key factors that influenced the outcome. For example, you might say: "To be completed..."
    
    messages = [
        {"role": "system", "content": "You are an intelligent and logical lawyer specialising in Hong Kong law. Hong Kong law is a common law system similar to UK (England and Wales) law. Legislation in Hong Kong is referred to as Ordinances instead of Acts. Case law is mainly the same."},
        {
            "role" : "user",
            "content": 'Excerpt of ' + judgment['citation'] + ' (precedent):\n' + judgment['context'] + '\nThe scenario (current case):\n' + issue.get_user_input() + "\nThe area of law:\n" + issue.get_area() + "\nThe legal issue:\n" + issue.get_issue() + "\nPrevious Steps:\n" + analysis + "\nInstruction:\nStep 11. Conclusion: Having read through the original argument by analogy (Step 1 to 4), the rebuttal arguments (Step 5-8), and the surrebuttal arguments (Step 9 to 10), be neutral and determine the merits and flaws of all the arguments and make a final decision to the legal issue. Assess whether the proposed rules and their applications are supported by the facts and legal principles involved. Make a final decision on the legal issue by balancing these considerations, striving for a decision that aligns with legal precedent while also serving justice and legal consistency. Conclude with a clear and reasoned statement that explains why the decision was reached, highlighting key factors that influenced the outcome.\nFollow the instructions of Step 11 and give detailed explanation where necessary. Use the format of the example below. Terminate after finishing Step 11. Do not repeat the previous steps.\nExample output:\n### Step 11: Conclusion\n\nAfter careful consideration of all arguments presented, including the initial analogy to [ABC v GHI], the distinctions raised, and the counterarguments offered, we make the following observations. The case shares [mention key similarities] with the precedent, but also differs in [mention key differences]. The proposed legal rule of [briefly state the rule] finds support in both cases, but its broader implications must be considered. We've weighed arguments from both sides, particularly [mention a strong point from each side]. Considering the underlying legal principles of [mention relevant principles] and the potential impact on future cases, we conclude that [state your decision]."
        }
    ]
    chat_response = get_response(messages)
    analysis += "\n\n" + chat_response

    return {"option": "Reasoning by analogy: cases", "content": analysis}

def consolidate_positions(issue, positions):
    title = "# " + issue.get_area() + ": " + issue.get_issue()
    answer = title + "\n\n"
    for position in positions:
        answer += "## " + position['option'] + "\n\n" + position['content'] + "\n\n"
    return answer

def generate_answer(issues):
    heading = "# Issues\n\n" + "\n\n".join([issue.get_area() + ": " + issue.get_issue() for issue in issues])
    return heading + "\n\n" + "\n".join([issue.get_consolidated_position() for issue in issues])

def run(user_input):
    issues = initial_analyse(user_input)
    for issue in issues:
        positions = []
        # Deductive reasoning
        # Deductive reasoning: legislation
        query = formulate_query(issue, option = "legislation")
        result = retrieve(query)
        temp_position = legal_reason_legislation(issue, result)
        if not temp_position is None:
            positions.append(temp_position)
        # Deductive reasoning: cfa
        query = formulate_query(issue, option = "cfa")
        result = retrieve(query)
        temp_position = legal_reason_cases_deductive(issue, result)
        if not temp_position is None:
            positions.append(temp_position)
        else:
            # Deductive reasoning: ca
            query = formulate_query(issue, option = "ca")
            result = retrieve(query)
            temp_position = legal_reason_cases_deductive(issue, result)
            if not temp_position is None:
                positions.append(temp_position)
            else:
                # Deductive reasoning: cfi
                query = formulate_query(issue, option = "cfi")
                result = retrieve(query)
                temp_position = legal_reason_cases_deductive(issue, result)
                if not temp_position is None:
                    positions.append(temp_position)
        # Reasoning by analogy: all cases
        temp_position = legal_reason_cases_analogy(issue, option="cases")
        if not temp_position is None:
            positions.append(temp_position)
        issue.set_consolidated_position(consolidate_positions(issue, positions))
    return generate_answer(issues)

def main():
    user_input = input()
    run(user_input)

if __name__ == "__main__":
    main()
