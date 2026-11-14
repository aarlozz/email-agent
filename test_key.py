from dotenv import load_dotenv
import groq
from groq import Groq

load_dotenv()
client = Groq()

try:
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": "Reply with exactly: key works"}],
        max_tokens=500,   # extra room, since the model reasons before answering
    )

    
    choice = response.choices[0]
    print("Reply:", repr(choice.message.content))
    print("Finish reason:", choice.finish_reason)

except groq.AuthenticationError:
    print("Failed: key is invalid or missing")
except groq.NotFoundError:
    print("Key is correct, but model not found")
except groq.RateLimitError:
    print("Rate limited, wait a minute")
except Exception as e:
    print("Other error:", type(e).__name__, e)