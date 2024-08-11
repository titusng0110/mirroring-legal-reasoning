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

def prompt1(interview):
    messages = [
        {"role": "system", "content": "You are an intelligent and logical lawyer providing legal advice on Hong Kong law. Hong Kong law is very similar to UK law."},
        {
            "role" : "user",
            "content": f"Here is an interview between you and the client:\n{interview}\nHere are the Questions:\n1) Is the client the plaintiff or the defendant or seeking advice for potential scenario?\n2) What are the areas of law (at most three) related to the case?\n3) If the client is the plaintiff, what are all their respective potential remedies available to the client? If the client is the defendant, what are all their respective potential claims against the client?\nIf you do not have enough information to answer the Questions, or it is obvious the client has not finished telling their situation, ask the client for key facts that will help you answer the Questions. Ask only one question at a time so as not to overwhelm the client. Don't press the client if he/she doesn't know the answer to your question. Start with \"Information Incomplete:\\n\" and output a question with the format as Example 1 and 2.\nExample 1: Information Incomplete:\nCan you tell me more about why your employer fired you?\nExample 2: Information Incomplete:\nWhat is the timeline of who lived in the flat and who made payments to the mortgage of the flat?\nIf you have enough information to answer the Questions, output your answer with the format as Example 3 and 4, start with \"Information Complete:\\n\":\nExample 3:\nInformation Complete:\nThe client is the plaintiff.\nArea of law #1: contract law\nPotential remedy: damages, rescission, termination\nArea of law #2: tort law\nPotential remedy: damages\nArea of law #3: employment law\nPotential remedy: damages\nExample 4:\nInformation Complete:\nThe client is the defendant.\nArea of law #1: land law\nPotential claims: equitable interest\nArea of law #2: trust law\nPotential claims: equitable interest"
        }
    ]
    # for i in messages:
    #     print(i)
    completion = client.chat.completions.create(
        model = model,
        messages = messages
    )
    chat_response = completion.choices[0].message.content
    return chat_response


def prompt2(interview, response1):
    messages=[
        { "role": "system", "content": "You are an AI assistant specializing in generating query strings for vector search."},
        {
            "role": "user",
            "content" : interview + "\n" + response1 + "\nBased on the areas of law identified, generate five query strings to search a legal database. The legal database has two options \"cases\" and \"ordinances\". \"cases\" contain all Hong Kong court judgments. \"ordinances\" contain all Hong Kong Ordinances in effect. Here are some questions for thought. What are the legal doctrine related to the current situation and the potential remedy/claim? What are some legal issues worth exploring? What might be specific about Hong Kong law that you will want to search?\nThe query strings generated shall encapsule the semantic meaning of the question you want to search. Expand abbreviations (CICT becomes Common Intention Constructive Trust) and remove specific information (Peter becomes Landlord, truck becomes vehicle) to enhance the effect of vector embeddings. As the database only contains Hong Kong law, do NOT include \"Hong Kong\" in your query. Output in json format, e.g.:\n```json\n[\n\t{\"query\": \"your query 1\", \"option\": \"cases\"},\n\t{\"query\": \"your query 2\", \"option\": \"cases\"},\n\t{\"query\": \"your query 3\", \"option\": \"ordinances\"},\n\t{\"query\": \"your query 4\", \"option\": \"ordinances\"},\n\t{\"query\": \"your query 5\", \"option\": \"ordinances\"}\n]\n```"
        }
    ]
    completion = client.chat.completions.create(
        model = model,
        messages = messages
    )
    chat_response = completion.choices[0].message.content
    return chat_response

def prompt3(interview, response1, search_results):
    messages = [
        { "role": "system", "content": "You are an intelligent and logical AI legal assistant providing legal advice on Hong Kong law."},
        {
            "role": "user",
            "content": f"Interview:\n{interview}\nInitial Analysis:\n{response1}\n Legal Sources:\n{search_results}\nBased only on the information given (legal sources might be irrelevant, be careful), write a detailed legal advice directly to the client in complete sentences. You must mention the relevant facts, a thorough explanation, and next steps the client should take. In your explanation, mention what the law is, analyze the law to the facts, and explain step by step the analysis to the layman client. Avoid legal jargon, explain as if the client is a high school student."
        }
    ]
    completion = client.chat.completions.create(
        model = model,
        messages = messages
    )
    chat_response = completion.choices[0].message.content
    return chat_response


if __name__ == "__main__":
    thread = threading.Thread(target=local_search.loadDB, args=({"cases": "data/hklii_cases_18072024.parquet", "ordinances": "data/legislation_20072024.parquet"},))
    thread.start()
    response1 = ""
    interview = "You: Hello, how can I help you?\n"
    print("GPT: Hello, how can I help you?")
    while True:
        client_input = input("Client: ")
        interview += f"Client: {client_input}\n"
        response1 = prompt1(interview)
        if "Information Complete:" in response1:
            response1 = response1.replace("Information Complete:", "").strip()
            break
        else:
            gpt_response = response1.replace("Information Incomplete:", "").strip()
            interview += f"You: {gpt_response}\n"
            print(f"GPT: {gpt_response}")
    
    print("\n")
    print(interview)
    print("\n")
    print(response1)
    response2 = prompt2(interview, response1)
    print("\n")
    print(response2)
    queries = json.loads(response2.replace("```json", "").replace("```", ""))
    thread.join()
    search_results = json.dumps([local_search.search(database=query['option'], query=query['query'], k=10, bigk=100) for query in queries])
    print("\n")
    print(search_results)
    response3 = prompt3(interview, response1, search_results)
    print("\n")
    print(response3)
    




