from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
from flask_cors import CORS
from google import genai # Check the updated API or library for Gemini 2.0
from docx import Document
from PyPDF2 import PdfReader

from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)  # Cross-Origin Resource Sharing

UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure Gemini 2.0 API key (Assuming the configuration changes for Gemini 2.0)


load_dotenv()

client = genai.Client(api_key=os.getenv("GENAI_API_KEY"))

# Create or open the conversation document
doc_name = 'new_convo.docx'
if os.path.exists(doc_name):
    doc = Document(doc_name)
else:
    doc = Document()  # Create a new blank document
    doc.save(doc_name)

# Helper to extract text from DOCX files
def docx_to_text(file_path):
    document = Document(file_path)
    return "\n".join([paragraph.text for paragraph in document.paragraphs])

# Helper to convert PDF to text
def pdf_to_text(file_path):
    pdf_reader = PdfReader(file_path)
    text = "".join(page.extract_text() for page in pdf_reader.pages)
    return text

# Accumulate all document texts for summarization
def get_all_docs_summary():
    doc2_texts = []
    doc_files = [
        'docs/Employee Policy.docx', 
        'docs/HR Policy 1.docx', 
        'docs/Remote Work Policy.docx', 
        'docs/IT POLICY MANUAL.docx',
        'docs/HR POLICY MANUAL.docx',
        'docs/Company Healthcare Policy.docx',
        'docs/Company Transportation Policy.docx',
        'docs/Company Workplace Security Policy.docx'
    ]
    
    for doc_file in doc_files:
        if os.path.exists(doc_file):
            doc2 = Document(doc_file)
            doc2_texts.append("".join([paragraph.text for paragraph in doc2.paragraphs]))
    
    # Combine all document texts and summarize them
    combined_text = "\n".join(doc2_texts)
    response =client.models.generate_content(
            model="gemini-2.0-flash",
            contents= f"Summarize the following content: \n\n{combined_text}")
    doc2_response = response.text
    return doc2_response

doc2_response = get_all_docs_summary()

# Handle text response with entire conversation history
def handle_text_input(input_text):
    doc.add_paragraph(f"User: {input_text}")  # Append new input

    # Combine entire conversation
    conversation_history = "\n".join([paragraph.text for paragraph in doc.paragraphs])
    full_text = f"{conversation_history}\n\n'only response for this, the above is the history,dont give any formating  '\n\n\nUser: {input_text}"
    
    # Call Gemini 2.0 model to get response
    response =client.models.generate_content(
            model="gemini-2.0-flash",
            contents= full_text)
    response = response.text
    
    # Save the response in the document
    doc.add_paragraph(f"Bot: {response}")
    doc.add_paragraph(doc2_response)  # Include doc2 summary as context
    doc.save(doc_name)
    
    return response

@app.route('/', methods=['GET'])
def test():
    # Return the conversation history for testing purposes
    doc = Document(doc_name)
    conversation_history = "\n".join([paragraph.text for paragraph in doc.paragraphs])
    return jsonify({"message": conversation_history})

@app.route('/bot', methods=['POST'])
def process_request():
    text_input = request.form.get('text', '')
    file = request.files.get('file')
    r_format = request.form.get('format', '').lower()

    if not text_input and not file:
        return jsonify({"error": "No input provided"}), 400

    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Handle different file formats
        if r_format == "pdf":
            extracted_text = pdf_to_text(file_path)
        elif r_format == "docx":
            extracted_text = docx_to_text(file_path)
        else:
            return jsonify({"error": "Unsupported file format"}), 400
        
        response = handle_text_input(extracted_text)
        return jsonify({"status": "File processed successfully", "text": response}), 200

    if text_input:
        response = handle_text_input(text_input)
        return jsonify({"status": "Query processed successfully", "text": response}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
