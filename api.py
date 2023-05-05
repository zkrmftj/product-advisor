from flask import Flask, request
from llama_index import SimpleDirectoryReader, GPTVectorStoreIndex, LLMPredictor, PromptHelper, StorageContext, load_index_from_storage, Document
from langchain import OpenAI 

from llama_index.langchain_helpers.text_splitter import TokenTextSplitter

import os

class AuthMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # Ambil nilai header "Authorization" dari OS variable
        auth_header = os.environ.get('AUTHORIZATION_HEADER', '')

        # Cek apakah header kosong
        if not auth_header:
            return self._unauthorized_response(start_response)

        # Validasi header sesuai kebutuhan
        # Contoh: Cek apakah header sama dengan nilai tertentu
        if auth_header != 'my-secret-header':
            return self._unauthorized_response(start_response)

        # Header valid, lanjutkan ke aplikasi Flask
        return self.app(environ, start_response)

    def _unauthorized_response(self, start_response):
        start_response('401 Unauthorized', [('Content-Type', 'text/plain')])
        return [b'Unauthorized']

def construct_index(directory_path):
    max_input_size = 4096
    num_outputs = 512
    max_chunk_overlap = 20
    chunk_size_limit = 600

    prompt_helper = PromptHelper(max_input_size, num_outputs, max_chunk_overlap, chunk_size_limit=chunk_size_limit)

    llm_predictor = LLMPredictor(llm=OpenAI(temperature=0.7, model_name="text-davinci-003", max_tokens=num_outputs))

    documents = SimpleDirectoryReader(directory_path).load_data()[0]
    text_splitter = TokenTextSplitter(separator=" ", chunk_size=2048, chunk_overlap=20)
    text_chunks = text_splitter.split_text(documents.text)
    doc_chunks = [Document(t) for t in text_chunks]

    index = GPTVectorStoreIndex.from_documents(doc_chunks, llm_predictor=llm_predictor, prompt_helper=prompt_helper)

    index.storage_context.persist()

    return index


def chatbot(input_text):
    storage_context = StorageContext.from_defaults(persist_dir="./storage")
    index = load_index_from_storage(storage_context)
    engine = index.as_query_engine()
    response = engine.query(input_text)
    print(response.response)
    return response.response

app = Flask(__name__)
app.wsgi_app = AuthMiddleware(app.wsgi_app)

@app.route("/")
def home():
    return "Hello World!"

@app.route("/query", methods=["POST"])
def query_index():
  global index
  raw = request.get_json()
  try:
     query_text = raw["message"]
  except:
     query_text = None

  if query_text is None:
    return "No text found, add message data in json field", 400
  
  response = chatbot(query_text)
  return str(response), 200

if __name__ == "__main__":
    construct_index("docs")
    app.run(host="0.0.0.0", port=5601)
