import os
import re
import json
import numpy as np
import pandas as pd

from embeddings.embedder import generate_embedding
from vectorstore.faiss_store import add_document, reset_index, save_index

DATA_FOLDER = "data"

# -----------------------------
# TEXT CLEANING
# -----------------------------
def clean_text(text):

    if not text:
        return ""

    text = str(text)

    junk_patterns = [
        "Skip to main content",
        "Login",
        "Privacy Policy",
        "Terms",
        "Blog",
        "Mobile View",
        "Premium",
        "Pricing",
        "Indian Kanoon",
        "Search",
        "Navigation"
    ]

    for junk in junk_patterns:
        text = text.replace(junk, " ")

    text = re.sub(r"\s+", " ", text).strip()

    return text


# -----------------------------
# LAW TYPE DETECTOR
# -----------------------------
def detect_law_type(path):

    name = path.lower()

    if "ipc" in name:
        return "IPC"
    elif "constitution" in name:
        return "CONSTITUTION"
    elif "crpc" in name or "criminal_procedure" in name:
        return "CRPC"
    elif "contract" in name:
        return "CONTRACT_ACT"
    elif "judgment" in name or "case" in name:
        return "CASE_LAW"
    elif "qa" in name:
        return "LEGAL_QA"
    else:
        return "GENERAL_LAW"


# -----------------------------
# SAFE WORD-BASED CHUNKING
# -----------------------------
def chunk_text(text, chunk_size=120):

    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)

    return chunks


# -----------------------------
# NORMALIZE EMBEDDING
# -----------------------------
def normalize_embedding(embedding):
    embedding = np.array(embedding)
    norm = np.linalg.norm(embedding)
    if norm == 0:
        return embedding
    return embedding / norm


# -----------------------------
# DUPLICATE FILTER
# -----------------------------
seen_chunks = set()

def is_duplicate(chunk):
    if chunk in seen_chunks:
        return True
    seen_chunks.add(chunk)
    return False


# -----------------------------
# PROCESS TXT FILE
# -----------------------------
def process_txt(path):

    with open(path, "r", encoding="utf-8") as f:
        text = clean_text(f.read())

    return chunk_text(text)


# -----------------------------
# PROCESS CSV FILE
# -----------------------------
def process_csv(path):

    df = pd.read_csv(path)
    text_columns = df.select_dtypes(include=["object"]).columns

    combined_text = []

    for col in text_columns:
        values = df[col].dropna().tolist()

        for v in values:
            combined_text.extend(chunk_text(clean_text(v)))

    return combined_text


# -----------------------------
# PROCESS JSON FILE
# -----------------------------
def process_json(path):

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    texts = []

    if isinstance(data, list):
        for item in data:

            if isinstance(item, dict):

                # QA dataset handling
                if "question" in item and "answer" in item:
                    qa_text = f"Question: {item['question']} Answer: {item['answer']}"
                    texts.extend(chunk_text(clean_text(qa_text)))
                else:
                    for v in item.values():
                        texts.extend(chunk_text(clean_text(v)))

            else:
                texts.extend(chunk_text(clean_text(item)))

    elif isinstance(data, dict):
        for v in data.values():
            texts.extend(chunk_text(clean_text(v)))

    return texts


# -----------------------------
# MAIN INGEST FUNCTION
# -----------------------------
def ingest_documents():

    reset_index()

    print("\nStarting UNIVERSAL LEGAL ingestion...\n")

    total_chunks = 0

    for root, dirs, files in os.walk(DATA_FOLDER):

        for file in files:

            path = os.path.join(root, file)
            law_type = detect_law_type(path)

            # skip heavy case-law for now
            if "case_law" in path.lower():
                print(f"Skipping large dataset: {file}")
                continue

            print(f"Ingesting: {file} | Type: {law_type}")

            try:

                if file.endswith(".txt"):
                    chunks = process_txt(path)

                elif file.endswith(".csv"):
                    chunks = process_csv(path)

                elif file.endswith(".json"):
                    chunks = process_json(path)

                else:
                    continue

                for chunk in chunks:

                    if not chunk or len(chunk) < 80:
                        continue

                    if is_duplicate(chunk):
                        continue

                    tagged_chunk = f"[{law_type}] {chunk}"

                    embedding = generate_embedding(tagged_chunk)
                    embedding = normalize_embedding(embedding)

                    add_document(
                        tagged_chunk,
                        embedding,
                        source=os.path.relpath(path, DATA_FOLDER).replace("\\", "/"),
                        page=0,
                        law_type=law_type,
                    )
                    total_chunks += 1

            except Exception as e:
                print(f"Error processing {file}: {e}")

    print("\nDocuments ingested into FAISS.")
    print(f"Total chunks indexed: {total_chunks}")

    # 🔥 CRITICAL STEP: persist FAISS
    save_index()
    print("FAISS persisted successfully.")

if __name__ == "__main__":
    ingest_documents()
c