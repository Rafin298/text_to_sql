import os
import google.generativeai as genai
from text2sql.services.schema_helper import get_schema_context

# Configure Gemini API key
API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError(
        "Missing GEMINI_API_KEY or GOOGLE_API_KEY in environment variables."
    )

genai.configure(api_key=API_KEY)


class GeminiWrapper:
    """
    A secure wrapper for calling Gemini to generate SQL queries
    from natural language input.

    Example:
        gem = GeminiWrapper()
        sql = gem.nl_to_sql("show total sales by month")
    """

    def __init__(self, model: str = "gemini-2.5-flash"):
        self.model = model
        self.model_client = genai.GenerativeModel(model)

    def nl_to_sql(self, nl_query: str, schema_hint: str = "") -> str:
        """
        Convert a natural language question into a single safe SQL SELECT query.
        Enforces instructions through prompt design.
        """
        schema_hint = get_schema_context() 
        # system_prompt = (
        #     "You are an expert SQL generator. "
        #     "Generate ONE valid PostgreSQL SELECT query only. "
        #     "Do not include any text, explanation, or code formatting. "
        #     "No INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, or transaction statements. "
        #     "If the query cannot be answered, return only this comment: "
        #     "-- NO_SQL_POSSIBLE"
        # )

        # prompt = (
        #     f"{system_prompt}\n\n"
        #     f"Schema (if available):\n{schema_hint}\n\n"
        #     f"User request:\n{nl_query}\n\n"
        #     "Return only the SQL query, nothing else."
        # )
        
        system_prompt = (
            "You are an expert SQL generator for PostgreSQL. "
            "Always use double quotes for table and column names exactly as in the schema. "
            "Only produce a single SELECT statement, no semicolons and make the sql in one line. "
            "Return only SQL, no explanations.\n\n"
            f"Database schema:\n{schema_hint}\n\n"
            f"User question:\n{nl_query}\n\n"
        )

        # try:
        #     response = self.model_client.generate_content(prompt)

        #     # Try to extract the generated SQL safely
        #     text = getattr(response, "text", None)
        #     if not text and hasattr(response, "candidates"):
        #         # Fallback to the first candidate
        #         try:
        #             text = response.candidates[0].content.parts[0].text
        #         except Exception:
        #             text = str(response)
        #     if not text:
        #         raise RuntimeError("Empty response from Gemini model.")

        #     # Clean any accidental code fences or Markdown
        #     text = text.strip()
        #     if text.startswith("```"):
        #         text = text.strip("`").replace("sql", "").strip()

        #     print(f"Gemini raw response: {text}")  # for debugging
        #     return text

        # except Exception as e:
        #     raise RuntimeError(f"Gemini API error: {e}")
        
        response = self.model_client.generate_content(system_prompt)
        sql = getattr(response, "text", "").strip()

        if sql.startswith("```"):
            sql = sql.strip("`").replace("sql", "").strip()

        print(f"Gemini raw response: {sql}")  # for debugging
        return sql