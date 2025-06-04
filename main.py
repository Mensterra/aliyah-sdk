__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import os
from dotenv import load_dotenv
import aliyah_sdk

# Load environment variables first
load_dotenv()

# Initialize Aliyah SDK for agent tracing
def initialize_aliyah_sdk():
    """Initialize Aliyah SDK with proper error handling"""
    try:
        aliyah_sdk.init(
            auto_start_session=False,  # Manage sessions manually for better control
            instrument_llm_calls=True,  # Automatically instrument LLM calls
            agent_id=int(os.getenv("AGENT_ID", 1)),  # Set your agent ID
            agent_name=os.getenv("AGENT_NAME", "pdf_article_generator")  # Set your agent name
        )

        # Enable OpenAI instrumentation for LLM tracing
        try:
            from opentelemetry.instrumentation.openai import OpenAIInstrumentor
            openai_instrumentor = OpenAIInstrumentor()
            openai_instrumentor.instrument()
            print("✅ Aliyah SDK initialized with OpenAI instrumentation")
            return True
        except Exception as e:
            print(f"Warning: Could not enable OpenAI instrumentation: {e}")
            return False

    except Exception as e:
        print(f"Error initializing Aliyah SDK: {e}")
        return False

# Initialize SDK
sdk_initialized = initialize_aliyah_sdk()

from crewai import Crew, Process
from rag_tool import CustomPDFSearchTool
from agents import ArticleAgents
from tasks import ArticleTasks

class ArticleCrew:
    def __init__(self, inputs, file_path=None):
        self.inputs = inputs
        self.file_path = file_path
        self.rag_tool = CustomPDFSearchTool()
        self.agents = ArticleAgents(llm=None, rag_tool=self.rag_tool)
        self.tasks = ArticleTasks(
            self.agents.get_agents()["pdf_reader"],
            self.agents.get_agents()["article_writer"],
            self.agents.get_agents()["title_creator"],
            self.agents.get_agents()["editor"],
        )
        self.session_id = None

    def start_tracing_session(self, session_name=None):
        """Start a new Aliyah tracing session"""
        if sdk_initialized:
            try:
                session_name = session_name or f"pdf_article_generation_{hash(str(self.inputs))}"
                self.session_id = aliyah_sdk.start_session(session_name)
                print(f"✅ Started Aliyah tracing session: {session_name}")
                return self.session_id
            except Exception as e:
                print(f"Warning: Could not start Aliyah session: {e}")
                return None
        return None

    def end_tracing_session(self):
        """End the current Aliyah tracing session"""
        if sdk_initialized and self.session_id:
            try:
                aliyah_sdk.end_session(self.session_id)
                print(f"✅ Ended Aliyah tracing session: {self.session_id}")
            except Exception as e:
                print(f"Warning: Could not end Aliyah session: {e}")

    def run(self, session_name=None):
        """Run the article generation workflow with tracing"""
        # Start tracing session
        self.start_tracing_session(session_name)

        try:
            pdf_reader = self.agents.get_agents()["pdf_reader"]
            article_writer = self.agents.get_agents()["article_writer"]
            title_creator = self.agents.get_agents()["title_creator"]
            editor = self.agents.get_agents()["editor"]

            tasks = self.tasks.get_tasks()

            crew = Crew(
                agents=[pdf_reader, article_writer, title_creator, editor],
                tasks=tasks,
                process=Process.sequential,
                planning=True,
                verbose=True,
            )

            # Add file_path as part of the input if provided
            inputs = {"user_input": self.inputs}
            if self.file_path:
                inputs["file_path"] = self.file_path

            # Execute the crew workflow (all LLM calls will be automatically traced)
            result = crew.kickoff(inputs=inputs)

            # Log successful completion
            if sdk_initialized:
                try:
                    aliyah_sdk.log_event("article_generation_completed", {
                        "inputs": str(inputs),
                        "result_length": len(str(result)) if result else 0
                    })
                except Exception as e:
                    print(f"Warning: Could not log completion event: {e}")

            return result

        except Exception as e:
            # Log error event
            if sdk_initialized:
                try:
                    aliyah_sdk.log_event("article_generation_error", {
                        "error": str(e),
                        "inputs": str(self.inputs)
                    })
                except Exception as log_e:
                    print(f"Warning: Could not log error event: {log_e}")
            raise e
        finally:
            # Always end the tracing session
            self.end_tracing_session()
