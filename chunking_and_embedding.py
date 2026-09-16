from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid
from langchain_core.tools import tool

EMBEDDING_MODEL = "nomic-embed-text"
COLLECTION_NAME = "business_rules"

TEXT_FILE = "business_logic.txt"



embeddings = OllamaEmbeddings(
    model = EMBEDDING_MODEL
)

with open(TEXT_FILE, "r", encoding="utf-8") as f:
    text = f.read()


document = Document(
    page_content=text,
    metadata={
        "source": TEXT_FILE
    }
)    

text_splitter = SemanticChunker(
    embeddings,
    breakpoint_threshold_type="percentile"
)

chunks = text_splitter.create_documents([text])

client = QdrantClient(
    url="http://localhost:6333"
)

test_embedding = embeddings.embed_query("test")
vector_size = len(test_embedding)

#-----------------------------------------------
# Create the collection if it doesn't exist
#-----------------------------------------------

if not client.collection_exists(COLLECTION_NAME):
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size = vector_size,
            distance=Distance.COSINE
        )
    )
    print("collection created: {COLLECTION_NAME}")


#------------------------------------------------
# Generate embeddings
#------------------------------------------------

points = []
for chunk in chunks:

    vector = embeddings.embed_query(
        chunk.page_content
    )

    point = PointStruct(
        id = str(uuid.uuid4()),
        vector = vector,
        payload={
            "text": chunk.page_content,
            "source": TEXT_FILE
        }
    )

    points.append(point)


#--------------------------------------------------
# Store vectors in Qdrant
#--------------------------------------------------

client.upsert(
    collection_name=COLLECTION_NAME,
    points = points
)

print(f"Stored {len(points)} embeddings in Qdrant")



#---------------------------------------------------
# Retrieval function
#---------------------------------------------------

@tool
def retrieve_business_rules(query: str, k: int=3) -> list[str]:
    """
    Search the company's factoring buisness rules.

    Use this tool when you need buisness policies, eligibility rules,
    approval requirements, fees, limits, risk rules, invoice rules,
    payment terms, or any other company-specific business logic.
    """
    query_vector = embeddings.embed_query(query)

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit = k
    ).points

    if not results:
        return "No relevant buisness rules were found."

    return"\n\n---\n\n".join(
        result.payload["text"]
        for result in results
    )

#test
if __name__ == "__main__":

    #-------------------------------------------------------
    # Test Search
    #-------------------------------------------------------    
    query = "what is the minimum invoice value for factoring?"
    query_vector = embeddings.embed_query(query)

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=3
    ).points

    for i, result in enumerate(results, start=1):
        print(f"_____result{i}_____")
        print(result.payload["text"])
        print("Score:", result.score)