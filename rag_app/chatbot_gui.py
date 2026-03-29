import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import threading
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
        logging.FileHandler('chatbot_gui.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize clients
es_client = Elasticsearch(["http://localhost:9200"])
openai_client = OpenAI()

# Configuration
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4"
MAX_CONTEXT_CHUNKS = 10
CONTEXT_WINDOW = 2000


class RAGChatbot:
    """RAG-based Chatbot that retrieves context from Elasticsearch and uses OpenAI to answer."""
    
    def __init__(self, index_name):
        """Initialize the chatbot."""
        self.index_name = index_name
        logger.info(f"RAG Chatbot Initialized with index: {self.index_name}")
    
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
    
    def retrieve_context(self, query, num_results=MAX_CONTEXT_CHUNKS):
        """Retrieve relevant context from Elasticsearch using hybrid search (most accurate)."""
        logger.info(f"Retrieving context for query: '{query}'")
        
        try:
            # Get embedding for the query
            query_embedding = self.get_embedding(query)
            if query_embedding is None:
                logger.error("Failed to generate query embedding")
                return []
            
            # Try hybrid search first (BEST ACCURACY - KNN + text match)
            logger.info(f"Attempting hybrid search (KNN + text match) with top {num_results} results")
            try:
                results = es_client.search(
                    index=self.index_name,
                    body={
                        "query": {
                            "bool": {
                                "should": [
                                    # Text-based match (keyword search)
                                    {
                                        "match": {
                                            "text": {
                                                "query": query,
                                                "boost": 1.0
                                            }
                                        }
                                    },
                                    # Vector-based match (semantic search with native KNN)
                                    {
                                        "knn": {
                                            "field": "embedding",
                                            "query_vector": query_embedding,
                                            "k": num_results
                                        }
                                    }
                                ],
                                "minimum_should_match": 1
                            }
                        },
                        "size": num_results
                    }
                )
                
                logger.info("[OK] Using hybrid search (KNN + text match) - HIGHEST ACCURACY")
            
            except Exception as hybrid_error:
                logger.warning(f"Hybrid search failed: {hybrid_error}. Trying native KNN...")
                
                try:
                    # Fallback to native KNN (ES 8.8+)
                    results = es_client.search(
                        index=self.index_name,
                        body={
                            "query": {
                                "knn": {
                                    "field": "embedding",
                                    "query_vector": query_embedding,
                                    "k": num_results
                                }
                            }
                        }
                    )
                    
                    logger.info("[OK] Using native KNN search - HIGH ACCURACY")
                
                except Exception as knn_error:
                    logger.warning(f"Native KNN failed: {knn_error}. Falling back to cosineSimilarity...")
                    
                    # Fallback to script_score with cosineSimilarity (ES < 8.8)
                    results = es_client.search(
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
                            "size": num_results
                        }
                    )
                    
                    logger.info("[OK] Using cosineSimilarity (fallback) - MEDIUM ACCURACY")
            
            # Extract relevant documents
            documents = []
            for hit in results['hits']['hits']:
                doc = {
                    "text": hit['_source'].get('text', ''),
                    "row_id": hit['_source'].get('row_id'),
                    "chunk_index": hit['_source'].get('chunk_index'),
                    "score": hit['_score']
                }
                documents.append(doc)
                logger.debug(f"Retrieved doc (score: {hit['_score']:.4f})")
            
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
            
            context_parts.append(f"[Document {idx}]\n{text}\n")
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
            return answer
        
        except Exception as e:
            logger.error(f"Error generating answer: {e}", exc_info=True)
            return "Sorry, I encountered an error while generating the answer."
    
    def ask(self, query, num_context=MAX_CONTEXT_CHUNKS):
        """Main method to ask a question and get an answer."""
        logger.info(f"Query: {query}")
        
        try:
            # Step 1: Retrieve relevant context
            documents = self.retrieve_context(query, num_context)
            
            if not documents:
                logger.warning("No relevant documents found")
                return "I couldn't find relevant information in the knowledge base to answer your question.", []
            
            # Log chunks used
            logger.info(f"=" * 60)
            logger.info(f"CHUNKS USED FOR QUERY: {query}")
            logger.info(f"=" * 60)
            for idx, doc in enumerate(documents, 1):
                row_id = doc.get('row_id', 'N/A')
                chunk_idx = doc.get('chunk_index', 'N/A')
                score = doc.get('score', 'N/A')
                text_preview = doc['text'][:100000].replace('\n', ' ')
                logger.info(f"Chunk {idx}: Row {row_id}, Index {chunk_idx}, Score {score:.4f}")
                logger.info(f"  Text: {text_preview}...")
            logger.info(f"=" * 60)
            
            # Step 2: Build context prompt
            context = self.build_context_prompt(documents)
            
            if not context.strip():
                logger.warning("Context prompt is empty")
                return "I couldn't extract meaningful context from the retrieved documents.", []
            
            # Step 3: Generate answer
            answer = self.generate_answer(query, context)
            return answer, documents
        
        except Exception as e:
            logger.error(f"Error in ask method: {e}", exc_info=True)
            return "An unexpected error occurred. Please try again.", []
    
    def test_connection(self):
        """Test connection to Elasticsearch and OpenAI."""
        logger.info("Testing connections...")
        
        # Test Elasticsearch
        try:
            info = es_client.info()
            logger.info(f"[OK] Elasticsearch connected (v{info['version']['number']})")
            return True, f"Elasticsearch v{info['version']['number']}"
        except Exception as e:
            logger.error(f"[FAIL] Elasticsearch connection failed: {e}")
            return False, f"Elasticsearch: {str(e)}"


