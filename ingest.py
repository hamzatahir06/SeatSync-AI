import os
import chromadb
from ollama import embed
from pypdf import PdfReader
import docx

# Configuration constants for the input file and text splitting size
DOC_PATH = "info_about_ai.pdf"   # change to your file name
CHUNK_SIZE = 500              # characters per chunk

# Helper function to extract text from a PDF file page by page
def read_pdf(path):
    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

# Helper function to extract text from a Word document (.docx)
def read_docx(path):
    d = docx.Document(path)
    return "\n".join(p.text for p in d.paragraphs)

# Helper function to read text from a standard plain text file (.txt)
def read_txt(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

# Router function that detects the file extension and calls the appropriate reader
def load_document(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return read_pdf(path)
    elif ext == ".docx":
        return read_docx(path)
    elif ext == ".txt":
        return read_txt(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

# Splits the extracted text into smaller, uniform blocks (chunks) for processing
def chunk_text(text, size=CHUNK_SIZE):
    chunks = []
    for i in range(0, len(text), size):
        chunk = text[i:i + size].strip()
        if chunk:
            chunks.append(chunk)
    return chunks

# Main execution logic to load, chunk, embed, and store the document data
def main():
    print(f"Loading document: {DOC_PATH}")
    text = load_document(DOC_PATH)
    chunks = chunk_text(text)
    print(f"Split into {len(chunks)} chunks.")

    # Initialize a local persistent ChromaDB client to save data on the disk
    client = chromadb.PersistentClient(path="./chroma_db")
    # Fetch the collection or create it if it doesn't already exist
    collection = client.get_or_create_collection(name="my_documents")

    # Loop through each text chunk to generate its vector embedding and save it
    for i, chunk in enumerate(chunks):
        # Call the local Ollama service to generate a vector embedding for the text chunk
        response = embed(model="nomic-embed-text", input=chunk)
        vector = response["embeddings"][0]
        
        # Insert the unique ID, vector math embedding, and original raw text into ChromaDB
        collection.add(
            ids=[f"chunk_{i}"],
            embeddings=[vector],
            documents=[chunk],
        )
        print(f"Stored chunk {i+1}/{len(chunks)}")

    print("Done. Knowledge base built in ./chroma_db")

# Standard boilerplate to ensure the main function runs only when executed directly
if __name__ == "__main__":
    main()