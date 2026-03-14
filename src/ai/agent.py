import os
import logging
from typing import Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from scraper.models import AgendaItem

load_dotenv()

logger = logging.getLogger(__name__)

class CivicAIAgent:
    def __init__(self, model_name: str = None):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = model_name or os.getenv("OPENROUTER_MODEL", "openrouter/hunter-alpha")
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")

        self.llm = ChatOpenAI(
            model=self.model,
            openai_api_key=self.api_key,
            openai_api_base=self.base_url,
            default_headers={
                "HTTP-Referer": "https://github.com/Caleb-Gawthroupe/minutes",
                "X-Title": "CivicClaw Agent"
            }
        )

    async def summarize_item_async(self, item: AgendaItem) -> AgendaItem:
        """Uses AI to generate a concise summary and a viral social media post for an agenda item."""
        logger.info(f"Generating AI intelligence for item {item.item_number}: {item.title}")
        
        # Prepare context from summary, recommendations, and parsed PDF text
        context = f"Title: {item.title}\n\n"
        if item.summary:
            context += f"Official Summary: {item.summary}\n\n"
        if item.recommendations:
            context += f"Recommendations: {item.recommendations}\n\n"
        if item.parsed_pdf_text:
            # Simple truncation if too long for the model context
            context += f"Staff Report Excerpt: {item.parsed_pdf_text[:5000]}"

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are CivicClaw, an agentic civic tool. Your goal is to make municipal government updates engaging, punchy, and fact-dense.
            
            Given the agenda item details from Toronto City Council:
            1. **Plain-Language Summary**: 2-3 sentences max. Focus on the direct impact to people's lives (money, space, rules).
            2. **Viral Social Post**: Keep it SHORT and FACT-DENSE. 
               - MUST mention the Item ID (e.g., EX29.14).
               - Prioritize specific facts from the recommendations or staff reports.
               - Use 2-3 emojis max.
               - Include a clear CTA like 'DM [KEYWORD] + postal code'.
            
            Be concise. No fluff. No generic intro text.
            
            Format your response exactly as:
            SUMMARY: [Your summary here]
            SOCIAL: [Your social post here]
            """),
            ("user", "{context}")
        ])

        try:
            chain = prompt | self.llm
            response = await chain.ainvoke({"context": context})
            content = response.content

            # Parse content
            if "SUMMARY:" in content and "SOCIAL:" in content:
                parts = content.split("SOCIAL:")
                item.ai_summary = parts[0].replace("SUMMARY:", "").strip()
                item.social_post = parts[1].strip()
            else:
                logger.warning(f"AI response for {item.item_number} was not in expected format.")
                item.ai_summary = content[:200]
                
        except Exception as e:
            logger.error(f"AI intelligence generation failed for {item.item_number}: {e}")
        
        return item

    async def generate_aggregate_post_async(self, meeting: dict, bylaw: dict, project: dict) -> str:
        """Synthesizes three updates into a single social media post."""
        logger.info("Generating aggregate AI social post...")
        
        context = f"""
        LATEST MEETING: {meeting.get('title')} on {meeting.get('post_date')}
        LATEST BYLAW: {bylaw.get('title')} ({bylaw.get('source_url')})
        LATEST PROJECT/AGENDA: {project.get('title')} (Item {project.get('item_number')})
        Summary: {project.get('summary')}
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are CivicClaw. Create ONE viral, fact-dense Instagram post that summarizes these three Toronto updates.
            
            Guidelines:
            - Keep it under 2000 characters.
            - Use a punchy headline.
            - Use bullet points for the 3 items.
            - Focus on the impact for Toronto residents.
            - Include 2-3 emojis.
            - MUST include a CTA: 'DM MINUTES + your postal code for deeper context.'
            - No fluff, no 'Here are your updates'. Start with the news.
            """),
            ("user", "{context}")
        ])

        try:
            chain = prompt | self.llm
            response = await chain.ainvoke({"context": context})
            return response.content.strip()
        except Exception as e:
            logger.error(f"Aggregate AI generation failed: {e}")
            return f"Toronto Updates:\n- Meeting: {meeting.get('title')}\n- Bylaw: {bylaw.get('title')}\n- Project: {project.get('title')}\nDM MINUTES for more."

    def generate_aggregate_post(self, meeting: dict, bylaw: dict, project: dict) -> str:
        import asyncio
        return asyncio.run(self.generate_aggregate_post_async(meeting, bylaw, project))

    def summarize_item(self, item: AgendaItem) -> AgendaItem:
        import asyncio
        return asyncio.run(self.summarize_item_async(item))

if __name__ == "__main__":
    # Test stub
    agent = CivicAIAgent()
    test_item = AgendaItem(
        item_number="TEST.101",
        title="Increase in Residential Property Tax",
        summary="City staff recommend a 9.5% increase in property taxes to fund housing initiatives.",
        recommendations="1. Increase tax rates. 2. Fund Housing Secretariat."
    )
    processed = agent.summarize_item(test_item)
    print(f"AI SUMMARY: {processed.ai_summary}")
    print(f"SOCIAL POST: {processed.social_post}")
