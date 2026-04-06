py indexing_script.py 
<file_name> 
<index_name> 
<chunking_strategy>(O -> defaults row if csv else size) 
chunking_strategy = size/row (only applicable for csv file) Chunking_strategy = size (for all txt file)
chunk_size = 500
<chunk_size> (O - defaults to 500 and used only for text strategy)

eg:
py indexing_script.py raw_txt instructions.txt
py indexing_script.py raw_txt instructions.txt size 1000
py indexing_script.py csv_data_size_chunk instructions.txt size 1000
py indexing_script.py csv_data_row_chunk 
py indexing_script.py csv_data_row_chunk row

invalid:
py indexing_script.py raw_txt instructions.txt row (txt file don't get row chunking)


py chatbot_gui.py <index_name>