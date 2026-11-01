from string import punctuation
import re

def slugify(text: str) -> str:
    # Remove punctuation using regex
    text = re.sub(f'[{re.escape(punctuation)}]', '', text)
    # Convert to lowercase and replace spaces with hyphens
    return text.lower().replace(' ', '-')
