import json
import pandas as pd
import re

def tamil_to_english(text):
    # Simple transliteration mapping (expand as needed)
    mapping = {
        'அ': 'a', 'ஆ': 'aa', 'இ': 'i', 'ஈ': 'ee', 'உ': 'u', 'ஊ': 'oo',
        'எ': 'e', 'ஏ': 'ae', 'ஐ': 'ai', 'ஒ': 'o', 'ஓ': 'oa', 'ஔ': 'au',
        'க': 'ka', 'ங': 'nga', 'ச': 'sa', 'ஞ': 'nya', 'ட': 'ta', 'ண': 'na',
        'த': 'tha', 'ந': 'na', 'ப': 'pa', 'ம': 'ma', 'ய': 'ya', 'ர': 'ra',
        'ல': 'la', 'வ': 'va', 'ழ': 'zha', 'ள': 'la', 'ற': 'ra', 'ன': 'na',
        'ஜ': 'ja', 'ஷ': 'sha', 'ஸ': 'sa', 'ஹ': 'ha', 'ஶ': 'sha',
        ' ': ' ', '்': '', 'ா': 'a', 'ி': 'i', 'ீ': 'ee', 'ு': 'u', 'ூ': 'oo',
        'ெ': 'e', 'ே': 'ae', 'ை': 'ai', 'ொ': 'o', 'ோ': 'oa', 'ௌ': 'au',
        'ஂ': 'm', 'ஃ': 'h',
    }
    # Replace each Tamil character with its English equivalent
    return ''.join([mapping.get(char, char) for char in text])

with open('161.txt', 'r', encoding='utf-8') as f:
    data = json.load(f)

rows = []
for voter in data['Voters']:
    name_en = tamil_to_english(voter['name'])
    relation_en = tamil_to_english(voter['relation_name'])
    row = voter.copy()
    row['name_english'] = name_en
    row['relation_name_english'] = relation_en
    rows.append(row)

# Write to CSV
output_fields = list(rows[0].keys())
df = pd.DataFrame(rows)
df.to_csv('voters_with_english.csv', index=False, encoding='utf-8')
print('CSV file created: voters_with_english.csv')
