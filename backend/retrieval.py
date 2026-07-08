import re
import sqlite3
from backend.database import get_connection

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "do",
    "for", "from", "has", "have", "i", "if", "in", "is", "it", "me",
    "my", "no", "not", "of", "on", "or", "our", "please", "the", "this",
    "to", "was", "with", "you", "your"
}

def tokenize(text):
    return {
        token
        for token in re.findall(r"[a-z0-9_]+", text.lower())
        if token not in STOPWORDS and len(token) > 2
    }

def search_knowledge_base(query, top_k=3):
    """
    Search the knowledge documents table using token overlap scoring.
    Exposes ranked documents with relevance scores.
    """
    conn = get_connection()
    try:
        # Load all documents from the DB
        docs = conn.execute("SELECT doc_id, title, source_path, content FROM knowledge_documents").fetchall()
        
        query_tokens = tokenize(query)
        if not query_tokens:
            # If no meaningful tokens, return empty list or first top_k docs
            return []
            
        ranked = []
        for doc in docs:
            doc_id, title, source_path, content = doc
            
            # Compute token overlap score
            doc_text = f"{doc_id} {title} {content}"
            doc_tokens = tokenize(doc_text)
            overlap = len(query_tokens & doc_tokens)
            
            # Boost score if query terms match doc_id exactly or title
            boost = 0
            for qt in query_tokens:
                if qt in doc_id.lower():
                    boost += 5
                if qt in title.lower():
                    boost += 2
                    
            score = overlap + boost
            if score > 0:
                # Get a small snippet of the document (first 250 characters)
                snippet = content[:250].strip() + "..." if len(content) > 250 else content
                ranked.append({
                    "doc_id": doc_id,
                    "title": title,
                    "source_path": source_path,
                    "snippet": snippet,
                    "content": content,
                    "score": score
                })
                
        # Sort by score descending
        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked[:top_k]
    finally:
        conn.close()

if __name__ == "__main__":
    # Quick sanity test
    results = search_knowledge_base("damaged physical items replacement order")
    for r in results:
        print(f"[{r['doc_id']}] {r['title']} (score={r['score']})")
