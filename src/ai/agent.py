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

    async def generate_aggregate_post_async(self, meeting: dict, bylaw: dict, project: dict) -> dict:
        """Synthesizes three updates into a structured payload for image-centric posting."""
        logger.info("Generating structured high-impact AI content...")
        
        context = f"""
        LATEST MEETING: {meeting.get('title')} on {meeting.get('post_date')}
        LATEST BYLAW: {bylaw.get('title')} ({bylaw.get('source_url')})
        LATEST PROJECT/AGENDA: {project.get('title')} (Item {project.get('item_number')})
        Summary: {project.get('summary')}
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are CivicClaw, Toronto's premier civic engagement agent.
            We are moving to an IMAGE-CENTRIC posting style. 
            
            Your task is to produce a JSON-like payload with two specific parts:
            1. **"caption"**: A very short (max 200 chars), punchy hook for the Instagram caption. It should entice people to look at the image. Use 1 emoji. 
               Example: "URGENT: Your rent might be changing. 🏠 Details on the card below! #TorontoMinutes"
            
            2. **"card_title"**: A short, bold headline for the graphic (max 30 chars).
            
            3. **"card_body"**: A list of the 3 most important, human-centric facts from the provided context. 
               Each fact must be clear, plain-language, and explain the DIRECT IMPACT on residents.
               Keep each bullet point under 120 characters to ensure it fits on the card.
            
            4. **"cta"**: A specific call to action related to the main item (e.g., "DM FIGHTSLUMLORD to email your councillor").
            
            5. **"img_keyword"**: A high-relevance search query for a background image. **CRITICAL**: Never provide a name alone (e.g., use "Mayor Olivia Chow Toronto City Hall" instead of "Olivia Chow" to avoid unrelated results like animals). Favor "potholes", "Toronto streetcar", "City Hall council chamber", or "urban housing" if the news is about infrastructure.
            
            Provide your response exactly as:
            CAPTION: [Your hook here]
            TITLE: [Your card title here]
            BODY: [Bullet 1]|[Bullet 2]|[Bullet 3]
            CTA: [Your cta here]
            IMG: [Your image keyword here]
            """),
            ("user", "{context}")
        ])

        try:
            chain = prompt | self.llm
            response = await chain.ainvoke({"context": context})
            content = response.content.strip()
            
            # Simple manual parsing
            lines = content.split('\n')
            result = {}
            for line in lines:
                if line.startswith("CAPTION:"): result['caption'] = line.replace("CAPTION:", "").strip()
                elif line.startswith("TITLE:"): result['card_title'] = line.replace("TITLE:", "").strip()
                elif line.startswith("BODY:"): result['card_body'] = line.replace("BODY:", "").strip().split('|')
                elif line.startswith("CTA:"): result['cta'] = line.replace("CTA:", "").strip()
                elif line.startswith("IMG:"): result['img_keyword'] = line.replace("IMG:", "").strip()
            
            return result
        except Exception as e:
            logger.error(f"Structured AI generation failed: {e}")
            return {
                "caption": "New Toronto updates just dropped. Check the card! 🏙️",
                "card_title": "CIVIC UPDATE",
                "card_body": [f"Meeting: {meeting.get('title')}", f"Bylaw: {bylaw.get('title')}", f"Project: {project.get('title')}"],
                "cta": "DM MINUTES for more."
            }
    async def generate_deep_dive_post_async(
        self,
        topic_item: dict,
        historical_context: list[dict],
    ) -> dict:
        """
        RAG-enhanced post generation. Meeting-first: the topic_item is the star.
        historical_context provides supplementary depth from the vector store.
        """
        logger.info(f"Generating RAG-enhanced deep-dive post for: {topic_item.get('title', 'Unknown')}")

        # Build the primary context from the meeting item
        primary = f"""
=== TODAY'S KEY AGENDA ITEM ===
Item Number: {topic_item.get('item_number', 'N/A')}
Title: {topic_item.get('title', 'N/A')}
Status: {topic_item.get('status', 'N/A')}
Summary: {topic_item.get('summary', 'No summary available.')}
Recommendations: {topic_item.get('recommendations', 'None provided.')}
"""
        # Add parsed PDF text if available (truncated for context window)
        pdf_text = topic_item.get('parsed_pdf_text', '')
        if pdf_text:
            primary += f"\nStaff Report Excerpt:\n{pdf_text[:4000]}\n"

        # Build the historical context section
        history = ""
        if historical_context:
            history = "\n=== HISTORICAL CONTEXT (from past meetings/bylaws) ===\n"
            for i, chunk in enumerate(historical_context[:5]):
                source = chunk.get('metadata', {}).get('source', 'unknown')
                doc_type = chunk.get('metadata', {}).get('doc_type', 'document')
                history += f"\n[Past {doc_type} - {source}]:\n{chunk['text'][:800]}\n"

        full_context = primary + history

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are CivicClaw, Toronto's civic intelligence agent. You write clear, punchy Instagram posts about council decisions.

