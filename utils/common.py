import google.generativeai as genai

def get_embedding(text: str):
    """Generate embedding for text"""
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_query"
    )
    return result['embedding']