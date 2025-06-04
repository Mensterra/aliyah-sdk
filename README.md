# 📄 AI-Powered PDF-to-Article Generator

An AI-driven CrewAI Multi-Agent application that converts PDF content into polished articles. This app empowers users to generate professional articles by leveraging AI agents for PDF analysis, content creation, and editing.

## 🚀 Features

- **Multi-Agent System**: Employs CrewAI to manage specialized agents for reading, writing, and refining articles.
- **PDF Parsing**: Extracts meaningful content from uploaded PDFs.
- **AI-Powered Workflow**: Seamlessly converts PDF insights into engaging articles with minimal user input.
- **Custom Search Tool**: Integrates user queries to tailor article content to specific needs.
- **Session Management**: Tracks and saves user interactions for future reference.
- **Streamlit Interface**: User-friendly and interactive UI for uploading PDFs and generating articles.

## 🛠️ Tech Stack

- **Agents Framework**: CrewAI
- **Frontend**: Streamlit
- **Backend**: Python, SQLite (for conversation storage)
- **LLM**: OpenAI API for advanced content generation
- **Document Parsing**: Python (handling uploaded PDFs)
- **Environment Management**: dotenv for seamless API key and environment variable configuration
- **Deployed URL**: https://ragagentarticle.streamlit.app/ 

## 🌟 How It Works

1. **PDF Upload**: Users upload a PDF file through the Streamlit interface.
2. **Query Input**: Users enter a search query to tailor the content extraction.
3. **CrewAI Workflow**:
   - **PDF Reader Agent**: Parses and extracts relevant content from the uploaded PDF.
   - **Content Writer Agent**: Generates a draft article based on the parsed content and user query.
   - **Title Creator Agent**: Suggests an engaging title for the article.
   - **Editor Agent**: Proofreads and finalizes the article for publication.
4. **Output**: The generated article is displayed in the app for the user to review and save.

## 🚀 Getting Started

1. Clone the repository:
    ```bash
    git clone git@github.com:Chukwuebuka-2003/rag_agentarticle.git
    cd rag_agentarticle
    ```

2. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3. Set up environment variables:
    - Create a `.env` file in the root directory.
    - Add your API keys:
      ```env
      OPENAI_API_KEY=your_openai_api_key
      GROQ_API_KEY=your_groq_api_key
      GEMINI_API_KEY=your_gemini_api_key
      ```

4. Run the application:
    ```bash
    streamlit run rag_article.py
    ```

## 📄 Example Use Case

1. **Upload a PDF**: Upload a research paper, report, or any document in PDF format.
2. **Enter a Query**: Provide a specific topic or question to guide the article generation process.
3. **Generate an Article**: The AI-powered agents work collaboratively to extract insights, write content, and finalize an article.
4. **View Results**: Review and save the generated article directly from the Streamlit app.

## 💬 Future Enhancements

- Support for additional file formats (e.g., Word documents, HTML).
- Multi-language support for PDF content and generated articles.
- Integration with cloud storage platforms for uploading and saving files.
- Customization options for article formatting and style.
