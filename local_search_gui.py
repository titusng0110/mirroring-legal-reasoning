import gradio as gr
import local_search

def load_database_and_activate_search():
    if local_search.loadDB({"cases": "data/hklii.parquet", "ordinances": "data/legislation_02082024_xml.parquet"}):
        return gr.Button("Search", interactive=True)
    else:
        return gr.Button("Error loading database", interactive=False)

def handle_query(selected_option, query, topk, bigk):
    if bigk < topk:
        return [{"error": "Initial number of results cannot be less than final number of results."}]
    if selected_option == "HK case law (1997-2024) updated 18/07/2024":
        return local_search.search(database="cases", query=query, k=topk, bigk=bigk)
    elif selected_option == "HK legislation (tree) updated 02/08/2024":
        return local_search.search(database="ordinances", query=query, k=topk, bigk=bigk)
    else:
        return [{"error": "Please select a valid data source."}]

with gr.Blocks() as demo:
    gr.Markdown("# Law Prober")
    gr.Markdown("A tool to search and rank content from HK case law or legislation using AI vector embeddings.")
    
    data_option = gr.Radio(["HK case law (1997-2024) updated 18/07/2024", "HK legislation (tree) updated 02/08/2024"], label="Select Data Source")
    query_input = gr.Textbox(label="Query")
    bigk_slider = gr.Slider(minimum=10, maximum=400, value=80, step=1, label="Initial Top K Results")
    topk_slider = gr.Slider(minimum=1, maximum=100, value=10, step=1, label="Final Top K Results")
    search_button = gr.Button("Loading Database...", interactive=False)
    
    gr.Markdown("# IMPORTANT NOTICE REGARDING HK LEGISLATION")
    gr.Markdown("(a) Except for copyright belonging to third parties, the Government owns the copyright in all contents in HKeL, including the text of Legislation, the typographical arrangement of Legislation published in HKeL and the systematic and methodical arrangement of the data in HKeL;")
    gr.Markdown("(b) Reproduced Provisions included or displayed in the Product are replicated or reproduced from HKeL under a licence granted by the Government, and such licence does not apply to any third party rights in respect of which the Government has no authority to grant a licence;")
    gr.Markdown("(c) the Government is not responsible for the accuracy or updatedness of the Reproduced Provisions included or displayed in the Product;")
    gr.Markdown("(d) the date that the Reproduced Provisions included or displayed in the Product are up-to-date is provided in the selection of Data Source;")
    gr.Markdown('''(e)	Legislation, in both English and Chinese, is available free of charge in the HKeL website as maintained by the Department of Justice of the Government at https://www.elegislation.gov.hk, and users may visit the HKeL website to—
    (i)	access versions of Legislation with legal status, by downloading PDF copies of Legislation with pages marked with the wording "Verified Copy" at the bottom (if a "Verified Copy" of the relevant Legislation within the meaning of the Legislation Publication Ordinance (Cap. 614) has been published on the HKeL website already); and
    (ii) access versions of Legislation in other formats for information; and''')
    gr.Markdown('''(f) users may also refer to the following for versions of Legislation with legal status—
    (i) the Loose-leaf Edition of the Laws of Hong Kong (if a "Verified Copy" of the relevant Legislation has not been published on the HKeL website); and
    (Note: The Loose-leaf Edition is being phased out gradually. If a chapter has its verified copy published on HKeL, only a purple Checklist showing its position will be kept in the Edition. Subsequent updates to the chapter will only be reflected in HKeL.)
    (ii) the Government Gazette (if amendments to Legislation are yet to be incorporated in the HKeL website or the Loose-leaf Edition (as the case may be)).''')
    
    output_box = gr.JSON(label="Results")
    
    demo.load(load_database_and_activate_search, outputs=search_button)
    search_button.click(handle_query, inputs=[data_option, query_input, topk_slider, bigk_slider], outputs=output_box, trigger_mode='once')

demo.launch(server_port=8080, share=True)