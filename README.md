# LocuSearch 🔍

**A Research Paper Uploading, Summarizing, and Searching Application**

LocuSearch is an intelligent research paper management system that combines the power of Large Language Models (LLMs) with vector search capabilities to help researchers and academics efficiently organize, search, and extract insights from their research papers.

## 🌟 Features

### 📚 Document Management
- **PDF Upload & Processing**: Upload research papers in PDF format
- **Intelligent Text Extraction**: Advanced PDF parsing with block-level text extraction
- **Metadata Management**: Automatic extraction and storage of paper titles, authors, and page information

### 🔍 Advanced Search & Retrieval
- **Semantic Search**: Vector-based similarity search using state-of-the-art embeddings
- **Context-Aware Queries**: Find relevant information across multiple papers
- **Confidence Scoring**: Results ranked by relevance with certainty scores

### 🤖 AI-Powered Summarization
- **Question-Answering**: Ask specific questions about your research papers
- **Intelligent Summarization**: Generate contextual summaries using FLAN-T5 model
- **Citation Generation**: Automatic MLA format citations for retrieved content

### 🏗️ Architecture
- **FastAPI Backend**: Modern, fast web framework for API development
- **Weaviate Vector Database**: High-performance vector search and storage
- **SQLite Database**: Lightweight relational database for user management
- **Authentication System**: Secure user authentication and authorization

## 🛠️ Technology Stack

### Core Technologies
- **Python 3.9+**: Primary programming language
- **FastAPI**: Modern web framework for building APIs
- **Weaviate**: Vector database for semantic search
- **SQLite**: Lightweight database for user management

### AI/ML Components
- **FLAN-T5 Base**: Google's instruction-tuned language model for text generation
- **E5-Base Embeddings**: State-of-the-art sentence embeddings for semantic search
- **PyMuPDF (fitz)**: Advanced PDF processing and text extraction
- **Transformers**: Hugging Face library for model inference

### Additional Libraries
- **LangChain**: Framework for LLM applications
- **Sentence Transformers**: For generating embeddings
- **Torch**: Deep learning framework
- **Alembic**: Database migration tool

## 📁 Project Structure

```
LocuSearch/
├── data/
│   └── pdf/                    # PDF documents storage
├── LocuSearch-app/             # FastAPI application
│   ├── app/
│   │   ├── api/               # API routes and dependencies
│   │   ├── core/              # Configuration and security
│   │   ├── db/                # Database models and connection
│   │   ├── helpers/           # LLM and Weaviate utilities
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   └── services/          # Business logic
│   ├── alembic/               # Database migrations
│   └── requirements.txt       # Python dependencies
├── sampleRAG.py               # RAG implementation example
├── testPython.ipynb           # Jupyter notebook for testing
├── importer.py                # Data import utilities
└── requirements.txt           # Root dependencies
```

## 🚀 Getting Started

### Prerequisites
- Python 3.9 or higher
- Weaviate server running locally or remotely
- Sufficient disk space for model downloads

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd LocuSearch
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv locenv
   source locenv/bin/activate  # On Windows: locenv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Weaviate**
   ```bash
   # Start Weaviate server (Docker)
   docker run -d \
     --name weaviate \
     -p 8080:8080 \
     -e QUERY_DEFAULTS_LIMIT=25 \
     -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
     -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
     -e DEFAULT_VECTORIZER_MODULE='none' \
     -e ENABLE_MODULES='' \
     -e CLUSTER_HOSTNAME='node1' \
     semitechnologies/weaviate:1.22.4
   ```

5. **Run the FastAPI application**
   ```bash
   cd LocuSearch-app
   uvicorn app.main:app --reload
   ```

### Usage Examples

#### 1. Upload and Process a Research Paper
```python
from sampleRAG import PDFLoader, WeaviateDB

# Initialize components
loader = PDFLoader()
database = WeaviateDB("http://localhost:8080")

# Load and process PDF
file_path = "data/pdf/research_paper.pdf"
documents = loader.load(
    file_path, 
    "Your Paper Title", 
    ["Author 1", "Author 2"]
)

# Upload to vector database
database.ensure_schema()
database.upload_file(documents)
```

#### 2. Search and Query Papers
```python
# Search for relevant content
query = "What are the main findings about machine learning?"
results = database.retrieve(query)

# Generate AI-powered response
context = build_context(query, results)
response = generate_answer(context)
print(response)
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the `LocuSearch-app` directory:

```env
DATABASE_URL=sqlite:///./loc.sqlite3
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
WEAVIATE_URL=http://localhost:8080
```

### Model Configuration
- **FLAN-T5 Base**: Used for question-answering and summarization
- **E5-Base Embeddings**: Used for semantic search
- **Device**: Automatically uses MPS (Apple Silicon) or CUDA if available

## 📊 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/logout` - User logout

### Document Management
- `POST /api/v1/document/upload` - Upload PDF document
- `GET /api/v1/document/list` - List uploaded documents
- `GET /api/v1/document/{id}` - Get document details
- `DELETE /api/v1/document/{id}` - Delete document

### Search & Query
- `POST /api/v1/document/search` - Semantic search
- `POST /api/v1/document/query` - AI-powered Q&A

## 🧪 Testing

Run the sample RAG implementation:
```bash
python sampleRAG.py
```

Or explore the Jupyter notebook:
```bash
jupyter notebook testPython.ipynb
```

## 🔮 Future Enhancements

- [ ] Web-based user interface
- [ ] Multi-user collaboration features
- [ ] Advanced filtering and sorting
- [ ] Export functionality (PDF, Word, etc.)
- [ ] Integration with academic databases
- [ ] Real-time collaboration
- [ ] Mobile application
- [ ] Advanced analytics and insights

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Google FLAN-T5**: For the instruction-tuned language model
- **Weaviate**: For the vector database solution
- **Hugging Face**: For the transformers library and model hub
- **FastAPI**: For the modern web framework

## 📞 Support

For questions, issues, or contributions, please open an issue on GitHub or contact the development team.

---

**LocuSearch** - Making research paper management intelligent and efficient! 🚀 