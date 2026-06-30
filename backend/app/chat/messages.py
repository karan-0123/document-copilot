from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, UserPromptPart, TextPart

def convert_to_agent_history(messages: list[dict]) -> list[ModelMessage]:
    """Converts frontend Vercel AI SDK request message history into Pydantic AI ModelMessage history.
    
    Expects list of dicts with keys 'role' ('user', 'assistant') and 'content'.
    """
    history: list[ModelMessage] = []
    
    # We map the chat history up to the last message (excluding the active user prompt)
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "").strip()
        if not content:
            continue
            
        if role == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif role == "assistant":
            # For assistant, we map back as standard text responses
            history.append(ModelResponse(parts=[TextPart(content=content)]))
            
    return history