class ChatbotGUI:
    """GUI for the RAG Chatbot."""
    
    def __init__(self, root, index_name):
        """Initialize the GUI."""
        self.root = root
        self.index_name = index_name
        self.chatbot = RAGChatbot(index_name)
        self.setup_gui()
        self.test_connections()
    
    def setup_gui(self):
        """Setup the GUI components."""
        self.root.title(f"RAG Chatbot - Index: {self.index_name}")
        self.root.geometry("900x700")
        self.root.configure(bg="#f0f0f0")
        
        # Title
        title_frame = tk.Frame(self.root, bg="#2c3e50")
        title_frame.pack(fill=tk.X)
        
        title_label = tk.Label(
            title_frame,
            text=f"RAG Chatbot",
            font=("Arial", 18, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title_label.pack(pady=10)
        
        index_label = tk.Label(
            title_frame,
            text=f"Index: {self.index_name}",
            font=("Arial", 10),
            bg="#2c3e50",
            fg="#ecf0f1"
        )
        index_label.pack(pady=5)
        
        # Chat display area
        chat_frame = tk.Frame(self.root, bg="white")
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        chat_label = tk.Label(
            chat_frame,
            text="Conversation:",
            font=("Arial", 10, "bold"),
            bg="white",
            fg="#2c3e50"
        )
        chat_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=("Arial", 10),
            bg="#ecf0f1",
            fg="#2c3e50",
            height=20
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        self.chat_display.config(state=tk.DISABLED)
        
        # Configure text tags for styling
        self.chat_display.tag_config("user", foreground="#27ae60", font=("Arial", 10, "bold"))
        self.chat_display.tag_config("assistant", foreground="#2980b9", font=("Arial", 10, "bold"))
        self.chat_display.tag_config("system", foreground="#e74c3c", font=("Arial", 9, "italic"))
        
        # Input area
        input_frame = tk.Frame(self.root, bg="white")
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        input_label = tk.Label(
            input_frame,
            text="Your Question:",
            font=("Arial", 10, "bold"),
            bg="white",
            fg="#2c3e50"
        )
        input_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.input_field = tk.Entry(
            input_frame,
            font=("Arial", 10),
            bg="#ecf0f1",
            fg="#2c3e50"
        )
        self.input_field.pack(fill=tk.X, pady=(0, 10))
        self.input_field.bind("<Return>", lambda e: self.send_message())
        
        # Button frame
        button_frame = tk.Frame(self.root, bg="white")
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.send_button = tk.Button(
            button_frame,
            text="Send",
            command=self.send_message,
            font=("Arial", 10, "bold"),
            bg="#27ae60",
            fg="white",
            padx=20,
            pady=8,
            cursor="hand2"
        )
        self.send_button.pack(side=tk.LEFT, padx=(0, 10))
        
        clear_button = tk.Button(
            button_frame,
            text="Clear Chat",
            command=self.clear_chat,
            font=("Arial", 10),
            bg="#95a5a6",
            fg="white",
            padx=20,
            pady=8,
            cursor="hand2"
        )
        clear_button.pack(side=tk.LEFT)
        
        # Status bar
        self.status_label = tk.Label(
            self.root,
            text="Ready",
            font=("Arial", 9),
            bg="#34495e",
            fg="#ecf0f1",
            pady=5
        )
        self.status_label.pack(fill=tk.X)
    
    def test_connections(self):
        """Test connections to services."""
        self.update_status("Testing connections...")
        
        success, message = self.chatbot.test_connection()
        if success:
            self.add_system_message(f"Connected: {message}")
            self.update_status("Ready - Connected to Elasticsearch")
        else:
            self.add_system_message(f"Connection Error: {message}")
            self.update_status("Error - Connection failed")
            messagebox.showerror(
                "Connection Error",
                f"Failed to connect to Elasticsearch:\n{message}\n\nMake sure Elasticsearch is running on localhost:9200"
            )
    
    def send_message(self):
        """Send a message and get a response."""
        query = self.input_field.get().strip()
        
        if not query:
            messagebox.showwarning("Empty Query", "Please enter a question")
            return
        
        # Add user message to display
        self.add_user_message(query)
        
        # Clear input field
        self.input_field.delete(0, tk.END)
        
        # Disable send button
        self.send_button.config(state=tk.DISABLED)
        self.update_status("Thinking...")
        
        # Get answer in a separate thread to prevent GUI freezing
        threading.Thread(target=self.get_answer, args=(query,), daemon=True).start()
    
    def get_answer(self, query):
        """Get answer from chatbot (runs in separate thread)."""
        try:
            answer, documents = self.chatbot.ask(query)
            self.root.after(0, self.add_assistant_message, answer, documents)
        except Exception as e:
            logger.error(f"Error getting answer: {e}")
            self.root.after(0, self.add_system_message, f"Error: {str(e)}")
        finally:
            self.root.after(0, self.enable_send_button)
    
    def add_user_message(self, message):
        """Add user message to chat display."""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "You: ", "user")
        self.chat_display.insert(tk.END, f"{message}\n\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def add_assistant_message(self, message, documents=None):
        """Add assistant message to chat display."""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "Assistant: ", "assistant")
        self.chat_display.insert(tk.END, f"{message}\n")
        
        # Add chunks info if available
        if documents:
            self.chat_display.insert(tk.END, "\n[Context Chunks Used]\n", "system")
            for idx, doc in enumerate(documents, 1):
                row_id = doc.get('row_id', 'N/A')
                chunk_idx = doc.get('chunk_index', 'N/A')
                score = doc.get('score', 'N/A')
                text_preview = doc['text'][:80].replace('\n', ' ')
                self.chat_display.insert(
                    tk.END,
                    f"  Chunk {idx}: Row {row_id}, Idx {chunk_idx}, Score {score:.4f}\n",
                    "system"
                )
                self.chat_display.insert(tk.END, f"    {text_preview}...\n")
        
        self.chat_display.insert(tk.END, "\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
        self.update_status("Ready")
    
    def add_system_message(self, message):
        """Add system message to chat display."""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "[System] ", "system")
        self.chat_display.insert(tk.END, f"{message}\n\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def clear_chat(self):
        """Clear the chat display."""
        if messagebox.askyesno("Clear Chat", "Are you sure you want to clear the chat?"):
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete(1.0, tk.END)
            self.chat_display.config(state=tk.DISABLED)
    
    def enable_send_button(self):
        """Enable the send button."""
        self.send_button.config(state=tk.NORMAL)
        self.update_status("Ready")
    
    def update_status(self, message):
        """Update status bar."""
        self.status_label.config(text=message)
        self.root.update_idletasks()


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("RAG Chatbot GUI Application Started")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # Get index name from command line arguments
    if len(sys.argv) < 2:
        print("\n" + "=" * 60)
        print("RAG Chatbot - GUI Interface")
        print("=" * 60)
        print("\nUsage: python chatbot_gui.py <index_name>")
        print("\nExample:")
        print("  python chatbot_gui.py test-index")
        print("  python chatbot_gui.py my-index")
        print("\nArguments:")
        print("  index_name  : Name of the Elasticsearch index (required)")
        print("=" * 60 + "\n")
        
        logger.error("Missing required argument: index_name")
        sys.exit(1)
    
    index_name = sys.argv[1]
    logger.info(f"Index Name: {index_name}")
    
    # Create and run GUI
    root = tk.Tk()
    gui = ChatbotGUI(root, index_name)
    root.mainloop()
    
    logger.info("RAG Chatbot GUI Application Ended")


if __name__ == "__main__":
    main()
