# Test Script for Talent Search Feature
import requests
import json

# Test the talent search endpoint
BASE_URL = "http://localhost:5000"

def test_talent_search():
    """Test the talent search functionality"""
    
    # First, you need to be logged in as HR
    # This is just a test script - in real usage, authentication will be handled by the frontend
    
    test_queries = [
        "I need an AI engineer with 3+ years of experience",
        "Find me React developers for a startup",
        "Show me data scientists with Python and machine learning skills",
        "I want full-stack developers with Node.js experience",
        "Find candidates with experience in healthcare technology",
        "Show me senior software engineers who know AWS and Docker"
    ]
    
    headers = {
        'Content-Type': 'application/json',
        # Add actual authentication token here when testing
        'Authorization': 'Bearer YOUR_TOKEN_HERE'
    }
    
    for query in test_queries:
        print(f"\n🔍 Testing query: '{query}'")
        print("-" * 50)
        
        payload = {
            'query': query,
            'conversation_id': 'test_conversation'
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/talent-search/search",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ AI Response: {data['ai_response']}")
                print(f"📊 Candidates found: {len(data.get('candidates', []))}")
                print(f"🎯 Confidence: {data.get('confidence', 0):.2f}")
                
                if data.get('candidates'):
                    print("\n🏆 Top candidates:")
                    for i, candidate in enumerate(data['candidates'][:2], 1):
                        print(f"  {i}. {candidate['name']} - {candidate['match_score']}% match")
                
                if data.get('follow_up_questions'):
                    print(f"\n❓ Follow-up questions: {len(data['follow_up_questions'])}")
                    for q in data['follow_up_questions'][:2]:
                        print(f"  • {q}")
                        
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        print()

if __name__ == "__main__":
    print("🚀 Talent Search Feature Test")
    print("=" * 50)
    print("Make sure to:")
    print("1. Start the Flask server (python app.py)")
    print("2. Add a valid HR authentication token")
    print("3. Have some candidate resumes in the database")
    print()
    
    # Uncomment the line below to run the tests
    # test_talent_search()
    
    print("Test script ready! Update the token and uncomment test_talent_search() to run.")
