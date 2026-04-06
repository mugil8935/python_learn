"""
Simple Chatbot using OpenAI API
Engages in conversations on any topic with conversation history.
"""

from openai import OpenAI

# Initialize OpenAI client
client = OpenAI()

def chat_with_bot(user_message: str, conversation_history: list) -> str:
    """
    Chat with OpenAI chatbot.
    
    Args:
        user_message: User's message
        conversation_history: List of previous messages in the conversation
        
    Returns:
        Bot's response
    """
    try:
        # Add user message to history
        conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation_history,
            temperature=0.7,
            n=2
        )
        
        bot_response = response.choices[0].message.content
        
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
    print("CHATBOT")
    print("=" * 70)
    print("Type your message (or 'quit' to exit):\n")
    
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
        
        bot_output = chat_with_bot(user_input, conversation_history)
        print(f"Bot: {bot_output}\n")

if __name__ == "__main__":
    main()
