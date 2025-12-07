from mcp.server.fastmcp import FastMCP
from utils.common import get_embedding
from google.cloud import firestore
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize clients
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
db = firestore.Client(project=os.getenv('PROJECT_ID'))

# Create MCP server
mcp = FastMCP("fund-knowledge")

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