**NARRATIVE STRUCTURE** (this is critical):
Your 3 bullet points must tell ONE coherent story, like a news brief:
- Bullet 1: "Council [decided/proposed] X" — state the decision clearly and simply.
- Bullet 2: "This means Y for residents" — explain the DIRECT, tangible consequence. Be specific (dollar amounts, timelines, who is affected).
- Bullet 3: "What happens next" — e.g. when it takes effect, what residents can do, or who to contact.

**CONTRADICTIONS** (only if the HISTORICAL CONTEXT section below genuinely contains one):
- If the historical context shows a past vote, bylaw, or statement that DIRECTLY CONTRADICTS today's item, replace Bullet 3 with the contradiction. Be specific: cite the past decision. Example: "In 2024, council rejected this same measure 18-7. Now they've reversed course."
- If there is NO clear contradiction in the historical context, do NOT invent one. Just use Bullet 3 for "what happens next."

**TONE**: Write like a smart friend explaining the news. Plain language. No jargon. No filler.

**FORMAT**:
- "caption": Max 200 chars. Punchy hook with 1 emoji.
- "card_title": Max 30 chars. Bold headline summarizing the decision.
- "card_body": Exactly 3 bullets, each under 120 chars. Must flow as one story.
- "cta": Specific call to action (e.g., "DM HOUSING for the full report").
- "img_keyword": Image search query. NEVER just a name. Add "Toronto" + scene description. Favor infrastructure/civic imagery.

Respond exactly as:
CAPTION: [hook]
TITLE: [headline]
BODY: [Bullet 1]|[Bullet 2]|[Bullet 3]
CTA: [cta]
IMG: [image keyword]
"""),
            ("user", "{context}")
        ])

        try:
            chain = prompt | self.llm
            response = await chain.ainvoke({"context": full_context})
            content = response.content.strip()

            # Parse the structured response
            lines = content.split('\n')
            result = {}
            for line in lines:
                if line.startswith("CAPTION:"): result['caption'] = line.replace("CAPTION:", "").strip()
                elif line.startswith("TITLE:"): result['card_title'] = line.replace("TITLE:", "").strip()
                elif line.startswith("BODY:"): result['card_body'] = line.replace("BODY:", "").strip().split('|')
                elif line.startswith("CTA:"): result['cta'] = line.replace("CTA:", "").strip()
                elif line.startswith("IMG:"): result['img_keyword'] = line.replace("IMG:", "").strip()

            return result
        except Exception as e:
            logger.error(f"RAG-enhanced AI generation failed: {e}")
            return {
                "caption": f"Breaking: {topic_item.get('title', 'Council Update')} 🏙️",
                "card_title": "CIVIC UPDATE",
                "card_body": [
                    topic_item.get('title', 'Council decision pending.'),
                    topic_item.get('summary', 'Details in the staff report.')[:120] if topic_item.get('summary') else 'Check the full report for details.',
                    "More context at toronto.ca/council"
                ],
                "cta": "DM MINUTES for the full report.",
                "img_keyword": "Toronto City Hall council chamber"
            }

    # --- Sync wrappers ---

    def generate_aggregate_post(self, meeting: dict, bylaw: dict, project: dict) -> str:
        import asyncio
        return asyncio.run(self.generate_aggregate_post_async(meeting, bylaw, project))

    def generate_deep_dive_post(self, topic_item: dict, historical_context: list[dict]) -> dict:
        import asyncio
        return asyncio.run(self.generate_deep_dive_post_async(topic_item, historical_context))

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
