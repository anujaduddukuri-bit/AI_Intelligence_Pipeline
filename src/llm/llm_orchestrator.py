import os
import json
import time
import random

from dotenv import load_dotenv
from google import genai
from groq import Groq
from openai import OpenAI


load_dotenv()


# ============================================================
# API KEYS
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")


# ============================================================
# CLIENTS
# ============================================================

gemini_client = None
groq_client = None
deepseek_client = None


if GEMINI_API_KEY:
    gemini_client = genai.Client(
        api_key=GEMINI_API_KEY
    )


if GROQ_API_KEY:
    groq_client = Groq(
        api_key=GROQ_API_KEY
    )


if DEEPSEEK_API_KEY:
    deepseek_client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )


# ============================================================
# PROVIDER STATUS
# ============================================================

# These flags prevent repeatedly calling providers
# that are already known to be unavailable.

gemini_available = True
groq_available = True
deepseek_available = True


# ============================================================
# STRICT STARTUP EXTRACTION PROMPT
# ============================================================

def create_prompt(text):

    prompt = f"""
You are a strict startup data extraction system.

Determine whether this webpage contains information about an
actual startup/company.

IMPORTANT RULES:

1. Use ONLY information explicitly present in the webpage text.
2. Never guess or invent information.
3. A website title, domain name, or company name alone is NOT
   enough evidence.
4. The webpage must contain meaningful information about the
   company/startup.
5. Documentation pages, blogs, unrelated pages, directories,
   examples, or non-company pages must be rejected.
6. If employee count is unavailable, use null.
7. If the entity is not a startup/company, entityName must be null.
8. Return ONLY valid JSON.
9. Do not add explanations.

Webpage text:

{text[:5000]}

Return exactly:

{{
    "isStartup": false,
    "entityName": null,
    "employeeCount": null
}}
"""

    return prompt


# ============================================================
# CLEAN JSON RESPONSE
# ============================================================

def clean_json_response(result):

    result = result.strip()

    if result.startswith("```json"):
        result = result[7:]

    elif result.startswith("```"):
        result = result[3:]

    if result.endswith("```"):
        result = result[:-3]

    result = result.strip()

    return json.loads(result)


# ============================================================
# VALIDATE RESULT
# ============================================================

def validate_result(data):

    if not isinstance(data, dict):
        return False

    required_fields = [
        "isStartup",
        "entityName",
        "employeeCount"
    ]

    for field in required_fields:

        if field not in data:
            return False

    if not isinstance(data["isStartup"], bool):
        return False

    if data["isStartup"]:

        if not data["entityName"]:
            return False

        if data["employeeCount"] is not None:

            if not isinstance(
                data["employeeCount"],
                int
            ):
                return False

            if data["employeeCount"] < 0:
                return False

    else:

        if data["entityName"] is not None:
            return False

    return True


# ============================================================
# GEMINI
# ============================================================

def call_gemini(prompt):

    if not gemini_client:
        raise Exception(
            "Gemini API key not configured"
        )

    interaction = gemini_client.interactions.create(
        model="gemini-3.6-flash",
        input=prompt
    )

    return interaction.output_text


# ============================================================
# GROQ
# ============================================================

def call_groq(prompt):

    if not groq_client:
        raise Exception(
            "Groq API key not configured"
        )

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=300
    )

    return response.choices[0].message.content


# ============================================================
# DEEPSEEK
# ============================================================

def call_deepseek(prompt):

    if not deepseek_client:
        raise Exception(
            "DeepSeek API key not configured"
        )

    response = deepseek_client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=300
    )

    return response.choices[0].message.content


# ============================================================
# ERROR CLASSIFICATION
# ============================================================

def classify_error(error):

    error_text = str(error).lower()

    # --------------------------------------------------------
    # Daily token quota
    # --------------------------------------------------------

    if "tokens per day" in error_text:
        return "daily_quota"

    if "tpd" in error_text:
        return "daily_quota"

    # --------------------------------------------------------
    # Permanent balance / quota problems
    # --------------------------------------------------------

    if "402" in error_text:
        return "permanent"

    if "insufficient balance" in error_text:
        return "permanent"

    if (
        "quota" in error_text
        and "exceeded" in error_text
    ):
        return "permanent"

    # --------------------------------------------------------
    # Temporary rate limits
    # --------------------------------------------------------

    if "429" in error_text:
        return "rate_limit"

    if "rate limit" in error_text:
        return "rate_limit"

    # --------------------------------------------------------
    # Other errors
    # --------------------------------------------------------

    return "other"


# ============================================================
# RETRY WITH BACKOFF
# ============================================================

