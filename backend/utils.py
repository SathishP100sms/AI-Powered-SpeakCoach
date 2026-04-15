import re

# ======================
# SYSTEM PROMPT
# ======================
SYSTEM_PROMPT = """You are an advanced AI Spoken English Coach designed to behave like a real human trainer.

PRIMARY GOAL:
Help the user speak English fluently, confidently, and naturally for real-life conversations and job interviews.

DOMAIN FOCUS:
You mainly focus on:
• Spoken English
• Grammar correction
• Vocabulary improvement
• Pronunciation guidance (text-based)
• Interview preparation

If the user goes slightly off-topic, gently guide them back instead of rejecting:
"That’s interesting! Let’s connect it to improving your English..."

---

CORE BEHAVIOR:

1. ERROR DETECTION (SMART)
- Analyze the user's sentence.
- Detect grammar, tense, word choice, and fluency issues.

2. CORRECTION + IMPROVEMENT
Always provide:
• Corrected sentence
• More natural spoken version
• Optional advanced version (only if useful)

If NO mistakes:
• Say: "Your sentence is already correct ✅"
• Then suggest a more natural or fluent variation

3. SIMPLE EXPLANATION
- Keep explanations short and practical.
- Avoid heavy grammar theory.

4. INTERACTIVE COACHING
- Always continue conversation.
- Ask 1 follow-up question OR give a small speaking task.

5. ADAPTIVE COMMUNICATION
- Beginner → simple corrections
- Intermediate → better phrasing
- Advanced → natural tone & fluency

6. VOICE INPUT HANDLING
- If sentence looks like speech/transcription:
  • Fix clarity and structure
  • Normalize spoken errors

7. INTERVIEW MODE
Trigger: "Start Interview"

- Ask one question at a time
- Wait for answer
- Evaluate:
  • Grammar
  • Clarity
  • Confidence
  • Structure

Respond with:
[Corrected Answer]
[Score: X/10]
[Feedback]
[Better Answer]
[Next Question]

8. CONVERSATION MODE
Trigger: "Start Conversation"

- Talk like a real human (friend/HR)
- Keep responses short and natural
- Avoid robotic structure

9. GRAMMAR PRACTICE MODE
Trigger: "Practice Grammar"

- Give exercises:
  • Fill in the blanks
  • Error correction
  • Sentence building

---

RESPONSE STYLE (DEFAULT):

If user makes mistakes:
[Corrected]
[Why]
[Better Way]
[Your Turn]

If user is correct:
[Feedback]
[Better Way]
[Your Turn]

---

TONE:
- Friendly, motivating, human-like
- Encourage confidence
- Never sound strict or robotic

---

OUTPUT RULES:
- Keep responses under 100 words
- Avoid long explanations
- Prioritize speaking improvement

---

GOAL:
Make the user confident in real conversations, interviews, and daily English communication.
"""


# ======================
# MODE CONFIGS
# ======================
MODE_CONFIGS: dict[str, dict] = {
    "grammar": {
        "temperature": 0.2,
        "top_p": 0.8,
        "top_k": 20,
        "max_output_tokens": 250,
    },
    "conversation": {
        "temperature": 0.5,
        "top_p": 0.9,
        "top_k": 40,
        "max_output_tokens": 300,
    },
    "interview": {
        "temperature": 0.4,
        "top_p": 0.9,
        "top_k": 40,
        "max_output_tokens": 400,
    },
}

# Default fallback
_DEFAULT_MODE = "conversation"


def get_config(mode: str) -> dict:
    """Return Gemini generation config based on selected mode."""
    return MODE_CONFIGS.get(mode.lower().strip(), MODE_CONFIGS[_DEFAULT_MODE])


def build_system_prompt(mode: str) -> str:
    """Return system prompt tailored to the selected mode."""
    mode = mode.lower().strip()

    suffixes = {
        "grammar":      "\n\nFocus more on grammar correction and explanations.",
        "interview":    "\n\nAct strictly as an interviewer. Ask questions one by one and evaluate answers.",
        "conversation": "\n\nSpeak like a friendly human and keep conversation natural.",
    }

    return SYSTEM_PROMPT + suffixes.get(mode, suffixes[_DEFAULT_MODE])


# ======================
# TTS TEXT CLEANER
# ======================
# Pre-compiled patterns for performance
_RE_BOLD        = re.compile(r"(\*\*|__)(.*?)\1")
_RE_ITALIC      = re.compile(r"(\*|_)(.*?)\1")
_RE_CODE        = re.compile(r"`(.*?)`")
_RE_HEADING     = re.compile(r"^#+\s*", re.MULTILINE)
_RE_BRACKET_TAG = re.compile(r"\[.*?\]")   # removes [Corrected Sentence], [Why?] etc.
_RE_NON_ASCII   = re.compile(r"[^\x00-\x7F]+")
_RE_MULTI_SPACE = re.compile(r" {2,}")
_RE_DOT_SPACE   = re.compile(r"\.\s+")
_RE_Q_SPACE     = re.compile(r"\?\s+")
_RE_EXCL_SPACE  = re.compile(r"!\s+")


def humanize_tts(text: str) -> str:
    """
    Convert LLM markdown/structured text into clean,
    natural-sounding speech for TTS engines.
    """
    if not text:
        return ""

    # 1. Strip markdown formatting
    text = _RE_BOLD.sub(r"\2", text)
    text = _RE_ITALIC.sub(r"\2", text)
    text = _RE_CODE.sub(r"\1", text)
    text = _RE_HEADING.sub("", text)

    # 2. Remove response-structure labels like [Why?], [Score: X/10]
    text = _RE_BRACKET_TAG.sub("", text)

    # 3. Convert bullet lines to plain sentences
    lines = text.split("\n")
    clean_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # strip bullet/dash prefix
        line = re.sub(r"^[-•*]\s*", "", line)
        # ensure sentence ends with punctuation
        if line and line[-1] not in ".!?":
            line += "."
        clean_lines.append(line)
    text = " ".join(clean_lines)

    # 4. Normalise sentence spacing (single space after punctuation)
    text = _RE_DOT_SPACE.sub(". ", text)
    text = _RE_Q_SPACE.sub("? ", text)
    text = _RE_EXCL_SPACE.sub("! ", text)

    # 5. Remove non-ASCII (emojis, special chars)
    text = _RE_NON_ASCII.sub("", text)

    # 6. Collapse multiple spaces
    text = _RE_MULTI_SPACE.sub(" ", text)

    return text.strip()
