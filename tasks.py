from crewai import Task

class ArticleTasks:
    def __init__(self, pdf_reader, article_writer, title_creator, editor):

        self.pdf_reading_task = Task(
            description=(
                "Read and extract relevant content from the provided PDF file based on the user's query: {user_input}. "
                "Use the RAG tool to search through the PDF and identify the most relevant sections. "
                "Focus on extracting key information, main concepts, and supporting details that directly relate to the user's query. "
                "Ensure the extracted content is comprehensive yet focused, avoiding irrelevant information."
            ),
            agent=pdf_reader,
            expected_output=(
                "A well-structured summary of extracted and preprocessed text from the PDF that is directly relevant to the user's query. "
                "Include key concepts, main points, and supporting details in a logical order."
            ),
        )

        self.task_article_writing = Task(
            description=(
                "Create a comprehensive and engaging article with 8-10 well-developed paragraphs based on the extracted PDF content. "
                "Structure the article with a clear introduction, body paragraphs that explore different aspects of the topic, "
                "and a conclusion that ties everything together. Each paragraph should be substantive (4-6 sentences) and "
                "flow logically to the next. Use clear, engaging language that makes complex topics accessible to readers. "
                "Ensure the article is informative, well-researched, and provides value to the reader."
            ),
            agent=article_writer,
            expected_output=(
                "A well-structured article with 8-10 paragraphs, each containing 4-6 sentences. The article should have: "
                "1) An engaging introduction that sets the context, "
                "2) Body paragraphs that explore key points from the PDF content, "
                "3) A strong conclusion that summarizes insights and implications. "
                "The writing should be clear, professional, and engaging."
            ),
        )

        self.task_title_generation = Task(
            description=(
                "Generate a compelling, informative, and SEO-friendly title for the article. "
                "The title should be 5-7 words long, capture the essence of the article content, "
                "and be engaging enough to attract readers while accurately representing the main topic. "
                "Consider using powerful action words, specific keywords, and ensure the title is "
                "both descriptive and intriguing. Avoid clickbait while maintaining appeal."
            ),
            agent=title_creator,
            expected_output=(
                "A single, compelling title of 5-7 words that accurately represents the article content "
                "and is optimized for both reader engagement and search visibility."
            ),
        )

        self.edit_task = Task(
            description=(
                "Proofread, refine, and structure the article to ensure it meets publication standards. "
                "Review the content for grammatical errors, clarity, flow, and coherence. "
                "Enhance the structure by ensuring smooth transitions between paragraphs, "
                "improving sentence variety, and optimizing readability. Verify that each section "
                "has approximately 5 well-developed paragraphs and that the overall article maintains "
                "a consistent tone and style. Polish the language to be professional yet accessible, "
                "and ensure all key points from the PDF are effectively communicated."
            ),
            agent=editor,
            expected_output=(
                "A finalized, publication-ready article with polished prose, perfect grammar, "
                "and excellent structure. The article should be divided into clear sections, "
                "each containing approximately 5 well-crafted paragraphs. The content should "
                "flow seamlessly from introduction to conclusion, with engaging language that "
                "effectively communicates the key insights from the source material."
            ),
        )

    def get_tasks(self):
        """Return all tasks in execution order"""
        return [
            self.pdf_reading_task,
            self.task_article_writing,
            self.task_title_generation,
            self.edit_task
        ]

    def get_task_info(self):
        """Return task information for monitoring and debugging"""
        return {
            "pdf_reading_task": {
                "agent_role": self.pdf_reading_task.agent.role,
                "description_length": len(self.pdf_reading_task.description),
                "has_tools": len(self.pdf_reading_task.agent.tools) > 0 if self.pdf_reading_task.agent.tools else False
            },
            "article_writing_task": {
                "agent_role": self.task_article_writing.agent.role,
                "description_length": len(self.task_article_writing.description),
                "expected_paragraphs": "8-10"
            },
            "title_generation_task": {
                "agent_role": self.task_title_generation.agent.role,
                "description_length": len(self.task_title_generation.description),
                "expected_word_count": "5-7"
            },
            "editing_task": {
                "agent_role": self.edit_task.agent.role,
                "description_length": len(self.edit_task.description),
                "expected_sections": "5 paragraphs per section"
            }
        }
