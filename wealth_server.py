from mcp.server.fastmcp import FastMCP
from utils.common import get_embedding
from google.cloud import firestore
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
import google.generativeai as genai
import os
from dotenv import load_dotenv
import logging
import uuid

load_dotenv()

# Initialize clients
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
db = firestore.Client(project=os.getenv('PROJECT_ID'))

logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

# Create MCP server
mcp = FastMCP("RBC Wealth Management Server")

@mcp.tool()
def search_funds(query: str, risk_level: str = None, asset_class: str = None) -> list:
    """
    Search for mutual funds using semantic search.
    
    Args:
        query: Natural language search query (e.g., "retirement income funds")
        risk_level: Optional filter - "Low", "Medium", "High", etc.
        asset_class: Optional filter - "Canadian Equity Funds", "Fixed Income Funds", etc.
    
    Returns:
        List of matching funds with details
    """
    try:
        # Generate query embedding
        query_embedding = get_embedding(query)
        
        # Start with base query
        vector_query = db.collection('funds').find_nearest(
            vector_field='embedding',
            query_vector=query_embedding,
            distance_measure=DistanceMeasure.COSINE,
            limit=10
        )
        
        # Get results
        results = list(vector_query.stream())
        
        # Apply filters in Python (post-processing)
        funds = []
        for doc in results:
            data = doc.to_dict()
            
            # Apply filters
            if risk_level and data.get('risk_level') != risk_level:
                continue
            if asset_class and data.get('asset_class') != asset_class:
                continue
            
            funds.append({
                'fund_id': data.get('fund_id'),
                'name': data.get('name'),
                'asset_class': data.get('asset_class'),
                'risk_level': data.get('risk_level'),
                'mer': data.get('mer'),
                'return_1yr': data.get('return_1yr'),
                'return_3yr': data.get('return_3yr'),
                'return_5yr': data.get('return_5yr'),
                'description': data.get('description')
            })
            
            if len(funds) >= 5:
                break
        
        return funds
    
    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool()
def get_fund_details(fund_id: str) -> dict:
    """
    Get complete details for a specific fund.
    
    Args:
        fund_id: RBC fund code (e.g., "RBF460")
    
    Returns:
        Complete fund information including performance, characteristics, etc.
    """
    try:
        doc = db.collection('funds').document(fund_id).get()
        
        if not doc.exists:
            return {"error": f"Fund {fund_id} not found"}
        
        data = doc.to_dict()
        
        return {
            'fund_id': data.get('fund_id'),
            'name': data.get('name'),
            'asset_class': data.get('asset_class'),
            'risk_level': data.get('risk_level'),
            'mer': data.get('mer'),
            'management_fee': data.get('management_fee'),
            'current_price': data.get('current_price'),
            'performance': data.get('performance'),
            'calendar_returns': data.get('calendar_returns'),
            'characteristics': data.get('characteristics'),
            'description': data.get('description'),
            'inception_date': data.get('inception_date')
        }
    
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def compare_funds(fund_ids: list) -> dict:
    """
    Compare multiple funds side-by-side.
    
    Args:
        fund_ids: List of fund codes to compare (e.g., ["RBF460", "RBF559"])
    
    Returns:
        Comparison table with key metrics
    """
    try:
        funds = []
        
        for fund_id in fund_ids[:5]:  # Limit to 5 funds
            doc = db.collection('funds').document(fund_id).get()
            if doc.exists:
                funds.append(doc.to_dict())
        
        if not funds:
            return {"error": "No funds found"}
        
        comparison = {
            "funds": [
                {
                    "fund_id": f.get('fund_id'),
                    "name": f.get('name'),
                    "risk": f.get('risk_level'),
                    "mer": f.get('mer'),
                    "return_1yr": f.get('return_1yr'),
                    "return_3yr": f.get('return_3yr'),
                    "return_5yr": f.get('return_5yr')
                }
                for f in funds
            ]
        }
        
        return comparison
    
    except Exception as e:
        return {"error": str(e)}

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

# Risk to asset class mapping
RISK_MAPPINGS = {
    "Conservative": ["Money Market Funds", "Fixed Income Funds", "Balanced Funds & Portfolio Solutions"],
    "Moderate": ["Balanced Funds & Portfolio Solutions", "Canadian Equity Funds", "Fixed Income Funds"],
    "Aggressive": ["Canadian Equity Funds", "U.S. Equity Funds", "Global Equity Funds", "International Equity Funds"]
}

@mcp.tool()
def generate_portfolio(risk_profile: str, timeline: int, amount: float) -> list:
    """
    Generate personalized fund recommendations based on investor profile.
    
    Args:
        risk_profile: "Conservative", "Moderate", or "Aggressive"
        timeline: Investment timeline in years
        amount: Investment amount in dollars
    
    Returns:
        List of recommended funds with allocation suggestions
    """
    try:
        # Get suitable asset classes
        suitable_classes = RISK_MAPPINGS.get(risk_profile, ["Balanced Funds & Portfolio Solutions"])
        
        # Query funds
        funds_ref = db.collection('funds')
        query = funds_ref.where('asset_class', 'in', suitable_classes).limit(10)
        
        recommendations = []
        for doc in query.stream():
            fund = doc.to_dict()
            
            # Skip if min investment too high
            if fund.get('min_investment', 0) > amount:
                continue
            
            # Calculate allocation
            allocation_pct = 20 if risk_profile == "Conservative" else 25
            
            recommendations.append({
                "fund_id": fund.get('fund_id'),
                "name": fund.get('name'),
                "asset_class": fund.get('asset_class'),
                "risk_level": fund.get('risk_level'),
                "allocation_percent": allocation_pct,
                "allocation_amount": amount * (allocation_pct / 100),
                "mer": fund.get('mer'),
                "return_5yr": fund.get('return_5yr'),
                "rationale": f"Aligns with your {risk_profile.lower()} risk profile and {timeline}-year timeline"
            })
            
            if len(recommendations) >= 5:
                break
        
        return recommendations
    
    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool()
def calculate_projections(fund_ids: list, amount: float, years: int) -> list:
    """
    Project future returns for selected funds.
    
    Args:
        fund_ids: List of fund codes
        amount: Investment amount
        years: Projection period in years
    
    Returns:
        Projected values (best, expected, worst case)
    """
    try:
        projections = []
        
        for fund_id in fund_ids:
            doc = db.collection('funds').document(fund_id).get()
            if not doc.exists:
                continue
            
            fund = doc.to_dict()
            avg_return = (fund.get('return_5yr') or 7.0) / 100
            
            # Calculate scenarios
            best_case = amount * ((1 + avg_return * 1.5) ** years)
            expected = amount * ((1 + avg_return) ** years)
            worst_case = amount * ((1 + avg_return * 0.5) ** years)
            
            projections.append({
                "fund_id": fund_id,
                "fund_name": fund.get('name'),
                "initial": amount,
                "years": years,
                "best_case": round(best_case, 2),
                "expected": round(expected, 2),
                "worst_case": round(worst_case, 2)
            })
        
        return projections
    
    except Exception as e:
        return [{"error": str(e)}]


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8080))
    logger.info(f"🚀 RBC Wealth Management MCP server started on port {port}")
    
    mcp.run()

