import gradio as gr
import google.generativeai as genai
from google.cloud import firestore
import os
from dotenv import load_dotenv
import uuid
from datetime import datetime

# Import MCP functions directly
import sys
from wealth_server import search_funds, get_fund_details, compare_funds, generate_portfolio, capture_lead, save_conversation

load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
db = firestore.Client(project=os.getenv('PROJECT_ID'))

# System prompt
SYSTEM_PROMPT = """You are an RBC wealth management advisor assistant.

Your goals:
1. Understand client's investment goals (risk tolerance, timeline, amount)
2. Recommend suitable RBC mutual funds using your tools
3. Answer questions about fund performance and features
4. After 3+ exchanges, invite them to schedule a call

Available tools:
- search_funds: Find funds by query and filters
- get_fund_details: Get complete fund info
- compare_funds: Compare multiple funds
- generate_portfolio: Create personalized recommendations
- capture_lead: Save contact info

Guidelines:
- Be conversational and helpful
- Ask about risk tolerance (Conservative/Moderate/Aggressive), timeline, and amount if unknown
- Only recommend funds from search results
- After 3+ exchanges, suggest: "Would you like to speak with one of our advisors?"

FORMATTING INSTRUCTIONS:
When presenting fund results, use this structure:

For search results or recommendations:
```
Based on your profile, here are some excellent options:

### 🏆 [Fund Name] (Fund Code)
**Asset Class:** [asset_class]
**Risk Level:** [risk_level]
**MER:** [mer]%
**Performance:**
- 1 Year: [return_1yr]%
- 3 Year: [return_3yr]%
- 5 Year: [return_5yr]%

[Brief description or key features]

---

[Repeat for each fund]
```

For portfolio recommendations:
```
### 💼 Your Personalized Portfolio

**Investment Details:**
- Amount: $[amount]
- Risk Profile: [Conservative/Moderate/Aggressive]
- Timeline: [years] years

**Recommended Allocation:**

#### Fund 1: [Name] ([allocation]%)
- Allocation: $[amount]
- Rationale: [reason]
- 5-Year Return: [return]%

[Repeat for each fund]

**Next Steps:** [Suggest scheduling call if appropriate]
```

For comparisons:
```
### 📊 Fund Comparison

| Metric | Fund 1 | Fund 2 | Fund 3 |
|--------|--------|--------|--------|
| Risk Level | [x] | [x] | [x] |
| MER | [x]% | [x]% | [x]% |
| 1-Year Return | [x]% | [x]% | [x]% |
| 3-Year Return | [x]% | [x]% | [x]% |
| 5-Year Return | [x]% | [x]% | [x]% |
```

Risk levels: Conservative, Moderate, Aggressive
"""

# Configure Gemini with tools
model = genai.GenerativeModel(
    model_name='models/gemini-2.5-flash',  # Changed from 'gemini-1.5-pro'
    tools=[search_funds, get_fund_details, compare_funds, generate_portfolio],
    system_instruction=SYSTEM_PROMPT
)

# Session state
conversation_id = f"conv_{uuid.uuid4().hex[:8]}"

def format_percentage(value):
    """Format percentage values safely"""
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.2f}%"
    except (ValueError, TypeError):
        return "N/A"

def format_currency(value):
    """Format currency values"""
    if value is None:
        return "N/A"
    try:
        return f"${float(value):,.2f}"
    except (ValueError, TypeError):
        return "N/A"

