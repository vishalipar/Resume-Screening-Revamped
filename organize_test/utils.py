from groq import Groq
from django.conf import settings
import re
import json

client = Groq(api_key=settings.GROQ_API_KEY)

def generate_questions(paragraph, q_type, count, difficulty, mcq_options=None):
    
    prompt = f"""
    Generate {count} {difficulty} level questions from the following paragraph.
    Return ONLY valid JSON. Do not add explanation or markdown.
    Paragraph:
    {paragraph}

    Question Type: {q_type}
    """

    if q_type in ["MCQ", "MCQ Multiple Correct"]:
        prompt += f"\nEach question should have {mcq_options} options."

        prompt += """
        Return JSON like:
        [
          {
            "question": "...",
            "options": ["...", "..."],
            "answer": "..."
          }
        ]
        """
    else:
      prompt += """
      Return JSON like:
      [
        {
          "question": "...",
          "answer": "..."
        }
      ]
      """

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )
    content = response.choices[0].message.content

    # extract JSON part
    json_text = re.search(r'\[.*\]', content, re.DOTALL).group()

    return json.loads(json_text)