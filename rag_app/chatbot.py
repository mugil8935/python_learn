import logging
from datetime import datetime
from elasticsearch import Elasticsearch
from openai import OpenAI
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chatbot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize clients
es_client = Elasticsearch(["http://localhost:9200"])
openai_client = OpenAI()

# Configuration
INDEX_NAME = "test-index"
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4"
MAX_CONTEXT_CHUNKS = 5
CONTEXT_WINDOW = 2000


class RAGChatbot:
    """RAG-based Chatbot that retrieves context from Elasticsearch and uses OpenAI to answer."""
    
    def __init__(self, index_name):
        """Initialize the chatbot."""
        self.index_name = index_name
        logger.info("=" * 60)
        logger.info("RAG Chatbot Initialized")
        logger.info(f"Index: {self.index_name}")
        logger.info("=" * 60)
    
    def get_embedding(self, text):
        """Get embedding from OpenAI for the given text."""
        try:
            logger.debug(f"Generating embedding for text of length {len(text)}")
            response = openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text
            )
            embedding = response.data[0].embedding
            logger.debug(f"Embedding generated successfully ({len(embedding)} dims)")
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            return None
    
    def _apply_reciprocal_rank_fusion(self, text_results, vector_results, rrf_k=60):
        """
        Combine text and vector search results using Reciprocal Rank Fusion (RRF).
        RRF formula: score = 1 / (k + rank)
        More robust than score normalization because it's rank-based.
        """
        combined = {}
        rrf_scores = {}
        
        # Add text search results with RRF scoring
        for rank, hit in enumerate(text_results.get('hits', {}).get('hits', []), 1):
            doc_id = hit['_id']
            rrf_score = 1.0 / (rrf_k + rank)
            combined[doc_id] = hit
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + rrf_score
        
        # Add vector search results with RRF scoring
        for rank, hit in enumerate(vector_results.get('hits', {}).get('hits', []), 1):
            doc_id = hit['_id']
            rrf_score = 1.0 / (rrf_k + rank)
            if doc_id not in combined:
                combined[doc_id] = hit
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + rrf_score
        
        # Sort by combined RRF scores
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_docs, combined

    def retrieve_context(self, query, num_results=MAX_CONTEXT_CHUNKS):
        """
        Retrieve context using HYBRID SEARCH with RRF (Reciprocal Rank Fusion).
        Best approach for combining multiple search signals:
        - Text search: captures exact keyword matches
        - Vector search: captures semantic meaning
        """
        logger.info(f"Retrieving context for query: '{query}'")
        
        try:
            # Get embedding for the query
            query_embedding = self.get_embedding(query)
            if query_embedding is None:
                logger.error("Failed to generate query embedding")
                return []
            
            # Step 1: Text-based search
            logger.info("Step 1: Performing text-based search...")
            try:
                text_results = es_client.search(
                    index=self.index_name,
                    body={
                        "query": {
                            "match": {
                                "text": {
                                    "query": query,
                                    "fuzziness": "AUTO"
                                }
                            }
                        },
                        "size": num_results * 2
                    }
                )
                logger.info(f"Text search returned {len(text_results['hits']['hits'])} results")
            except Exception as e:
                logger.warning(f"Text search failed: {e}")
                text_results = {"hits": {"hits": []}}
            
            # Step 2: Vector-based search
            logger.info("Step 2: Performing vector-based search...")
            try:
                vector_results = es_client.search(
                    index=self.index_name,
                    body={
                        "query": {
                            "knn": {
                                "field": "embedding",
                                "query_vector": query_embedding,
                                "k": num_results * 2
                            }
                        },
                        "size": num_results * 2
                    }
                )
                logger.info(f"Vector search (KNN) returned {len(vector_results['hits']['hits'])} results")
            except Exception as e:
                logger.warning(f"KNN search failed: {e}. Trying cosineSimilarity...")
                try:
                    vector_results = es_client.search(
                        index=self.index_name,
                        body={
                            "query": {
                                "script_score": {
                                    "query": {
                                        "match_all": {}
                                    },
                                    "script": {
                                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                        "params": {
                                            "query_vector": query_embedding
                                        }
                                    }
                                }
                            },
                            "size": num_results * 2
                        }
                    )
                    logger.info(f"CosineSimilarity search returned {len(vector_results['hits']['hits'])} results")
                except Exception as fallback_error:
                    logger.error(f"All vector searches failed: {fallback_error}")
                    vector_results = {"hits": {"hits": []}}
            
            # Step 3: Combine using RRF
            logger.info("Step 3: Combining results with Reciprocal Rank Fusion...")
            sorted_docs, combined = self._apply_reciprocal_rank_fusion(text_results, vector_results)
            
            # Step 4: Extract top N documents
            documents = []
            for doc_id, rrf_score in sorted_docs[:num_results]:
                hit = combined[doc_id]
                doc = {
                    "text": hit['_source'].get('text', ''),
                    "row_id": hit['_source'].get('row_id'),
                    "chunk_index": hit['_source'].get('chunk_index'),
                    "score": hit['_score'],
                    "rrf_score": rrf_score
                }
                documents.append(doc)
                logger.debug(f"Final result (RRF: {rrf_score:.6f}, ES: {hit['_score']:.4f}): Row {doc['row_id']}, Chunk {doc['chunk_index']}")
            
            logger.info(f"[OK] Hybrid search (RRF) retrieved {len(documents)} documents")
            return documents
        
        except Exception as e:
            logger.error(f"Error retrieving context: {e}", exc_info=True)
            return []
            
            logger.info(f"[OK] Retrieved {len(documents)} relevant documents")
            return documents
        
        except Exception as e:
            logger.error(f"Error retrieving context: {e}", exc_info=True)
            return []
    
    def build_context_prompt(self, documents):
        """Build context string from retrieved documents."""
        logger.debug("Building context prompt from documents")
        
        if not documents:
            logger.warning("No documents provided for context")
            return ""
        
        context_parts = []
        total_length = 0
        
        for idx, doc in enumerate(documents, 1):
            text = doc['text']
            # Limit context window
            if total_length + len(text) > CONTEXT_WINDOW:
                logger.debug(f"Context window limit reached at document {idx}")
                break
            
            context_parts.append(f"[Document {idx} - Row {doc['row_id']}, Chunk {doc['chunk_index']}]\n{text}\n")
            total_length += len(text)
        
        context = "\n".join(context_parts)
        logger.debug(f"Context prompt built: {len(context)} characters")
        return context
    
    def generate_answer(self, query, context):
        """Generate answer using OpenAI based on context and query."""
        logger.info(f"Generating answer for query: '{query}'")
        
        try:
            system_prompt = """You are a helpful assistant that answers questions based on the provided context. 
If the context doesn't contain relevant information to answer the question, say so honestly.
Provide clear, concise, and accurate answers based only on the context provided."""
            
            user_prompt = f"""Context Information:
{context}

Question: {query}

Please answer the question based on the context provided above."""
            
            logger.info(f"Calling OpenAI API with model: {LLM_MODEL}")
            response = openai_client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content
            logger.info(f"[OK] Answer generated successfully")
            logger.debug(f"Answer: {answer[:100]}...")
            
            return answer
        
        except Exception as e:
            logger.error(f"Error generating answer: {e}", exc_info=True)
            return "Sorry, I encountered an error while generating the answer."
    
    def ask(self, query, num_context=MAX_CONTEXT_CHUNKS):
        """Main method to ask a question and get an answer."""
        logger.info("=" * 60)
        logger.info(f"Query: {query}")
        logger.info("=" * 60)
        
        try:
            # Step 1: Retrieve relevant context
            logger.info("Step 1: Retrieving relevant context...")
            documents = self.retrieve_context(query, num_context)
            
            if not documents:
                logger.warning("No relevant documents found")
                return "I couldn't find relevant information in the knowledge base to answer your question."
            
            # Step 2: Build context prompt
            logger.info("Step 2: Building context prompt...")
            context = self.build_context_prompt(documents)
            
            if not context.strip():
                logger.warning("Context prompt is empty")
                return "I couldn't extract meaningful context from the retrieved documents."
            
            # Step 3: Generate answer
            logger.info("Step 3: Generating answer with OpenAI...")
            answer = self.generate_answer(query, context)
            
            # Log the interaction
            logger.info("-" * 60)
            logger.info(f"Final Answer:\n{answer}")
            logger.info("-" * 60)
            
            return answer
        
        except Exception as e:
            logger.error(f"Error in ask method: {e}", exc_info=True)
            return "An unexpected error occurred. Please try again."
    
    def interactive_chat(self):
        """Start an interactive chat session."""
        logger.info("=" * 60)
        logger.info("Starting Interactive Chat Session")
        logger.info("Type 'exit' or 'quit' to end the conversation")
        logger.info("=" * 60)
        
        print("\n" + "=" * 60)
        print("RAG Chatbot - Interactive Mode")
        print("=" * 60)
        print("Type your questions below. Type 'exit' to quit.\n")
        
        while True:
            try:
                query = input("You: ").strip()
                
                if not query:
                    print("Please enter a question.\n")
                    continue
                
                if query.lower() in ['exit', 'quit', 'bye']:
                    logger.info("User ended the conversation")
                    print("\nGoodbye! Thank you for using the RAG Chatbot.")
                    break
                
                # Get answer
                answer = self.ask(query)
                print(f"\nAssistant: {answer}\n")
            
            except KeyboardInterrupt:
                logger.info("Chat interrupted by user")
                print("\n\nChat interrupted. Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error in interactive chat: {e}", exc_info=True)
                print(f"Error: {e}\n")
    
    def test_connection(self):
        """Test connection to Elasticsearch and OpenAI."""
        logger.info("Testing connections...")
        
        # Test Elasticsearch
        try:
            info = es_client.info()
            logger.info(f"[OK] Elasticsearch connected (v{info['version']['number']})")
        except Exception as e:
            logger.error(f"[FAIL] Elasticsearch connection failed: {e}")
            return False
        
        # Test OpenAI
        try:
            logger.info("[OK] OpenAI client initialized")
        except Exception as e:
            logger.error(f"[FAIL] OpenAI connection failed: {e}")
            return False
        
        logger.info("[OK] All connections successful")
        return True


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("RAG Chatbot Application Started")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # Initialize chatbot
    chatbot = RAGChatbot()
    
    # Test connections
    if not chatbot.test_connection():
        logger.error("Connection test failed. Exiting.")
        sys.exit(1)
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        # Single query mode
        query = " ".join(sys.argv[1:])
        logger.info(f"Single query mode: {query}")
        answer = chatbot.ask(query)
        print(f"\nQuestion: {query}\n")
        print(f"Answer:\n{answer}\n")
    else:
        # Interactive mode
        chatbot.interactive_chat()
    
    logger.info("RAG Chatbot Application Ended")


if __name__ == "__main__":
    main()
