# ====================
# LLM Prompt Templates
# ====================
#

# Study target prompts
STUDY_TARGET_SYSTEM_PROMPT = "You are a neuroscience expert and you are interested in developing a study target (objective or specific questions of the study) for a given dataset."

STUDY_TARGET_USER_PROMPT = """
{}
Given a dataset title, description, DOI title, and abstract, your task is to succinctly discern the study target, encompassing both the overarching goal and specific questions. 
In instances where any of the four components is missing/None, offer insights based on available information.
Present your response in a short and concise one-sentence format and ensure any essential subject or NER related keywords are present.
Start all your responses with the following: The study target is to...
-----
Dataset Title: {}
Dataset Description: {}
-----
Related DOI Title: {}
Related DOI Abstract: {}
-----
"""

# keyword extraction prompts
KEYWORDS_SYSTEM_PROMPT = "You are a neuroscience expert and you are interested in extracting important/related entities from a study target text."

KEYWORDS_USER_PROMPT = """
Here is the study target (objective and/or question) for a given neurophysiological dataset:
{}
-----
Analyze the study target and return a ranked list of the top {} most relevant entities (or grouped entities) ordered from most relevant to least relevant.
If a word or noun does not seem related enough to be a entity, do NOT include it in the list.
The format of the output list should be the {} entities in a SINGLE-row CSV (comma-separated values) format.
"""