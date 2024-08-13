import gradio as gr
import chat
import json
import threading
import local_search
from functools import partial

thread = None

class MyState:
    def __init__(self):
        self.has_information = False
        self.has_query_strings = False
        self.has_searched = False
        self.has_legal_advice = False
        self.interview = "You: Hello, how can I help you?\n"
        self.response1 = ""
        self.response2 = ""
        self.search_results = ""
        self.response3 = ""

def logic(message, history, state):
    state.interview += f"Client: {message}\n"
    
    if not state.has_information:
        yield "Doing Initial analysis..."
        state.response1 = chat.prompt1(state.interview)
        if "Information Complete:" in state.response1:
            state.has_information = True
            state.response1 = state.response1.replace("Information Complete:", "").strip()
            yield state.response1 + "\n" + "Generating query strings..."
        else:
            gpt_response = state.response1.replace("Information Incomplete:", "").strip()
            state.interview += f"You: {gpt_response}\n"
            yield gpt_response
    
    if state.has_information and not state.has_query_strings:
        state.response2 = chat.prompt2(state.interview, state.response1)
        state.has_query_strings = True
        yield state.response1 + "\n" + state.response2 + "\n" + "Retrieving documents..."
    
    if state.has_query_strings and not state.has_searched:
        queries = json.loads(state.response2.replace("```json", "").replace("```", ""))
        thread.join()
        state.search_results = json.dumps([local_search.search(database=query['option'], query=query['query'], k=5, bigk=50) for query in queries], indent=4)
        state.has_searched = True
        yield state.response1 + "\n" + state.response2 + "\n" + "```json\n" + state.search_results + "\n```"  + "\n" + "Generating legal advice..."
    
    if state.has_searched and not state.has_legal_advice:
        state.response3 = chat.prompt3(state.interview, state.response1, state.search_results)
        state.has_legal_advice = True
        yield state.response1 + "\n" + state.response2 + "\n" + "```json\n" + state.search_results + "\n```" + "\n" + state.response3 + "\n# DISCLAIMER: This AI must not be relied upon for actual legal advice. The information may be incomplete, inaccurate, or outdated. For any legal matters, consult a qualified, licensed lawyer in Hong Kong. We are not liable for any consequences resulting from the use of this tool. This system is for research purposes only."
    if state.has_legal_advice:
        yield state.response1 + "\n" + state.response2 + "\n" + "```json\n" + state.search_results + "\n```" + "\n" + state.response3 + "\n# DISCLAIMER: This AI must not be relied upon for actual legal advice. The information may be incomplete, inaccurate, or outdated. For any legal matters, consult a qualified, licensed lawyer in Hong Kong. We are not liable for any consequences resulting from the use of this tool. This system is for research purposes only."

with gr.Blocks(theme="soft") as demo:
    gr.Markdown("# CLIC-Chat 3.0 prototype")
    gr.Markdown("An AI legal assistant specializing in Hong Kong law. Describe your legal situation, and it will provide advice based on the information you give it.")
    gr.Markdown("## DISCLAIMER: This AI must not be relied upon for actual legal advice. The information may be incomplete, inaccurate, or outdated. For any legal matters, consult a qualified, licensed lawyer in Hong Kong. We are not liable for any consequences resulting from the use of this tool. This system is for research purposes only.")
    interface = gr.ChatInterface(
        fn=partial(logic, state=MyState()),
        chatbot=gr.Chatbot(height="66vh", value=[("", "Hello, how can I help you?")]),
        retry_btn=None,
        clear_btn=None,
        undo_btn=None
    )

if __name__ == "__main__":
    thread = threading.Thread(target=local_search.loadDB, args=({"cases": "data/hklii.parquet", "ordinances": "data/legislation_02082024_xml.parquet"},))
    thread.start()
    demo.launch(server_port=8081, share=True)