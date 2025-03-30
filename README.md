# ChatWithDocs API

This is the backend service for the ChatWithDocs application, a document-based chatbot that uses Retrieval-Augmented Generation (RAG) to answer questions based on your uploaded documents.

**Frontend application available at**: [https://chatwithdocs-front.vercel.app](https://chatwithdocs-front.vercel.app)

## System Architecture

<img width="838" alt="image" src="https://github.com/user-attachments/assets/8c782113-9cb9-4326-aa04-c89f424ae340" />

## Features

### Authentication System
- Auth0 integration for secure user authentication
- Secure token management and user sessions
- Simple login option for development environments

### Document Management
- Upload documents (PDF, DOCX, etc.)
- Document storage using AWS S3 or MinIO
- Automatic document processing and text extraction

### Conversation Management
- Create and manage chat threads
- Store conversation history
- Associate documents with specific conversations

### Document Indexing
- Automatic document chunking for better retrieval
- Vector embedding generation using OpenAI models
- Vector storage in Pinecone for fast similarity search

### RAG-powered Chatbot
- Retrieval of relevant document chunks based on user questions
- Integration with large language models (OpenAI, Anthropic)
- Streaming responses for better user experience

## Project Structure

### Main Components

- `api/`: FastAPI application with routers and database models
  - `routers/`: API endpoints for auth, conversations, documents, and chatbot
  - `database/`: SQLAlchemy models and database connections
  - `config/`: Application settings and configuration

- `ingestion/`: Document processing and indexing
  - `document_processor.py`: Extracts text from different document formats
  - `ingestor.py`: Orchestrates the document processing workflow
  - `pinecone_indexer.py`: Manages vector indexing in Pinecone

- `retrieval/`: Vector search and document retrieval
  - `pinecone_utils.py`: Utilities for querying the Pinecone vector database

- `agent/`: Chatbot logic using LangGraph
  - `graph.py`: RAG conversation flow definition
  - `nodes.py`: Processing nodes for the conversation graph
  - `llm_config.py`: Configuration for language models

## How It Works

1. **User Authentication**: Users log in through Auth0 or a simplified login system
2. **Document Upload**: Documents are uploaded to S3/MinIO and registered in the database
3. **Document Processing**: 
   - Text is extracted from documents
   - Documents are split into smaller chunks
   - Chunks are embedded using OpenAI embeddings
   - Vectors are stored in Pinecone
4. **Conversation**: 
   - User asks a question in a conversation thread
   - System retrieves relevant document chunks from Pinecone
   - LLM generates a response based on the retrieved context
   - Response is streamed back to the user

## Running Locally

1. **Clone the repository**
   ```
   git clone https://github.com/yourusername/ChatWithDocs-API.git
   cd ChatWithDocs-API
   ```

2. **Create a virtual environment**
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file with the following variables:
   ```
   # Auth0 Configuration
   AUTH0_DOMAIN=your-auth0-domain
   AUTH0_CLIENT_ID=your-auth0-client-id
   AUTH0_CLIENT_SECRET=your-auth0-client-secret
   AUTH0_CALLBACK_URL=http://localhost:8000/auth/callback

   # API Configuration
   MIDDLEWARE_SECRET_KEY=your-secret-key
   FRONTEND_URL=http://localhost:5173
   API_URL=http://localhost:8000

   # Database
   DATABASE_URL=postgresql://user:password@localhost/dbname

   # AWS S3 or MinIO
   S3_BUCKET_NAME=your-bucket-name
   S3_ACCESS_KEY=your-access-key
   S3_SECRET_KEY=your-secret-key
   S3_REGION_NAME=your-region

   # OpenAI API
   OPENAI_API_KEY=your-openai-api-key

   # Pinecone
   PINECONE_API_KEY=your-pinecone-api-key
   ```

5. **Run the application**
   ```
   uvicorn api.main:app --reload
   ```

6. **Access the API**
   The API will be available at http://localhost:8000
   
   API documentation is available at http://localhost:8000/docs
