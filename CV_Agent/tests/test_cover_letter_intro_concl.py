import sys
import os
import pathlib
from dotenv import load_dotenv

# Compute project root and fix imports
script_dir = pathlib.Path(__file__).parent  # tests/
project_root = script_dir.parent.parent  # root
sys.path.append(str(project_root / "CV_Agent"))  # Add CV_Agent/ to path for imports

# Now import after path is fixed
from core.ingestion import parse_text, parse_pdf, parse_master_resume
from core.cover_letter_agent import deepseek, invoke_llm_with_rate_limiting, limiter, CoverLetterIntro, CoverLetterConclusion

from typing import Dict

load_dotenv()

# Paths relative to project root
JOB_PATH = str(project_root / "jobs" / "Dayforce (Ceridian)_96417" / "AI Transformation Engineer Intern 4 or 8 months (Fall 2025) - Req #22001_job_details.txt")
RESUME_PATH = str(project_root / "CV_Agent" / "Input-Documents" / "Master_Resume.pdf")

# Ingest files
def ingest_files() -> Dict[str, any]:
    with open(JOB_PATH, 'rb') as f:
        job_bytes = f.read()
    job_text = parse_text(job_bytes)
    
    with open(RESUME_PATH, 'rb') as f:
        resume_bytes = f.read()
    resume_text = parse_pdf(resume_bytes)
    structured_resume = parse_master_resume(resume_text)
    
    return {
        "job_description_text": job_text,
        "master_resume_structured": structured_resume
    }

