import re
import ftfy

def final_cleanup(sentence: str) -> str:
    cleaned_sentence = ftfy.fix_text(sentence)

    for delimiter in [' dan ', ',']:
        parts = cleaned_sentence.split(delimiter)
        if len(parts) > 1:
            last_part = parts[-1].lower()
            previous_part = parts[-2].lower()

            normalized_last = re.sub(r'^(bisa|dapat)?\s*(sebabkan|menyebabkan)\s*', '', last_part.strip()).rstrip('.,?!')
            
            if normalized_last and normalized_last in previous_part:
                cleaned_sentence = delimiter.join(parts[:-1])

    cleaned_sentence = re.sub(r'\s+([.,?!])', r'\1', cleaned_sentence)
    
    cleaned_sentence = re.sub(r'\b(\w+)\s+\1\b', r'\1', cleaned_sentence, flags=re.IGNORECASE)

    if cleaned_sentence:
        cleaned_sentence = cleaned_sentence.lower().capitalize()
        
    return cleaned_sentence.strip()