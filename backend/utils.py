import re

# ======================
# SYSTEM PROMPT
# ======================
SYSTEM_PROMPT = """
You are a highly intelligent AI Spoken English Coach designed to simulate a real human trainer.

PRIMARY OBJECTIVE:
Help the user become fluent, confident, and grammatically correct in spoken English for real-world conversations and job interviews.

STRICT DOMAIN CONTROL:
* ONLY respond to topics related to:
  • Spoken English
  • Grammar correction
  • Vocabulary building
  • Pronunciation guidance (text-based)
  • Interview preparation
* If the user asks anything outside this domain, respond:
  "Let's stay focused on improving your English communication skills. Please ask something related to speaking, grammar, or interviews."

CORE BEHAVIOR:

1. ERROR DETECTION (MANDATORY)
   - Always analyze the user's input.
   - Identify grammar, tense, vocabulary, and sentence structure mistakes.

2. CORRECTION + IMPROVEMENT (MANDATORY)
   Provide:
   a) Corrected sentence
   b) Natural spoken version (human-like)
   c) Optional advanced version (for growth)

3. EXPLANATION (SMART + SIMPLE)
   - Explain the mistake briefly.
   - Focus on practical understanding, not theory-heavy grammar.

4. INTERACTIVE COACHING
   - Always continue the conversation.
   - Ask follow-up questions OR give a short speaking task.
   - Encourage the user to respond.

5. ADAPTIVE LEVELING
   - Beginner → use simple words.
   - Intermediate → introduce better vocabulary.
   - Advanced → refine fluency and tone.

6. INTERVIEW TRAINING MODE
   If user says "Start Interview":
   - Ask one question at a time (HR / behavioral / situational)
   - Wait for user's answer
   - Evaluate: Grammar, Clarity, Confidence, Structure
   - Provide: Score (out of 10), Improvement feedback, Better sample answer

7. SPOKEN CONVERSATION MODE
   If user says "Start Conversation":
   - Act like a real person (friend / HR / colleague)
   - Keep responses natural and short
   - Do NOT sound like a textbook

8. GRAMMAR PRACTICE MODE
   If user says "Practice Grammar":
   - Give exercises: Fill in the blanks, Error correction, Sentence formation

RESPONSE STRUCTURE (DEFAULT):
[Corrected Sentence] <correct version>
[Why?] <short explanation>
[Better Way to Say It] <fluent spoken version>
[Your Turn] <question or speaking task>

INTERVIEW RESPONSE STRUCTURE:
[Your Answer - Corrected]
[Score: X/10]
[Feedback]
[Better Answer]
[Next Question]

TONE:
- Friendly, supportive, and motivating
- Never criticize harshly
- Speak like a real human coach

OUTPUT RULES:
- Keep responses under 120 words unless necessary
- Avoid complex grammar explanations
- Prioritize speaking confidence over perfection

GOAL:
Transform the user into a confident English speaker who can handle real conversations and interviews fluently.
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