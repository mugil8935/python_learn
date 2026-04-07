"""
Tamil to English Translator using Langchain
Provider-agnostic translator that works with multiple LLM providers.
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Optional, List

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
            temperature=kwargs.get("temperature", 0.7),
            api_key=kwargs.get("api_key"),
        )
    
    elif provider.lower() == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=kwargs.get("model", "claude-3-5-sonnet-20241022"),
            temperature=kwargs.get("temperature", 0.7),
            api_key=kwargs.get("api_key"),
        )
    
    elif provider.lower() == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=kwargs.get("model", "gemini-1.5-pro"),
            temperature=kwargs.get("temperature", 0.7),
            api_key=kwargs.get("api_key"),
        )
    
    else:
        raise ValueError(f"Unsupported provider: {provider}. Use 'openai', 'anthropic', or 'google'")

def chat_with_bot(user_message: str, conversation_history: List[dict], llm: BaseChatModel) -> Optional[str]:
    """
    Chat with Langchain chatbot.
    
    Args:
        user_message: User's message
        conversation_history: List of previous messages in the conversation
        llm: BaseChatModel instance
        
    Returns:
        Bot's response
    """
    try:
        # Add user message to history
        conversation_history.append({
            "role": "user",
            "content": user_message
        })

        messages = [
            SystemMessage(content="You are a helpful assistant."),
        ] + [
            HumanMessage(content=msg["content"]) if msg["role"] == "user" else SystemMessage(content=msg["content"])
            for msg in conversation_history
        ]

        response = llm.invoke(messages)
        bot_response = response.content

        # Add bot response to history
        conversation_history.append({
            "role": "assistant",
            "content": bot_response
        })

        return bot_response
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    """Main chatbot function."""
    
    print("=" * 70)
    print("CHATBOT (Langchain)")
    print("=" * 70)
    print("Type your message (or 'quit' to exit):\n")
    
    # Configuration - Easy to change provider
    PROVIDER = "openai"  # Change to "anthropic" or "google" to use different provider

    # Initialize LLM
    try:
        llm = get_language_model(PROVIDER)
        print(f"✓ Loaded {PROVIDER.upper()} model\n")
    except Exception as e:
        print(f"✗ Error initializing model: {e}")
        return

    # Keep conversation history for context
    conversation_history = []
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Exiting chatbot...")
            break
        
        if not user_input:
            print("Please enter something.\n")
            continue
        
        bot_output = chat_with_bot(user_input, conversation_history, llm)
        print(f"Bot: {bot_output}\n")

if __name__ == "__main__":
    main()
