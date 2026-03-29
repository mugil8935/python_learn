import pandas as pd
from elasticsearch import Elasticsearch
from openai import OpenAI
import time
import logging
from datetime import datetime
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('indexing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize clients
es_client = Elasticsearch(["http://localhost:9200"])
openai_client = OpenAI()

# CSV file path and Index name - will be set via command line
csv_file = None
index_name = None
chunk_strategy = "size"  # "size" or "row"
chunk_size = 500  # Only used if strategy is "size"

def chunk_text(text, chunk_size=500):
    """Split text into chunks based on character size."""
    if not text or pd.isna(text):
        logger.debug("Empty or NA text encountered, skipping")
        return []
    
    text = str(text).strip()
    if not text:
        logger.debug("Text is empty after stripping")
        return []
    
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
    
    logger.debug(f"Created {len(chunks)} chunk(s) from text of length {len(text)}")
    return chunks

def chunk_row(row, df):
    """Create a single chunk from an entire row."""
    text_parts = []
    for col in df.columns:
        value = row[col]
        if pd.notna(value):
            text_parts.append(f"{col}: {value}")
    
    combined_text = " | ".join(text_parts)
    if combined_text.strip():
        logger.debug(f"Created 1 chunk from entire row with length {len(combined_text)}")
        return [combined_text]
    return []

def read_text_file(filepath):
    """Read a plain text file and return content."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info(f"[OK] Successfully read text file: {filepath}")
        logger.info(f"File size: {len(content)} characters")
        return content
    except Exception as e:
        logger.error(f"Error reading text file: {e}", exc_info=True)
        return None

def process_text_file(content):
    """Process plain text file by chunking it."""
    logger.info("=" * 60)
    logger.info("Processing plain text file")
    logger.info("=" * 60)
    
    start_time = time.time()
    
    # Delete index if it exists
    logger.info(f"Checking if index '{index_name}' exists...")
    if es_client.indices.exists(index=index_name):
        logger.warning(f"Index '{index_name}' found - deleting...")
        try:
            es_client.indices.delete(index=index_name)
            logger.info(f"[OK] Index '{index_name}' deleted successfully")
        except Exception as e:
            logger.error(f"Error deleting index: {e}", exc_info=True)
            return
    else:
        logger.info(f"Index '{index_name}' does not exist (new index)")
    
    # Create index with proper mapping
    logger.info(f"Creating index '{index_name}' with mappings...")
    index_mapping = {
        "mappings": {
            "properties": {
                "text": {
                    "type": "text"
                },
                "embedding": {
                    "type": "dense_vector",
                    "dims": 1536,
                    "index": True,
                    "similarity": "cosine"
                },
                "chunk_index": {
                    "type": "integer"
                }
            }
        }
    }
    
    try:
        es_client.indices.create(index=index_name, body=index_mapping)
        logger.info(f"[OK] Index '{index_name}' created successfully with mappings")
    except Exception as e:
        logger.error(f"Error creating index: {e}", exc_info=True)
        return
    
    # Chunk the text
    logger.info(f"Chunking text file using strategy: {chunk_strategy.upper()}")
    if chunk_strategy == "size":
        logger.info(f"Chunk size: {chunk_size} characters")
    
    chunks = chunk_text(content, chunk_size)
    
    if not chunks:
        logger.error("No valid chunks created from text file")
        return
    
    logger.info(f"Created {len(chunks)} chunk(s) from text file")
    logger.info("-" * 60)
    
    # Index chunks
    indexed_count = 0
    failed_count = 0
    
    for chunk_idx, chunk in enumerate(chunks):
        try:
            # Progress indicator every 10 chunks
            if (chunk_idx + 1) % 10 == 0:
                logger.info(f"Progress: Indexed {chunk_idx + 1}/{len(chunks)} chunks")
            
            logger.info(f"Chunk {chunk_idx}: Getting embedding...")
            embedding = get_embedding(chunk)
            
            if embedding is None:
                logger.error(f"Chunk {chunk_idx}: Failed to get embedding")
                failed_count += 1
                continue
            
            # Create document
            doc = {
                "text": chunk,
                "embedding": embedding,
                "chunk_index": chunk_idx
            }
            
            # Index to Elasticsearch
            doc_id = f"chunk_{chunk_idx}"
            logger.info(f"Chunk {chunk_idx}: Indexing document {doc_id}...")
            es_client.index(index=index_name, id=doc_id, document=doc)
            indexed_count += 1
            
            logger.info(f"[OK] Chunk {chunk_idx}: Successfully indexed")
            
            # Add delay to avoid rate limiting
            time.sleep(0.5)
        
        except Exception as e:
            logger.error(f"Chunk {chunk_idx}: Error - {e}", exc_info=True)
            failed_count += 1
            continue
    
    elapsed_time = time.time() - start_time
    
    logger.info("-" * 60)
    logger.info("=" * 60)
    logger.info("TEXT FILE INDEXING COMPLETE!")
    logger.info("=" * 60)
    logger.info(f"Total chunks created: {len(chunks)}")
    logger.info(f"Total chunks indexed: {indexed_count}")
    logger.info(f"Failed operations: {failed_count}")
    logger.info(f"Success rate: {((indexed_count / (indexed_count + failed_count)) * 100):.2f}%" if (indexed_count + failed_count) > 0 else "N/A")
    logger.info(f"Time elapsed: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
    logger.info(f"Average time per chunk: {(elapsed_time/indexed_count):.2f} seconds" if indexed_count > 0 else "N/A")
    logger.info("=" * 60)

def get_embedding(text):
    """Get embedding from OpenAI for the given text."""
    try:
        logger.info(f"Requesting embedding for text of length {len(text)}")
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        embedding = response.data[0].embedding
        logger.debug(f"Successfully received embedding with {len(embedding)} dimensions")
        return embedding
    except Exception as e:
        logger.error(f"Error getting embedding: {e}", exc_info=True)
        return None

def index_data_to_elasticsearch():
    """Read CSV and index data to Elasticsearch."""
    logger.info("=" * 60)
    logger.info("Starting Elasticsearch indexing process")
    logger.info("=" * 60)
    
    start_time = time.time()
    
    # Delete index if it exists
    logger.info(f"Checking if index '{index_name}' exists...")
    if es_client.indices.exists(index=index_name):
        logger.warning(f"Index '{index_name}' found - deleting...")
        try:
            es_client.indices.delete(index=index_name)
            logger.info(f"[OK] Index '{index_name}' deleted successfully")
        except Exception as e:
            logger.error(f"Error deleting index: {e}", exc_info=True)
            return
    else:
        logger.info(f"Index '{index_name}' does not exist (new index)")
    
    # Create index with proper mapping
    logger.info(f"Creating index '{index_name}' with mappings...")
    index_mapping = {
        "mappings": {
            "properties": {
                "text": {
                    "type": "text"
                },
                "embedding": {
                    "type": "dense_vector",
                    "dims": 1536,
                    "index": True,
                    "similarity": "cosine"
                },
                "row_id": {
                    "type": "integer"
                },
                "chunk_index": {
                    "type": "integer"
                }
            }
        }
    }
    
    try:
        es_client.indices.create(index=index_name, body=index_mapping)
        logger.info(f"[OK] Index '{index_name}' created successfully with mappings")
    except Exception as e:
        logger.error(f"Error creating index: {e}", exc_info=True)
        return
    
    # Read CSV file
    logger.info(f"Reading CSV file: {csv_file}")
    df = pd.read_csv(csv_file)
    logger.info(f"✓ Successfully loaded CSV with {len(df)} rows and {len(df.columns)} columns")
    logger.info(f"Columns: {list(df.columns)}")
    logger.info(f"Chunking strategy: {chunk_strategy.upper()}")
    if chunk_strategy == "size":
        logger.info(f"Chunk size: {chunk_size} characters")
    
    # Combine relevant columns to create text for embedding
    indexed_count = 0
    failed_count = 0
    total_chunks = 0
    
    logger.info(f"Starting to process {len(df)} rows...")
    logger.info("-" * 60)
    
    for idx, row in df.iterrows():
        try:
            # Progress indicator every 50 rows
            if (idx + 1) % 50 == 0:
                logger.info(f"Progress: Processed {idx + 1}/{len(df)} rows")
            
            logger.debug(f"Processing row {idx}")
            
            # Get chunks based on strategy
            if chunk_strategy == "row":
                # One chunk per row
                chunks = chunk_row(row, df)
            else:
                # Size-based chunks
                text_parts = []
                for col in df.columns:
                    value = row[col]
                    if pd.notna(value):
                        text_parts.append(f"{col}: {value}")
                
                combined_text = " | ".join(text_parts)
                chunks = chunk_text(combined_text, chunk_size)
            
            if not chunks:
                logger.warning(f"Row {idx}: No valid chunks to index")
                failed_count += 1
                continue
            
            logger.debug(f"Row {idx}: Created {len(chunks)} chunk(s)")
            
            # Index each chunk with its embedding
            for chunk_idx, chunk in enumerate(chunks):
                try:
                    # Get embedding for the chunk
                    logger.info(f"Row {idx}, Chunk {chunk_idx}/{len(chunks)-1}: Getting embedding...")
                    embedding = get_embedding(chunk)
                    
                    if embedding is None:
                        logger.error(f"Row {idx}, Chunk {chunk_idx}: Failed to get embedding")
                        failed_count += 1
                        continue
                    
                    # Create document
                    doc = {
                        "text": chunk,
                        "embedding": embedding,
                        "row_id": idx,
                        "chunk_index": chunk_idx
                    }
                    
                    # Index to Elasticsearch
                    doc_id = f"{idx}_{chunk_idx}"
                    logger.info(f"Row {idx}, Chunk {chunk_idx}: Indexing document {doc_id}...")
                    es_client.index(index=index_name, id=doc_id, document=doc)
                    indexed_count += 1
                    total_chunks += 1
                    
                    logger.info(f"[OK] Row {idx}, Chunk {chunk_idx}: Successfully indexed")
                    
                    # Add delay to avoid rate limiting
                    time.sleep(0.5)
                
                except Exception as chunk_err:
                    logger.error(f"Row {idx}, Chunk {chunk_idx}: Error - {chunk_err}", exc_info=True)
                    failed_count += 1
                    continue
        
        except Exception as e:
            logger.error(f"Row {idx}: Error processing row - {e}", exc_info=True)
            failed_count += 1
            continue
    
    elapsed_time = time.time() - start_time
    
    logger.info("-" * 60)
    logger.info("=" * 60)
    logger.info("INDEXING COMPLETE!")
    logger.info("=" * 60)
    logger.info(f"Total rows processed: {len(df)}")
    logger.info(f"Total chunks indexed: {indexed_count}")
    logger.info(f"Failed operations: {failed_count}")
    logger.info(f"Success rate: {((indexed_count / (indexed_count + failed_count)) * 100):.2f}%" if (indexed_count + failed_count) > 0 else "N/A")
    logger.info(f"Time elapsed: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
    logger.info(f"Average time per chunk: {(elapsed_time/indexed_count):.2f} seconds" if indexed_count > 0 else "N/A")
    logger.info("=" * 60)

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("RAG Elasticsearch Indexer Started")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # Get index name and CSV file from command line arguments
    if len(sys.argv) < 3:
        print("\n" + "=" * 60)
        print("RAG Elasticsearch Indexer")
        print("=" * 60)
        print("\nUsage: python openai_api.py <input_file> <index_name> [chunk_strategy] [chunk_size]")
        print("\nInput File Types:")
        print("  .csv        - CSV file (rows as documents)")
        print("  .txt        - Plain text file")
        print("\nExample:")
        print("  python openai_api.py final_161.csv test-index")
        print("  python openai_api.py final_161.csv test-index row")
        print("  python openai_api.py data.csv my-index size 500")
        print("  python openai_api.py document.txt text-index")
        print("  python openai_api.py document.txt text-index size 1000")
        print("\nArguments:")
        print("  input_file      : Path to CSV or text file (required)")
        print("  index_name      : Name of the Elasticsearch index (required)")
        print("  chunk_strategy  : 'row' or 'size' (optional)")
        print("                    For CSV: 'row' (default) or 'size'")
        print("                    For TXT: 'size' is used (row not applicable)")
        print("  chunk_size      : Characters per chunk (optional, default: 500)")
        print("                    Only used if chunk_strategy is 'size'")
        print("\nExamples:")
        print("  # CSV with row-based chunking (default for CSV)")
        print("  python openai_api.py final_161.csv test-index")
        print("  python openai_api.py final_161.csv test-index row")
        print("\n  # CSV with size-based chunking")
        print("  python openai_api.py final_161.csv test-index size 500")
        print("\n  # Text file with size-based chunking")
        print("  python openai_api.py document.txt text-index")
        print("  python openai_api.py document.txt text-index size 1000")
        print("\nThe script will:")
        print("  1. Detect file type (CSV or TXT)")
        print("  2. Delete the index if it exists")
        print("  3. Create a new index with proper mappings")
        print("  4. Read and chunk the input file")
        print("  5. Generate embeddings using OpenAI")
        print("  6. Index all documents in Elasticsearch")
        print("=" * 60 + "\n")
        
        logger.error("Missing required arguments: input_file and index_name")
        sys.exit(1)
    
    input_file = sys.argv[1]
    index_name = sys.argv[2]
    
    # Detect file type
    file_extension = os.path.splitext(input_file)[1].lower()
    if file_extension not in ['.csv', '.txt']:
        print(f"\nError: Unsupported file type '{file_extension}'. Supported types: .csv, .txt\n")
        logger.error(f"Unsupported file type: {file_extension}")
        sys.exit(1)
    
    # Optional chunk strategy (default depends on file type)
    if len(sys.argv) > 3:
        chunk_strategy = sys.argv[3].lower()
        if chunk_strategy not in ["row", "size"]:
            print(f"\nError: chunk_strategy must be 'row' or 'size', got '{chunk_strategy}'\n")
            sys.exit(1)
        # For text files, row strategy is not applicable
        if file_extension == '.txt' and chunk_strategy == "row":
            print(f"\nWarning: Row strategy not applicable for text files. Using 'size' instead.\n")
            logger.warning("Row strategy not applicable for text files - using size strategy")
            chunk_strategy = "size"
    else:
        # Default: row for CSV, size for text
        chunk_strategy = "row" if file_extension == '.csv' else "size"
    
    # Optional chunk size (default: 500)
    if len(sys.argv) > 4:
        try:
            chunk_size = int(sys.argv[4])
            if chunk_size < 10:
                print(f"\nError: chunk_size must be at least 10 characters\n")
                sys.exit(1)
        except ValueError:
            print(f"\nError: chunk_size must be an integer, got '{sys.argv[4]}'\n")
            sys.exit(1)
    
    logger.info(f"Input File: {input_file}")
    logger.info(f"File Type: {file_extension.upper()}")
    logger.info(f"Index Name: {index_name}")
    logger.info(f"Chunk Strategy: {chunk_strategy.upper()}")
    if chunk_strategy == "size":
        logger.info(f"Chunk Size: {chunk_size} characters")
    
    # Validate input file exists
    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        print(f"\nError: Input file not found: {input_file}\n")
        sys.exit(1)
    
    logger.info(f"[OK] Input file found: {input_file}")
    
    # Test Elasticsearch connection
    logger.info("Testing Elasticsearch connection...")
    try:
        info = es_client.info()
        es_version = info['version']['number']
        logger.info(f"[OK] Connected to Elasticsearch")
        logger.info(f"  Version: {es_version}")
        logger.info(f"  Cluster name: {info.get('cluster_name', 'N/A')}")
    except Exception as e:
        logger.error(f"[FAIL] Error connecting to Elasticsearch: {e}", exc_info=True)
        logger.error("Make sure Elasticsearch is running on localhost:9200")
        print(f"\nError: Cannot connect to Elasticsearch - {e}\n")
        sys.exit(1)
    
    # Test OpenAI connection
    logger.info("Testing OpenAI connection...")
    try:
        logger.info("[OK] OpenAI client initialized")
    except Exception as e:
        logger.error(f"[FAIL] Error with OpenAI client: {e}", exc_info=True)
        print(f"\nError: OpenAI client error - {e}\n")
        sys.exit(1)
    
    logger.info("All connections verified!")
    logger.info("-" * 60)
    
    # Process file based on type
    if file_extension == '.csv':
        csv_file = input_file
        index_data_to_elasticsearch()
    elif file_extension == '.txt':
        text_content = read_text_file(input_file)
        if text_content:
            process_text_file(text_content)
        else:
            logger.error("Failed to read text file")
            print(f"\nError: Failed to read text file\n")
            sys.exit(1)
    
    logger.info("Script execution completed")
    logger.info("Check 'indexing.log' for detailed logs")