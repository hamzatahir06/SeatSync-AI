import chromadb
from ollama import embed, chat

# Initialize local vector database connection
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="my_documents")


def get_relevant_chunks(question, n_results=5):
    response = embed(model="nomic-embed-text", input=question)
    query_vector = response["embeddings"][0]
    results = collection.query(query_embeddings=[query_vector], n_results=n_results)
    return results["documents"][0]


def ask_document(question):
    context = "\n\n".join(get_relevant_chunks(question))

    prompt = f"""
Answer ONLY using the context below. Do not use outside knowledge.

If the answer is not explicitly present in the context,
reply with exactly: "I don't know based on the provided document."

Context:
{context}

Question:
{question}

Answer:
"""

    response = chat(
        model="llama3.2",
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0}
    )
    return response["message"]["content"]


def classify_intent(text):
    prompt = f"""Classify the user's message into exactly ONE category.
Reply with ONLY the category word in capital letters, nothing else — no punctuation, no explanation.

Categories:
BOOK     -> wants to book/reserve a bus seat or appointment
STATUS   -> wants to check an existing booking, or is giving/referring to a booking number
HISTORY  -> wants to review all of his booking history till today.
CANCEL   -> wants to cancel an existing booking
SUPPORT  -> wants to talk to a human, helpline, or support team
DOCUMENT -> anything else, including general knowledge questions

Examples (including typos and casual phrasing):
"i wanna book a seaat" -> BOOK
"check it for 123" -> STATUS
"chekc my booking 402" -> STATUS
"whats my status, appointment 555" -> STATUS
"cancel my seat" -> CANCEL
"all bookings" OR "my tickets" or "Seating history" -> HISTORY
"i dont want my booking anymore, number is 200" -> CANCEL
"i want contact hepline" -> SUPPORT
"talk to a real person" -> SUPPORT
"what is machine learning" -> DOCUMENT
"where is ML used" -> DOCUMENT
Message: "{text}"

Category:"""

    response = chat(
        model="llama3.2",
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0}
    )
    result = response["message"]["content"].strip().upper()

    for category in ["BOOK", "STATUS", "CANCEL", "SUPPORT", "DOCUMENT", "HISTORY"]:
        if category in result:
            return category
    return "DOCUMENT"