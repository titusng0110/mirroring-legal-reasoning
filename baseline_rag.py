import app
import json
import re

def formulate_query(user_input):
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {
            "role": "user",
            "content": 'The scenario:\n' + user_input + '\nInstruction:\nBased on the scenario, generate five query strings to search a legal database. The legal database has two options \"cases\" and \"legislation\". \"cases\" contain all Hong Kong court judgments. \"legislation\" contain all Hong Kong Ordinances in effect. Here are some questions for thought. What are the legal doctrine related to the current situation and the potential remedy/claim? What are some legal issues worth exploring? What might be specific about Hong Kong law that you will want to search?\nThe query strings generated shall encapsule the semantic meaning of the question you want to search. Expand abbreviations (CICT becomes Common Intention Constructive Trust) and remove specific information (Peter becomes Landlord, truck becomes vehicle) to enhance the effect of vector embeddings. As the database only contains Hong Kong law, do NOT include \"Hong Kong\" in your query. Output in json format, e.g.:\n```json\n[\n\t{\"query\": \"your query 1\", \"option\": \"cases\"},\n\t{\"query\": \"your query 2\", \"option\": \"cases\"},\n\t{\"query\": \"your query 3\", \"option\": \"legislation\"},\n\t{\"query\": \"your query 4\", \"option\": \"legislation\"},\n\t{\"query\": \"your query 5\", \"option\": \"legislation\"}\n]\n```'
        }
    ]
    chat_response = app.get_response(messages)
    queries = json.loads(re.search(r'```json(.*?)```', chat_response, re.DOTALL).group(1))
    return queries

def generate_legal_analysis(user_input, result):
    messages = [
        {"role": "system", "content": "You are an intelligent and logical lawyer specialising in Hong Kong law. Hong Kong law is a common law system similar to UK (England and Wales) law. Legislation in Hong Kong is referred to as Ordinances instead of Acts. Case law is mainly the same."},
        {"role": "user", "content": 'The search results:\n' + json.dumps(result, indent=4) + '\nThe scenario:\n' + user_input + '\nInstruction:\nProvide a legal analysis of the scenario. First, identify the legal issues related to the scenario. Next, identify the applicable laws to the scenario. Finally, apply the law to the facts. You may refer to relevant legislation and case law. Please provide a detailed analysis.'}
    ]
    response = app.get_response(messages)
    return response

def run(user_input):
    queries = formulate_query(user_input)
    results = []
    for query in queries:
        result = app.retrieve(query)
        results.append(result)
    return generate_legal_analysis(user_input, results)

def main():
    user_input = input()
    run(user_input)

if __name__ == "__main__":
    main()