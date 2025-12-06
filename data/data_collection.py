import os
import requests
import json
from dotenv import load_dotenv
from google.cloud import firestore
import google.generativeai as genai
from datetime import datetime

load_dotenv()

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
db = firestore.Client(project=os.getenv('PROJECT_ID'))

FUND_API_URL = "https://www.rbcgam.com/api/vtl/fds-fund-list?alts=false&langId=1&series=f&language_id=1"

def fetch_funds():
    """
    Fetch fund from RBC API
    """

    try:
        response = requests.get(FUND_API_URL)
        response.raise_for_status()
        funds_data = response.json()

        print(f"Fetched {len(funds_data)} funds")

        with open('data/funds_raw.json', 'w') as f:
            json.dump(funds_data, f, indent=2)
        print("✅ Saved raw data to data/funds_raw.json")
        
        return funds_data

    except Exception as e:
        print(f"Error fetching funds: {e}")
        return []

def generate_description(fund_data):
    """Generate description based on fund attributes"""
    
    asset_class = fund_data.get('assetClass', {}).get('en', 'investment fund')
    risk = fund_data.get('risk', {}).get('en', 'Medium')
    
    # Description templates by asset class
    descriptions = {
        'Money Market Funds': f"Invests in short-term money market instruments with {risk.lower()} risk, emphasizing capital preservation and liquidity.",
        
        'Fixed Income Funds': f"Invests in fixed income securities with {risk.lower()} risk, focusing on income generation and capital preservation.",
        
        'Balanced Funds & Portfolio Solutions': f"Provides balanced exposure to equities and fixed income with {risk.lower()} risk, seeking both growth and income.",
        
        'Canadian Equity Funds': f"Seeks long-term capital growth through Canadian equity investments with {risk.lower()} risk profile.",
        
        'U.S. Equity Funds': f"Seeks long-term capital growth through U.S. equity investments with {risk.lower()} risk profile.",
        
        'North American Equity Funds': f"Seeks long-term capital growth through North American equity investments with {risk.lower()} risk profile.",
        
        'International Equity Funds': f"Seeks long-term capital growth through international equity investments with {risk.lower()} risk profile.",
        
        'Global Equity Funds': f"Seeks long-term capital growth through global equity investments with {risk.lower()} risk profile.",
        
        'Alternative Investments': f"Employs alternative investment strategies with {risk.lower()} risk, seeking diversification and enhanced returns."
    }
    
    # Return matching description or default
    return descriptions.get(
        asset_class,
        f"Investment fund with {risk.lower()} risk profile seeking to achieve investment objectives."
    )

def transform_fund(raw_fund):
    """Transform API data to our Firestore structure"""
    
    # Generate description
    description = generate_description(raw_fund)
    
    # Extract nested fields
    fund_name = raw_fund.get('fundName', {}).get('en', 'Unknown Fund')
    asset_class = raw_fund.get('assetClass', {}).get('en', 'Unknown')
    risk_level = raw_fund.get('risk', {}).get('en', 'Medium')
    
    # Create search text
    search_text = f"""
    {fund_name}
    Asset Class: {asset_class}
    Risk: {risk_level}
    {description}
    """
    
    doc = {
        "fund_id": raw_fund.get('rbcFundCode'),
        "series": raw_fund.get('series', 'F').upper(),
        "name": fund_name,
        "is_active": raw_fund.get('isActive', True),
        "inception_date": raw_fund.get('inceptionDate'),

        "asset_class": asset_class,
        "risk_level": risk_level,
        "mer": raw_fund.get('mer', 0),
        "management_fee": raw_fund.get('managementFees', 0),
        
        "return_1yr": raw_fund.get('performance', {}).get('1Yr'),
        "return_3yr": raw_fund.get('performance', {}).get('3Yr'),
        "return_5yr": raw_fund.get('performance', {}).get('5Yr'),
        "return_ytd": raw_fund.get('performance', {}).get('YTD'),

        "current_price": raw_fund.get('price'),
        "nav": raw_fund.get('navpu'),
        "yield": raw_fund.get('yield'),
        
        "performance": raw_fund.get('performance', {}),
        "calendar_returns": raw_fund.get('calendarReturns', {}),
        "characteristics": raw_fund.get('characteristics', {}),
        
        "pricing": {
            "price": raw_fund.get('price'),
            "nav": raw_fund.get('navpu'),
            "net_change": raw_fund.get('netChange'),
            "pct_change": raw_fund.get('pctChange'),
            "as_of_date": raw_fund.get('analysisDate', {}).get('price')
        },
        
        "distributions": {
            "last_amount": raw_fund.get('distribLast'),
            "last_date": raw_fund.get('distribLastDate'),
            "ytd": raw_fund.get('distribYTD')
        },
        
        "analysis_dates": raw_fund.get('analysisDate', {}),
        
        "description": description,
        "search_text": search_text.strip(),

        "last_updated": firestore.SERVER_TIMESTAMP,
        "data_source": "RBC fds-fund-list API"
    }
    
    return doc

def generate_embedding(search_text):
    """Generate embedding for search text"""
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=search_text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return [0.0] * 768

def load_to_firestore(funds_data):
    """Transform and load funds to Firestore"""
    
    print("\nTransforming and loading funds to Firestore...")
    print("="*50)
    
    successful = 0
    failed = 0
    
    for i, raw_fund in enumerate(funds_data, 1):
        try:
            # Transform
            fund = transform_fund(raw_fund)
            
            # Generate embedding
            print(f"[{i}/{len(funds_data)}] Processing {fund['name'][:50]}...")
            fund['embedding'] = generate_embedding(fund['search_text'])
            
            # Save to Firestore
            db.collection('funds').document(fund['fund_id']).set(fund)
            
            successful += 1
            
            # Progress update every 10 funds
            if i % 10 == 0:
                print(f"   ✓ Loaded {i}/{len(funds_data)} funds")
        
        except Exception as e:
            print(f"Error loading {raw_fund.get('rbcFundCode', 'unknown')}: {e}")
            failed += 1
    
    print("="*50)
    print(f"\nSuccessfully loaded: {successful} funds")
    if failed > 0:
        print(f"Failed: {failed} funds")
    print("="*50)
    
    return successful, failed

def main():

    with open('data/funds_raw.json', 'r') as f:
        data = json.load(f).get('fundData')

    successful, failed = load_to_firestore(data)

    print("\n" + "="*50)
    print("PIPELINE COMPLETE")
    print("="*50)
    print(f"Total: {len(data)}")
    print(f"Success: {successful}")
    print(f"Failed: {failed}")
    print("\nNext: Test vector search")
    print("  python test_vector_search.py")
    print("="*50)


if __name__ == "__main__":
    main()