def chat_response(message, history):
    """Handle chat interaction"""
    
    try:
        # Handle message format from Gradio
        # Sometimes Gradio sends: [{'text': 'message', 'type': 'text'}]
        if isinstance(message, list) and len(message) > 0:
            if isinstance(message[0], dict):
                message = message[0].get('text', '')
        
        # Build Gemini history from Gradio history
        gemini_history = []
        for item in history:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                user_msg = item[0]
                assistant_msg = item[1]
                
                # Extract text if in list format
                if isinstance(user_msg, list) and len(user_msg) > 0:
                    if isinstance(user_msg[0], dict):
                        user_msg = user_msg[0].get('text', '')
                
                gemini_history.append({
                    "role": "user",
                    "parts": [str(user_msg)]
                })
                
                if assistant_msg:
                    # Extract text if in list format
                    if isinstance(assistant_msg, list) and len(assistant_msg) > 0:
                        if isinstance(assistant_msg[0], dict):
                            assistant_msg = assistant_msg[0].get('text', '')
                    
                    gemini_history.append({
                        "role": "model",
                        "parts": [str(assistant_msg)]
                    })
        
        # Create chat session with history
        chat_session = model.start_chat(history=gemini_history)
        
        # Send message and get response
        response = chat_session.send_message(message)
        
        # Handle function calls
        while response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]
            
            # Check if it's a function call
            if hasattr(part, 'function_call') and part.function_call:
                function_call = part.function_call
                function_name = function_call.name
                function_args = dict(function_call.args)
                
                print(f"Calling function: {function_name} with args: {function_args}")
                
                # Execute the function
                function_map = {
                    'search_funds': search_funds,
                    'get_fund_details': get_fund_details,
                    'compare_funds': compare_funds,
                    'generate_portfolio': generate_portfolio,
                    'capture_lead': capture_lead
                }
                
                if function_name in function_map:
                    function_result = function_map[function_name](**function_args)
                    
                    print(f"Function result type: {type(function_result)}")
                    print(f"Function result: {function_result}")
                    
                    # Ensure result is JSON-serializable
                    # Convert to dict format if it's a list
                    if isinstance(function_result, list):
                        serialized_result = {"results": function_result}
                    elif isinstance(function_result, dict):
                        serialized_result = function_result
                    else:
                        serialized_result = {"result": str(function_result)}
                    
                    # Send function response back to model
                    response = chat_session.send_message(
                        genai.types.content_types.to_content({
                            "parts": [{
                                "function_response": {
                                    "name": function_name,
                                    "response": serialized_result
                                }
                            }]
                        })
                    )
                else:
                    return f"Unknown function: {function_name}"
            else:
                # Text response is ready
                break
        
        response_text = response.text
        
        # Save to Firestore (optional)
        try:
            messages = []
            for item in history:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    user_msg = item[0]
                    bot_msg = item[1]
                    
                    # Extract text if in list format
                    if isinstance(user_msg, list) and len(user_msg) > 0:
                        if isinstance(user_msg[0], dict):
                            user_msg = user_msg[0].get('text', '')
                    
                    messages.append({"role": "user", "content": str(user_msg), "timestamp": datetime.now().isoformat()})
                    
                    if bot_msg:
                        # Extract text if in list format
                        if isinstance(bot_msg, list) and len(bot_msg) > 0:
                            if isinstance(bot_msg[0], dict):
                                bot_msg = bot_msg[0].get('text', '')
                        
                        messages.append({"role": "assistant", "content": str(bot_msg), "timestamp": datetime.now().isoformat()})
            
            messages.append({"role": "user", "content": str(message), "timestamp": datetime.now().isoformat()})
            messages.append({"role": "assistant", "content": response_text, "timestamp": datetime.now().isoformat()})
            
            save_conversation(
                conversation_id=conversation_id,
                messages=messages,
                user_profile={}
            )
        except Exception as e:
            print(f"Error saving to Firestore: {e}")
        
        return response_text
    
    except Exception as e:
        return f"Error: {str(e)}"

# Build Simple Gradio UI - Compatible with Gradio 5.9.1
with gr.Blocks(title="RBC Wealth Assistant") as app:
    
    # Custom CSS for better formatting
    gr.HTML("""
    <style>
        .message-wrap {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .bot-message h3 {
            color: #005EB8;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }
        .bot-message h4 {
            color: #0073CF;
            margin-top: 1em;
            margin-bottom: 0.5em;
        }
        .bot-message strong {
            color: #333;
        }
        .bot-message table {
            width: 100%;
            border-collapse: collapse;
            margin: 1em 0;
        }
        .bot-message table th {
            background-color: #005EB8;
            color: white;
            padding: 10px;
            text-align: left;
        }
        .bot-message table td {
            padding: 8px;
            border-bottom: 1px solid #ddd;
        }
        .bot-message hr {
            border: none;
            border-top: 2px solid #e0e0e0;
            margin: 1.5em 0;
        }
    </style>
    """)
    
    gr.Markdown("# 🏦 RBC Wealth Management Assistant")
    gr.Markdown("Get AI-powered investment recommendations tailored to your goals")
    
    # Simple ChatInterface - using only compatible parameters
    gr.ChatInterface(
        fn=chat_response,
        examples=[
            "I want to invest $50,000 for retirement",
            "Show me low-risk Canadian equity funds",
            "What are the best performing funds?",
            "Compare RBF460 and RBF559",
            "I'd like a conservative portfolio for 20 years"
        ]
    )

if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )