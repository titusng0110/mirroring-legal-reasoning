import app

def run(user_input):
    messages = [
        {"role": "system", "content": "You are an intelligent and logical lawyer specialising in Hong Kong law. Hong Kong law is a common law system similar to UK (England and Wales) law. Legislation in Hong Kong is referred to as Ordinances instead of Acts. Case law is mainly the same."},
        {"role": "user", "content": 'The scenario:\n' + user_input + '\nInstruction:\nProvide a legal analysis of the scenario. First, identify the legal issues related to the scenario. Next, identify the applicable laws to the scenario. Finally, apply the law to the facts. You may refer to relevant legislation and case law. Please provide a detailed analysis.'}
    ]
    response = app.get_response(messages)
    return response

def main():
    user_input = input()
    run(user_input)

if __name__ == "__main__":
    main()