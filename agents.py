from crewai import Agent
from langchain.chat_models import ChatOpenAI
import os


class ArticleAgents:
    def __init__(self, llm, rag_tool):
        # Use environment variable for model configuration
        default_model = os.getenv("DEFAULT_LLM_MODEL", "gpt-3.5-turbo")

        # Initialize LLM if not provided
        if llm is None:
            llm = ChatOpenAI(
                model=default_model,
                temperature=0.7,
                # All LLM calls will be automatically traced by Aliyah SDK
            )

        self.pdf_reader = Agent(
            llm=llm,
            role="PDF Content Extractor",
            goal="Extract and preprocess text from a PDF based on the user input: {user_input}",
            backstory=(
                "You are a specialized AI agent focused on handling and interpreting PDF documents. "
                "Your expertise lies in extracting relevant information based on user queries and "
                "preprocessing text for further analysis. You work efficiently with RAG tools to "
                "find the most relevant content within documents."
            ),
            allow_delegation=False,
            tools=[rag_tool],  # Use the passed rag_tool here
            verbose=True,
            max_iter=3,  # Limit iterations for better tracing
        )

        self.article_writer = Agent(
            llm=llm,
            role="Article Creator",
            goal="Write a concise and engaging article using the contents extracted by the PDF reader agent",
            backstory=(
                "You are an expert content creator with years of experience in transforming raw "
                "information into compelling, well-structured articles. You excel at identifying "
                "key insights, organizing information logically, and writing in an engaging style "
                "that captures and maintains reader interest. Your articles are informative, "
                "accessible, and professionally crafted."
            ),
            allow_delegation=False,
            verbose=True,
            max_iter=3,
        )

        self.title_creator = Agent(
            llm=llm,
            role="Title Generator",
            goal="Generate a compelling and SEO-friendly title for the article",
            backstory=(
                "You are a creative title specialist with a keen understanding of what makes "
                "headlines compelling and clickable. You craft titles that are concise, "
                "attention-grabbing, and accurately represent the article content. Your titles "
                "balance creativity with clarity, ensuring they appeal to the target audience "
                "while maintaining professional standards."
            ),
            allow_delegation=False,
            verbose=True,
            max_iter=2,
        )

        self.editor = Agent(
            llm=llm,
            role="Article Editor",
            goal="Proofread, refine, and structure the article to ensure it is ready for publication.",
            backstory=(
                "You are a meticulous editor with extensive experience in polishing content for "
                "publication. Your responsibilities include reviewing and enhancing article content, "
                "improving readability, ensuring error-free copy, optimizing structure, and aligning "
                "tone with the article's purpose. You have a keen eye for detail and ensure that "
                "every article engages the audience, flows logically, and effectively communicates "
                "key insights. Your editing transforms good content into exceptional, publication-ready material."
            ),
            allow_delegation=False,
            verbose=True,
            max_iter=2,
        )

    def get_agents(self):
        """Return a dictionary of all agents for easy access"""
        return {
            "pdf_reader": self.pdf_reader,
            "article_writer": self.article_writer,
            "title_creator": self.title_creator,
            "editor": self.editor,
        }

    def get_agent_info(self):
        """Return information about all agents for logging/tracing purposes"""
        return {
            "pdf_reader": {
                "role": self.pdf_reader.role,
                "goal": self.pdf_reader.goal,
                "tools_count": len(self.pdf_reader.tools) if self.pdf_reader.tools else 0
            },
            "article_writer": {
                "role": self.article_writer.role,
                "goal": self.article_writer.goal,
                "tools_count": len(self.article_writer.tools) if self.article_writer.tools else 0
            },
            "title_creator": {
                "role": self.title_creator.role,
                "goal": self.title_creator.goal,
                "tools_count": len(self.title_creator.tools) if self.title_creator.tools else 0
            },
            "editor": {
                "role": self.editor.role,
                "goal": self.editor.goal,
                "tools_count": len(self.editor.tools) if self.editor.tools else 0
            }
        }
