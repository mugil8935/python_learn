"""
Tamil to English Translator using Langchain
Provider-agnostic translator that works with multiple LLM providers.
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Optional

def get_language_model(provider: str = "openai", **kwargs) -> BaseChatModel:
    """
    Get LLM instance from any provider.
    
    Args:
        provider: "openai", "anthropic", "google" (default: "openai")
        **kwargs: Provider-specific arguments (model, api_key, temperature, etc.)
        
    Returns:
        BaseChatModel instance
    """
    
    if provider.lower() == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=kwargs.get("model", "gpt-4o-mini"),
            temperature=kwargs.get("temperature", 0.3),
            api_key=kwargs.get("api_key"),
        )
    
    elif provider.lower() == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=kwargs.get("model", "claude-3-5-sonnet-20241022"),
            temperature=kwargs.get("temperature", 0.3),
            api_key=kwargs.get("api_key"),
        )
    
    elif provider.lower() == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=kwargs.get("model", "gemini-1.5-pro"),
            temperature=kwargs.get("temperature", 0.3),
            api_key=kwargs.get("api_key"),
        )
    
    else:
        raise ValueError(f"Unsupported provider: {provider}. Use 'openai', 'anthropic', or 'google'")

def translate_tamil_to_english(tamil_text: str, llm: BaseChatModel) -> Optional[str]:
    """
    Translate Tamil text to English using Langchain.
    
    Args:
        tamil_text: Text in Tamil language
        llm: BaseChatModel instance (from any provider)
        
    Returns:
        Translated text in English or None if error
    """
    try:
        messages = [
            SystemMessage(
                content="You are a professional translator. Translate Tamil text to English accurately and naturally. Return only the translated text."
            ),
            HumanMessage(
                content=f"Translate this Tamil text to English:\n\n{tamil_text}"
            )
        ]
        
        response = llm.invoke(messages)
        return response.content
    
    except Exception as e:
        print(f"Error during translation: {e}")
        return None

def main():
    """Main function with example translations."""
    
    # Configuration - Easy to change provider
    PROVIDER = "openai"  # Change to "anthropic" or "google" to use different provider
    
    examples = [
        "வணக்கம், உங்கள் பெயர் என்ன?",  # Hello, what is your name?
        "நான் இந்தியாவில் வசிக்கிறேன்",  # I live in India
        "இன்று மிகவும் வெப்பமாக உள்ளது",  # It is very hot today
        "நீங்கள் எப்போது வருவீர்கள்?",  # When will you come?
        "தமிழ் மொழி மிகவும் அழகான மொழி",  # Tamil language is a beautiful language
    ]
    
    print("=" * 70)
    print("TAMIL TO ENGLISH TRANSLATOR (Langchain)")
    print(f"Provider: {PROVIDER.upper()}")
    print("=" * 70 + "\n")
    
    # Initialize LLM
    try:
        llm = get_language_model(PROVIDER)
        print(f"✓ Loaded {PROVIDER.upper()} model\n")
    except Exception as e:
        print(f"✗ Error initializing model: {e}")
        return
    
    # Translate examples
    print("BATCH TRANSLATION:")
    print("-" * 70)
    for i, tamil_text in enumerate(examples, 1):
        english_text = translate_tamil_to_english(tamil_text, llm)
        print(f"\n[Example {i}]")
        print(f"Tamil:   {tamil_text}")
        print(f"English: {english_text}")
    
    # Interactive mode
    print("\n" + "=" * 70)
    print("INTERACTIVE MODE")
    print("=" * 70)
    print("Enter Tamil text to translate (or 'quit' to exit):\n")
    
    while True:
        tamil_input = input("Tamil: ").strip()
        
        if tamil_input.lower() in ["quit", "exit", "q"]:
            print("\nExiting translator...")
            break
        
        if not tamil_input:
            print("Please enter some text to translate.\n")
            continue
        
        english_output = translate_tamil_to_english(tamil_input, llm)
        if english_output:
            print(f"English: {english_output}\n")
        else:
            print("Translation failed. Try again.\n")

def provider_comparison():
    """Compare translations from different providers."""
    
    test_text = "வணக்கம், நீங்கள் எப்படி இருக்கிறீர்கள்?"
    providers = ["openai", "anthropic", "google"]
    
    print("\n" + "=" * 70)
    print("PROVIDER COMPARISON")
    print("=" * 70)
    print(f"Test Text: {test_text}\n")
    
    for provider in providers:
        try:
            llm = get_language_model(provider)
            translation = translate_tamil_to_english(test_text, llm)
            print(f"[{provider.upper()}]")
            print(f"Translation: {translation}\n")
        except Exception as e:
            print(f"[{provider.upper()}] Error: {e}\n")

if __name__ == "__main__":
    # Uncomment to compare different providers
    # provider_comparison()
    
    # Run main translator
    main()
