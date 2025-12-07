from mcp.server.fastmcp import FastMCP
from google.cloud import firestore
import os
from dotenv import load_dotenv
from datetime import datetime
import uuid

load_dotenv()

db = firestore.Client(project=os.getenv('PROJECT_ID'))

mcp = FastMCP("crm")

@mcp.tool()
def save_conversation(conversation_id: str, messages: list, user_profile: dict) -> dict:
    """
    Save conversation history to Firestore.
    
    Args:
        conversation_id: Unique conversation ID
        messages: List of message objects
        user_profile: User profile data (risk, timeline, amount)
    
    Returns:
        Success status
    """
    try:
        doc = {
            'conversation_id': conversation_id,
            'messages': messages,
            'user_profile': user_profile,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'exchange_count': len([m for m in messages if m.get('role') == 'user'])
        }
        
        db.collection('conversations').document(conversation_id).set(doc, merge=True)
        
        return {"success": True, "conversation_id": conversation_id}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def capture_lead(name: str, email: str, phone: str, preferred_time: str, conversation_id: str = None) -> dict:
    """
    Capture lead information for follow-up.
    
    Args:
        name: Client's full name
        email: Email address
        phone: Phone number
        preferred_time: When they prefer to be contacted
        conversation_id: Optional - link to conversation
    
    Returns:
        Success status with lead ID
    """
    try:
        lead_id = f"lead_{uuid.uuid4().hex[:8]}"
        
        lead_data = {
            'lead_id': lead_id,
            'name': name,
            'email': email,
            'phone': phone,
            'preferred_time': preferred_time,
            'conversation_id': conversation_id,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'status': 'new'
        }
        
        db.collection('leads').document(lead_id).set(lead_data)
        
        # Update conversation to mark lead captured
        if conversation_id:
            db.collection('conversations').document(conversation_id).update({
                'lead_captured': True,
                'lead_id': lead_id
            })
        
        return {
            "success": True,
            "lead_id": lead_id,
            "message": "Thank you! Our team will contact you within 24 hours."
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}