# Mock GraphState type
class GraphState(Dict[str, any]):
    pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_cover_letter_intro_concl.py [intro|both]")
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    if mode not in ['intro', 'both']:
        print("Invalid mode. Choose 'intro' or 'both'.")
        sys.exit(1)
    
    state_data = ingest_files()
    state = GraphState(state_data)
    
    output_file = "test_output.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        if mode in ['intro', 'both']:
            # Replicate intro prompt
            jd_text = state["job_description_text"]
            resume_context = state["master_resume_structured"]['full_text']
            intro_prompt = f"""
                You are an expert cover letter writer. Generate a compelling introduction for a cover letter based on the job description and candidate's resume.

                The introduction should:
                1. Start with a creative, thematic hook that connects to the company's mission or values in an original way 
                2. Use metaphors or creative framings that feel natural and smooth, not forced or overly direct
                3. Weave in specific technical projects naturally without being too explicit about connections (avoid phrases like "much like", "mirroring", "similar to")
                4. Include enough personal details and technical experience to give substance
                5. Show personality and genuine enthusiasm through storytelling, not generic excitement phrases
                6. Be 4-5 sentences maximum with engaging, flowing language
                7. Do not use em dashes, hyphens for clauses, or corporate buzzwords like "synergy", "leverage", "utilize"
                8. Use non-technical language unless the technical term appears in the job description - if you must use technical terms, add brief descriptive context
                9. Avoid being too direct or sales-y in the opening - draw them in first, then connect

                Technical language guidelines:
                - Only use technical terms that appear in the job description
                - For other technical terms, use descriptive phrases (e.g., "AI agent framework" instead of "LangChain")
                - Keep explanations brief and accessible to non-technical readers

                Voice and tone:
                - Natural, smooth connections rather than forced parallels
                - Genuine enthusiasm through storytelling, not generic excitement
                - Professional but personable, avoiding overly poetic or preachy language
                - Let connections emerge organically rather than stating them explicitly
                - Creative but authentic voice that reflects genuine interest

                Avoid these overused openings:
                - "In a world where..."
                - "Amidst the..."
                - "As a [student/developer]..."
                - "I was excited to discover..."
                - "Imagine if..."
                - "In today's digital landscape..."

                Avoid these forced connection patterns:
                - "much like [company]..."
                - "mirroring your..."
                - "similar to how [company]..."
                - Em dashes for clauses
                - Overly direct comparisons
                - Corporate buzzwords (synergy, leverage, utilize, streamline)

                Focus on:
                - Finding unique angles related to the company's industry/mission/values
                - Original metaphors or perspectives that haven't been overused
                - Specific technical details woven naturally into the narrative
                - Personality that makes the reader want to learn more about you

                JOB DESCRIPTION: {jd_text}

                CANDIDATE'S RESUME: {resume_context}

                Output in json format with a single key 'introduction' containing the generated text.
            """
            
            f.write("=== INTRO PROMPT ===\n")
            f.write(intro_prompt + "\n\n")
            
            try:
                structured_llm = deepseek.with_structured_output(CoverLetterIntro, method="json_mode")
                intro_response = invoke_llm_with_rate_limiting(structured_llm, intro_prompt)
                intro_text = intro_response.introduction
                f.write("=== INTRO RESULT ===\n")
                f.write(intro_text + "\n\n")
            except Exception as e:
                f.write("=== INTRO ERROR ===\n")
                f.write(f"Failed to generate intro: {str(e)}\n\n")
                intro_text = "[INTRO GENERATION FAILED]"
        
        if mode == 'both':
            # Replicate conclusion prompt
            concl_prompt = f"""
                You are an expert cover letter writer. Generate a compelling conclusion for a cover letter that maintains the creative voice and theme established in the introduction.

                The conclusion should:
                1. Echo the theme/metaphor from the introduction subtly and naturally, not through explicit "just as" or "much like" constructions
                2. Show confidence and readiness to contribute, not just eagerness to learn
                3. Position the interview as a natural next step using invitational language, not presumptuous or demanding tone
                4. Reference the role naturally without over-specifying location details or repeating job title verbatim
                5. Be 3-4 sentences maximum for impact and flow
                6. Maintain the same creative, thoughtful voice as the introduction
                7. Do not use em dashes, hyphens for clauses, or corporate buzzwords

                Voice and tone:
                - Same personality and creativity as the introduction
                - Confident but respectful, not presumptuous or demanding
                - Natural flow that feels like a logical conclusion
                - Professional but personable
                - Invitational rather than assumptive about next steps

                Technical language guidelines:
                - Only use technical terms that appear in the job description
                - For other technical concepts, use descriptive phrases accessible to non-technical readers
                - Keep explanations brief and natural

                Avoid these forced callback patterns:
                - "Just as [company/intro theme]..."
                - "Much like..."
                - "Similar to how..."
                - "In the same spirit of..."
                - Direct equation statements like "aligns with your vision"

                Avoid these presumptuous phrases:
                - "Let's explore..."
                - "I'm confident that a conversation...is a natural next step"
                - "I believe discussing...is a natural next step"
                - Over-specific location references 

                Interview reference guidelines:
                - Use invitational language: "I would welcome the opportunity to discuss..."
                - Make it feel natural without being demanding
                - Reference the mission/impact rather than specific logistics
                - Be confident but not presumptuous

                Focus on:
                - Organic theme integration that feels natural
                - Confident readiness to contribute
                - Respectful invitation to continue the conversation
                - Natural flow that doesn't over-specify details

                INTRODUCTION: {intro_text}
                JOB DESCRIPTION: {jd_text}
                CANDIDATE'S RESUME: {resume_context}

                Output in json format with a single key 'conclusion' containing the generated text.
            """
            
            f.write("=== CONCLUSION PROMPT ===\n")
            f.write(concl_prompt + "\n\n")
            
            try:
                structured_llm = deepseek.with_structured_output(CoverLetterConclusion, method="json_mode")
                concl_response = invoke_llm_with_rate_limiting(structured_llm, concl_prompt)
                concl_text = concl_response.conclusion
                f.write("=== CONCLUSION RESULT ===\n")
                f.write(concl_text + "\n\n")
            except Exception as e:
                f.write("=== CONCLUSION ERROR ===\n")
                f.write(f"Failed to generate conclusion: {str(e)}\n\n")
    
    print(f"Output written to {output_file}") 