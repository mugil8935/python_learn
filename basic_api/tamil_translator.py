"""
Simple Tamil to English Translator using OpenAI API
Translates Tamil text to English using GPT models.
"""

from openai import OpenAI

# Initialize OpenAI client
client = OpenAI()

def translate_tamil_to_english(tamil_text: str) -> str:
    """
    Translate Tamil text to English using OpenAI.
    
    Args:
        tamil_text: Text in Tamil language to translate
        
    Returns:
        Translated text in English
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messaexiges=[
                {
                    "role": "system",
                    "content": "You are a professional translator. Translate Tamil text to English accurately and naturally. Return only the translated text."
                },
                {
                    "role": "user",
                    "content": f"Translate this Tamil text to English:\n\n{tamil_text}"
                }
            ],
            temperature=0.1,
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    """Main function with example translations."""
    
    examples = [
        "வணக்கம், உங்கள் பெயர் என்ன?",  # Hello, what is your name?
        "நான் இந்தியாவில் வசிக்கிறேன்",  # I live in India
        "இன்று மிகவும் வெப்பமாக உள்ளது",  # It is very hot today
        "நீங்கள் எப்போது வருவீர்கள்?",  # When will you come?
        "தமிழ் மொழி மிகவும் அழகான மொழி",  # Tamil language is a beautiful language
    ]
    
    print("=" * 70)
    print("TAMIL TO ENGLISH TRANSLATOR")
    print("=" * 70 + "\n")
    
    # # Translate examples
    # for i, tamil_text in enumerate(examples, 1):
    #     english_text = translate_tamil_to_english(tamil_text)
    #     print(f"[Example {i}]")
    #     print(f"Tamil:   {tamil_text}")
    #     print(f"English: {english_text}")
    #     print("-" * 70)
    
    # Interactive mode
    print("\n" + "=" * 70)
    print("INTERACTIVE MODE")
    print("=" * 70)
    print("Enter Tamil text to translate (or 'quit' to exit):\n")
    
    while True:
        tamil_input = input("Tamil: ").strip()
        
        if tamil_input.lower() in ["quit", "exit", "q"]:
            print("Exiting translator...")
            break
        
        if not tamil_input:
            print("Please enter some text to translate.\n")
            continue
        
        english_output = translate_tamil_to_english(tamil_input)
        print(f"English: {english_output}\n")

if __name__ == "__main__":
    main()
