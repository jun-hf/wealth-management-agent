"""
Test script for Firestore vector search functionality
Tests all indexes and search patterns
"""

import os
from dotenv import load_dotenv
from google.cloud import firestore
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
import google.generativeai as genai

# Load environment
load_dotenv()
PROJECT_ID = os.getenv('PROJECT_ID')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Initialize clients
db = firestore.Client(project=PROJECT_ID, database='(default)')
genai.configure(api_key=GEMINI_API_KEY)

def get_embedding(text: str) -> list[float]:
    """Generate embedding using Gemini"""
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_query"
    )
    return result['embedding']

def test_basic_search():
    """Test 1: Basic vector search without filters"""
    print("\n" + "="*60)
    print("TEST 1: Basic Vector Search")
    print("="*60)
    
    query = "low risk Canadian equity funds"
    print(f"\nQuery: '{query}'")
    
    query_embedding = get_embedding(query)
    
    vector_query = db.collection('funds').find_nearest(
        vector_field='embedding',
        query_vector=query_embedding,
        distance_measure=DistanceMeasure.COSINE,
        limit=5
    )
    
    results = list(vector_query.stream())
    print(f"\nFound {len(results)} results:")
    
    for i, doc in enumerate(results, 1):
        data = doc.to_dict()
        print(f"\n{i}. {data['name']}")
        print(f"   Fund ID: {data['fund_id']}")
        print(f"   Asset Class: {data['asset_class']}")
        print(f"   Risk Level: {data['risk_level']}")
        print(f"   5yr Return: {data.get('return_5yr', 'N/A')}%")
        print(f"   MER: {data.get('mer', 'N/A')}%")

def test_risk_filter():
    """Test 2: Vector search with risk level filter"""
    print("\n" + "="*60)
    print("TEST 2: Vector Search with Risk Filter")
    print("="*60)
    
    query = "Canadian equity funds"
    risk_level = "Low"
    print(f"\nQuery: '{query}'")
    print(f"Filter: Risk Level = '{risk_level}'")
    
    query_embedding = get_embedding(query)
    
    vector_query = db.collection('funds').where(
        filter=firestore.FieldFilter('risk_level', '==', risk_level)
    ).find_nearest(
        vector_field='embedding',
        query_vector=query_embedding,
        distance_measure=DistanceMeasure.COSINE,
        limit=5
    )
    
    results = vector_query.get()
    print(f"\nFound {len(results)} results:")
    
    for i, doc in enumerate(results, 1):
        data = doc.to_dict()
        print(f"\n{i}. {data['name']}")
        print(f"   Risk Level: {data['risk_level']}")
        print(f"   Asset Class: {data['asset_class']}")
        print(f"   5yr Return: {data.get('return_5yr', 'N/A')}%")

def test_asset_class_filter():
    """Test 3: Vector search with asset class filter"""
    print("\n" + "="*60)
    print("TEST 3: Vector Search with Asset Class Filter")
    print("="*60)
    
    query = "growth focused investments"
    asset_class = "Canadian Equity Funds"
    print(f"\nQuery: '{query}'")
    print(f"Filter: Asset Class = '{asset_class}'")
    
    query_embedding = get_embedding(query)
    
    vector_query = db.collection('funds').where(
        filter=firestore.FieldFilter('asset_class', '==', asset_class)
    ).find_nearest(
        vector_field='embedding',
        query_vector=query_embedding,
        distance_measure=DistanceMeasure.COSINE,
        limit=5
    )
    
    results = vector_query.get()
    print(f"\nFound {len(results)} results:")
    
    for i, doc in enumerate(results, 1):
        data = doc.to_dict()
        print(f"\n{i}. {data['name']}")
        print(f"   Asset Class: {data['asset_class']}")
        print(f"   Risk Level: {data['risk_level']}")
        print(f"   5yr Return: {data.get('return_5yr', 'N/A')}%")

def test_performance_range():
    """Test 4: Vector search with performance filter"""
    print("\n" + "="*60)
    print("TEST 4: Vector Search with Performance Filter")
    print("="*60)
    
    query = "high performing equity funds"
    min_return = 10.0  # 10% minimum 5-year return
    print(f"\nQuery: '{query}'")
    print(f"Filter: 5yr Return >= {min_return}%")
    
    query_embedding = get_embedding(query)
    
    vector_query = db.collection('funds').where(
        filter=firestore.FieldFilter('return_5yr', '>=', min_return)
    ).find_nearest(
        vector_field='embedding',
        query_vector=query_embedding,
        distance_measure=DistanceMeasure.COSINE,
        limit=5
    )
    
    results = vector_query.get()
    print(f"\nFound {len(results)} results:")
    
    for i, doc in enumerate(results, 1):
        data = doc.to_dict()
        print(f"\n{i}. {data['name']}")
        print(f"   5yr Return: {data.get('return_5yr', 'N/A')}%")
        print(f"   Risk Level: {data['risk_level']}")
        print(f"   Asset Class: {data['asset_class']}")

def test_data_stats():
    """Test 6: Check data statistics"""
    print("\n" + "="*60)
    print("TEST 6: Data Statistics")
    print("="*60)
    
    # Count total funds
    total_funds = db.collection('funds').count().get()[0][0].value
    print(f"\nTotal funds in database: {total_funds}")
    
    # Count by risk level
    print("\nFunds by Risk Level:")
    risk_levels = ["Low", "Low to Medium", "Medium", "Medium to High", "High"]
    for risk in risk_levels:
        count = db.collection('funds').where(
            filter=firestore.FieldFilter('risk_level', '==', risk)
        ).count().get()[0][0].value
        print(f"  {risk}: {count}")
    
    # Count by asset class
    print("\nFunds by Asset Class:")
    asset_classes = [
        "Money Market Funds",
        "Fixed Income Funds",
        "Canadian Equity Funds",
        "U.S. Equity Funds",
        "International Equity Funds",
        "Global Equity Funds",
        "North American Equity Funds",
        "Balanced Funds & Portfolio Solutions",
        "Alternative Investments"
    ]
    for asset_class in asset_classes:
        count = db.collection('funds').where(
            filter=firestore.FieldFilter('asset_class', '==', asset_class)
        ).count().get()[0][0].value
        if count > 0:
            print(f"  {asset_class}: {count}")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("FIRESTORE VECTOR SEARCH TESTS")
    print("="*60)
    
    try:
        # Run all tests
        test_data_stats()
        test_basic_search()
        test_risk_filter()
        test_asset_class_filter()
        test_performance_range()
        test_multiple_filters()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*60)
        print("\nVector search is working correctly!")
        print("Ready to build the agent.")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTroubleshooting tips:")
        print("1. Check that indexes are fully built (takes 5-10 mins)")
        print("2. Verify .env file has correct PROJECT_ID and GEMINI_API_KEY")
        print("3. Ensure funds collection exists in Firestore")