def retry_with_backoff(
    function,
    prompt,
    provider,
    max_retries=2
):

    for attempt in range(max_retries + 1):

        try:

            print(
                f"[{provider}] Attempt "
                f"{attempt + 1}/{max_retries + 1}"
            )

            return function(prompt)

        except Exception as error:

            error_type = classify_error(error)

            error_text = str(error)

            print(
                f"[{provider}] Error: "
                f"{error_text[:250]}"
            )

            # ------------------------------------------------
            # DAILY QUOTA
            # ------------------------------------------------

            if error_type == "daily_quota":

                print(
                    f"[{provider}] Daily token quota "
                    f"exhausted."
                )

                raise error

            # ------------------------------------------------
            # PERMANENT FAILURE
            # ------------------------------------------------

            if error_type == "permanent":

                print(
                    f"[{provider}] Permanent failure. "
                    f"Skipping provider."
                )

                raise error

            # ------------------------------------------------
            # OTHER ERROR
            # ------------------------------------------------

            if error_type != "rate_limit":

                raise error

            # ------------------------------------------------
            # MAXIMUM RETRIES
            # ------------------------------------------------

            if attempt == max_retries:

                print(
                    f"[{provider}] Maximum retries reached."
                )

                raise error

            # ------------------------------------------------
            # EXPONENTIAL BACKOFF + JITTER
            # ------------------------------------------------

            delay = (
                5 * (2 ** attempt)
                + random.uniform(0, 2)
            )

            print(
                f"[{provider}] Rate limited. "
                f"Waiting {delay:.2f} seconds..."
            )

            time.sleep(delay)


# ============================================================
# MAIN ORCHESTRATOR
# ============================================================

def extract_startup(text, source_url):

    global gemini_available
    global groq_available
    global deepseek_available

    prompt = create_prompt(text)

    # --------------------------------------------------------
    # Provider list
    # --------------------------------------------------------

    providers = []

    if (
        gemini_available
        and gemini_client
    ):

        providers.append(
            ("Gemini", call_gemini)
        )

    if (
        groq_available
        and groq_client
    ):

        providers.append(
            ("Groq", call_groq)
        )

    if (
        deepseek_available
        and deepseek_client
    ):

        providers.append(
            ("DeepSeek", call_deepseek)
        )

    # --------------------------------------------------------
    # No providers available
    # --------------------------------------------------------

    if not providers:

        print(
            "[SYSTEM] No LLM providers are "
            "currently available."
        )

        return {
            "isStartup": False,
            "entityName": None,
            "employeeCount": None,
            "sourceUrl": source_url,
            "error": "All LLM providers unavailable"
        }

    # --------------------------------------------------------
    # Try providers
    # --------------------------------------------------------

    for provider_name, provider_function in providers:

        try:

            print(
                f"\nTrying LLM provider: "
                f"{provider_name}"
            )

            result = retry_with_backoff(
                provider_function,
                prompt,
                provider_name
            )

            data = clean_json_response(result)

            if not validate_result(data):

                raise ValueError(
                    f"{provider_name} returned "
                    f"invalid JSON structure"
                )

            data["sourceUrl"] = source_url

            print(
                f"[SUCCESS] {provider_name} "
                f"returned valid data"
            )

            return data

        except Exception as error:

            error_type = classify_error(error)

            print(
                f"[FAILED] {provider_name}: "
                f"{str(error)[:200]}"
            )

            # ------------------------------------------------
            # Disable Gemini
            # ------------------------------------------------

            if provider_name == "Gemini":

                if error_type in [
                    "permanent",
                    "daily_quota"
                ]:

                    gemini_available = False

                    print(
                        "[SYSTEM] Gemini disabled "
                        "for the rest of this run."
                    )

            # ------------------------------------------------
            # Disable Groq
            # ------------------------------------------------

            if provider_name == "Groq":

                if error_type in [
                    "permanent",
                    "daily_quota"
                ]:

                    groq_available = False

                    print(
                        "[SYSTEM] Groq disabled "
                        "for the rest of this run."
                    )

            # ------------------------------------------------
            # Disable DeepSeek
            # ------------------------------------------------

            if provider_name == "DeepSeek":

                if error_type in [
                    "permanent",
                    "daily_quota"
                ]:

                    deepseek_available = False

                    print(
                        "[SYSTEM] DeepSeek disabled "
                        "for the rest of this run."
                    )

            continue

    # --------------------------------------------------------
    # All providers failed
    # --------------------------------------------------------

    print(
        "[FAILED] All LLM providers failed."
    )

    return {
        "isStartup": False,
        "entityName": None,
        "employeeCount": None,
        "sourceUrl": source_url,
        "error": "All LLM providers failed"
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    sample_text = """
    TechNova AI is a technology startup building artificial
    intelligence tools for businesses. The company has 75 employees
    and is based in San Francisco.
    """

    result = extract_startup(
        sample_text,
        "https://example.com/technova"
    )

    print("\nFinal Result:")

    print(
        json.dumps(
            result,
            indent=4
        )
    )
