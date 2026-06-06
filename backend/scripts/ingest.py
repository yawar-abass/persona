import os
import re
import base64
import requests
from glob import glob
from pypdf import PdfReader
from dotenv import load_dotenv
from google import genai
from pinecone import Pinecone

# Load environment variables
load_dotenv()

# Initialize modern production clients
if not os.getenv("GEMINI_API_KEY") or not os.getenv("PINECONE_API_KEY"):
    raise ValueError("Missing critical API keys in environment variables.")

ai_client = genai.Client()
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("scaler-rag")

def get_embedding(text: str) -> list[float]:
    """Generates text embeddings using the standard Google GenAI SDK."""
    response = ai_client.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )
    return response.embeddings[0].values

def chunk_text(text: str, max_chars: int = 1000, overlap: int = 200) -> list[str]:
    """Splits text into clean paragraphs/sections with a sliding window overlap."""
    text = re.sub(r'\s+', ' ', text).strip()
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunk = text[start:end]
        chunks.append(chunk)
        start += (max_chars - overlap)
    return chunks

def extract_text_from_pdf(file_path: str) -> str:
    """Safely extracts text from a PDF."""
    try:
        reader = PdfReader(file_path)
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
        return full_text
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        return ""

def process_local_documents(directory: str, source_type: str) -> list[dict]:
    """Scans a directory for PDFs/TXTs and chunks them into RAG documents."""
    documents = []
    if not os.path.exists(directory):
        print(f"Directory '{directory}' not found. Skipping.")
        return documents

    # Grab both PDFs and Text files
    files = glob(f"{directory}/*.pdf") + glob(f"{directory}/*.txt") + glob(f"{directory}/*.md")
    
    for file_path in files:
        print(f"Processing {source_type} file: {file_path}")
        
        if file_path.endswith('.pdf'):
            text = extract_text_from_pdf(file_path)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

        if not text.strip():
            continue

        chunks = chunk_text(text, max_chars=800, overlap=150)
        file_name = os.path.basename(file_path).replace(" ", "_")
        
        for i, chunk in enumerate(chunks):
            documents.append({
                "id": f"{source_type}_{file_name}_chunk_{i}",
                "text": chunk,
                "metadata": {"source": source_type, "file": file_name, "type": "profile_data"}
            })
            
    return documents

def get_all_github_repos(username: str) -> list[str]:
    """Paginates through GitHub API to get all public, non-forked repo names."""
    print(f"Fetching all repositories for GitHub user: {username}...")
    repos = []
    page = 1
    headers = {}
    if os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = f"token {os.getenv('GITHUB_TOKEN')}"

    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"GitHub API Error: {response.status_code} - {response.text}")
            break
            
        data = response.json()
        if not data:
            break # No more pages
            
        for repo in data:
            # Skip forks to avoid cluttering your AI with other people's code
            if not repo["fork"]:
                repos.append(repo["name"])
        page += 1
        
    print(f"Found {len(repos)} original public repositories.")
    return repos

def process_github_readmes(username: str) -> list[dict]:
    """Fetches and chunks READMEs for all repositories."""
    repos = get_all_github_repos(username)
    documents = []
    headers = {}
    if os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = f"token {os.getenv('GITHUB_TOKEN')}"

    for repo_name in repos:
        print(f"Fetching README for: {repo_name}")
        url = f"https://api.github.com/repos/{username}/{repo_name}/readme"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            content_b64 = response.json().get("content", "")
            try:
                readme_text = base64.b64decode(content_b64).decode("utf-8")
                
                # Split by markdown sub-headings
                sections = readme_text.split("\n## ")
                for i, section in enumerate(sections):
                    if not section.strip():
                        continue
                        
                    clean_text = f"## {section}" if i > 0 else section
                    chunks = chunk_text(clean_text, max_chars=1000, overlap=200)
                    
                    for j, chunk in enumerate(chunks):
                        documents.append({
                            "id": f"github_{repo_name}_sec_{i}_chunk_{j}",
                            "text": chunk,
                            "metadata": {"source": "github", "repo": repo_name, "type": "codebase"}
                        })
            except Exception as e:
                print(f"Failed to decode README for {repo_name}: {e}")
        else:
             # Often returns 404 if a repo doesn't have a README
             print(f" -> No README found for {repo_name}")

    return documents

def upload_to_vector_db(documents: list[dict]):
    """Vectorizes and batch upserts document objects to Pinecone."""
    if not documents:
        print("No documents to upload.")
        return
        
    print(f"Vectorizing and uploading {len(documents)} total chunks to Pinecone...")
    vectors_to_upsert = []
    
    for doc in documents:
        try:
            embedding = get_embedding(doc["text"])
            vectors_to_upsert.append({
                "id": doc["id"],
                "values": embedding,
                "metadata": {
                    "page_content": doc["text"], 
                    **doc["metadata"]
                }
            })
        except Exception as e:
            print(f"Error vectorizing document {doc['id']}: {e}")
            
    # Batch upsert (Pinecone limit is typically 100 vectors per request)
    batch_size = 50
    for i in range(0, len(vectors_to_upsert), batch_size):
        batch = vectors_to_upsert[i:i + batch_size]
        index.upsert(vectors=batch)
        print(f"Successfully upserted batch {i // batch_size + 1} / {(len(vectors_to_upsert) // batch_size) + 1}")

if __name__ == "__main__":
    all_docs = []
    
    # 1. Process Resumes
    all_docs.extend(process_local_documents("data", "resume"))
    
    # 2. Process LinkedIn Data
    # all_docs.extend(process_local_documents("data", "linkedin"))
    
    # 3. Process All GitHub Repositories
    # Note: Replace with your actual GitHub username
    github_username = "yawar-abass" 
    all_docs.extend(process_github_readmes(github_username))
    
    # 4. Upload to Pinecone
    if all_docs:
        upload_to_vector_db(all_docs)
        print("\n🎉 Phase 1 Complete: Vector Database populated safely with all sources.")
    else:
        print("\n❌ Error: No documents extracted. Pipeline aborted.")