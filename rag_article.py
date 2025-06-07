import streamlit as st
import os
from dotenv import load_dotenv
import aliyah_sdk
import uuid
from datetime import datetime

# Load environment variables first
load_dotenv()

# Initialize Aliyah SDK for agent tracing
@st.cache_resource
def initialize_aliyah_sdk():
    """Initialize Aliyah SDK with proper error handling (cached for Streamlit)"""
    try:
        aliyah_sdk.init(
            auto_start_session=False,  # Manage sessions manually for better control
            instrument_llm_calls=True,  # Automatically instrument LLM calls
            agent_id=int(os.getenv("AGENT_ID", 1)),  # Set your agent ID
            agent_name=os.getenv("AGENT_NAME", "pdf_article_streamlit_app")  # Set your agent name
        )

        # Enable OpenAI instrumentation for LLM tracing
        try:
            from opentelemetry.instrumentation.openai import OpenAIInstrumentor
            openai_instrumentor = OpenAIInstrumentor()
            openai_instrumentor.instrument()
            st.success("✅ Aliyah SDK initialized with OpenAI instrumentation")
            return True
        except Exception as e:
            st.warning(f"Warning: Could not enable OpenAI instrumentation: {e}")
            return False

    except Exception as e:
        st.error(f"Error initializing Aliyah SDK: {e}")
        return False

# Initialize SDK
sdk_initialized = initialize_aliyah_sdk()

# Load API keys from Streamlit secrets
os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]

from main import ArticleCrew

# App title
st.title("PDF to Article Generator with AI Tracing")

# Add SDK status indicator in sidebar
with st.sidebar:
    st.header("🔍 AI Tracing Status")
    if sdk_initialized:
        st.success("✅ Aliyah SDK Active")
    else:
        st.error("❌ Aliyah SDK Not Active")

# Initialize session state for conversations
if "conversations" not in st.session_state:
    st.session_state.conversations = {}

# Load previous conversation if selected
def load_conversation(conversation_id):
    st.session_state.current_conversation = st.session_state.conversations[conversation_id]

# Sidebar for managing conversations
st.sidebar.title("Previous Conversations")
if st.session_state.conversations:
    conversation_ids = list(st.session_state.conversations.keys())
    selected_conversation = st.sidebar.selectbox("Select a conversation:", conversation_ids)
    if st.sidebar.button("Load Conversation"):
        load_conversation(selected_conversation)

# File uploader for PDF
uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
if uploaded_file:
    # Save uploaded file temporarily
    temp_path = f"/tmp/{uploaded_file.name}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success(f"PDF uploaded and ready to process: {uploaded_file.name}")

    # User input for search query
    user_input = st.text_input("Enter your search query:")

    # Add session naming option
    session_name = st.text_input("Session name (optional):",
                                placeholder=f"auto_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

    if user_input:
        if st.button("Generate Article", type="primary"):
            # Show processing status
            with st.spinner("Processing PDF and generating article... This may take a few minutes."):

                # Initialize ArticleCrew with inputs and file path
                inputs = {"user_input": user_input, "file_path": temp_path}
                article_crew = ArticleCrew(inputs=inputs)

                try:
                    # Log the start of processing if SDK is available
                    if sdk_initialized:
                        try:
                            aliyah_sdk.log_event("pdf_processing_started", {
                                "pdf_name": uploaded_file.name,
                                "query": user_input,
                                "timestamp": datetime.now().isoformat()
                            })
                        except Exception as e:
                            st.warning(f"Could not log start event: {e}")

                    # Execute the CrewAI workflow with tracing
                    response = article_crew.run(session_name=session_name or None)

                    st.write("### Final Output:")
                    st.markdown(response)  # Display the output

                    # Store the current conversation in session state
                    if "current_conversation" not in st.session_state:
                        st.session_state.current_conversation = []

                    st.session_state.current_conversation.append({
                        "role": "user",
                        "content": user_input,
                        "pdf_name": uploaded_file.name,
                        "timestamp": datetime.now().isoformat()
                    })
                    st.session_state.current_conversation.append({
                        "role": "assistant",
                        "content": response,
                        "timestamp": datetime.now().isoformat()
                    })

                    # Save conversation with a unique ID
                    conversation_id = f"{uploaded_file.name}_{str(uuid.uuid4())[:8]}"
                    st.session_state.conversations[conversation_id] = st.session_state.current_conversation

                    # Log successful completion
                    if sdk_initialized:
                        try:
                            aliyah_sdk.log_event("pdf_processing_completed", {
                                "pdf_name": uploaded_file.name,
                                "query": user_input,
                                "conversation_id": conversation_id,
                                "result_length": len(str(response)) if response else 0,
                                "timestamp": datetime.now().isoformat()
                            })
                        except Exception as e:
                            st.warning(f"Could not log completion event: {e}")

                    st.success("✅ Article generated successfully!")

                except Exception as e:
                    # Log error event
                    if sdk_initialized:
                        try:
                            aliyah_sdk.log_event("pdf_processing_error", {
                                "pdf_name": uploaded_file.name,
                                "query": user_input,
                                "error": str(e),
                                "timestamp": datetime.now().isoformat()
                            })
                        except Exception as log_e:
                            st.warning(f"Could not log error event: {log_e}")

                    st.error(f"An error occurred: {e}")
else:
    st.info("Please upload a PDF to begin.")

# Display conversation history if available
if "current_conversation" in st.session_state and st.session_state.current_conversation:
    st.write("### Conversation History")
    for message in st.session_state.current_conversation:
        if message["role"] == "user":
            st.write(f"**You:** {message['content']}")
            if "pdf_name" in message:
                st.caption(f"PDF: {message['pdf_name']} | Time: {message.get('timestamp', 'N/A')}")
        else:
            st.write(f"**Assistant:** {message['content'][:200]}...")
            st.caption(f"Time: {message.get('timestamp', 'N/A')}")
        st.write("---")
