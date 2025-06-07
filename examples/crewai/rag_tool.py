# rag_tool.py

from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from crewai_tools import PDFSearchTool
import os
import time

# Define the input schema for the tool
class PDFSearchToolInput(BaseModel):
    pdf_path: str = Field(..., description="Path to the PDF file to search within.")
    query: str = Field(..., description="The search query to find in the PDF.")

class CustomPDFSearchTool(BaseTool):
    name: str = "Custom PDF Search Tool"
    description: str = "Searches within a PDF document for a given query using RAG technology."
    args_schema: Type[BaseModel] = PDFSearchToolInput

    def _run(self, pdf_path: str, query: str) -> str:
        """
        Execute PDF search with enhanced error handling and logging
        """
        start_time = time.time()

        try:
            # Validate inputs
            if not pdf_path or not os.path.exists(pdf_path):
                error_msg = f"PDF file not found at path: {pdf_path}"
                self._log_event("pdf_search_error", {
                    "error": error_msg,
                    "pdf_path": pdf_path,
                    "query": query
                })
                return f"Error: {error_msg}"

            if not query or len(query.strip()) == 0:
                error_msg = "Search query cannot be empty"
                self._log_event("pdf_search_error", {
                    "error": error_msg,
                    "pdf_path": pdf_path,
                    "query": query
                })
                return f"Error: {error_msg}"

            # Log search initiation
            self._log_event("pdf_search_started", {
                "pdf_path": pdf_path,
                "query": query,
                "query_length": len(query)
            })

            # Initialize the PDFSearchTool with the provided PDF path
            rag_tool = PDFSearchTool(
                pdf=pdf_path,
                config=dict(
                    llm=dict(
                        provider="groq",  # Using Groq for fast inference
                        config=dict(
                            model="mixtral-8x7b-32768",
                            temperature=0.5,
                        ),
                    ),
                    embedder=dict(
                        provider="google",  # Using Google for embeddings
                        config=dict(
                            model="models/embedding-001",
                        ),
                    ),
                )
            )

            # Perform the search with the provided query
            result = rag_tool.run(query)

            # Calculate processing time
            processing_time = time.time() - start_time

            # Log successful completion
            self._log_event("pdf_search_completed", {
                "pdf_path": pdf_path,
                "query": query,
                "result_length": len(str(result)) if result else 0,
                "processing_time_seconds": round(processing_time, 2),
                "success": True
            })

            return result

        except Exception as e:
            # Calculate processing time even for errors
            processing_time = time.time() - start_time
            error_msg = str(e)

            # Log error details
            self._log_event("pdf_search_error", {
                "pdf_path": pdf_path,
                "query": query,
                "error": error_msg,
                "processing_time_seconds": round(processing_time, 2),
                "success": False
            })

            # Return a user-friendly error message
            return f"Error during PDF search: {error_msg}. Please check your PDF file and try again."

    def _log_event(self, event_name: str, event_data: dict):
        """
        Log events to Aliyah SDK if available, otherwise print to console
        """
        try:
            import aliyah_sdk
            aliyah_sdk.log_event(event_name, event_data)
        except ImportError:
            # Aliyah SDK not available, log to console
            print(f"[RAG Tool] {event_name}: {event_data}")
        except Exception as e:
            # SDK available but logging failed
            print(f"[RAG Tool] Failed to log event {event_name}: {e}")
            print(f"[RAG Tool] Event data: {event_data}")

    def get_tool_info(self) -> dict:
        """
        Return tool information for monitoring and debugging
        """
        return {
            "name": self.name,
            "description": self.description,
            "llm_provider": "groq",
            "llm_model": "mixtral-8x7b-32768",
            "embedder_provider": "google",
            "embedder_model": "models/embedding-001"
        }
