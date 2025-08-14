#!/usr/bin/env python3
"""
Test script for the new simplified bulk upload endpoint with SimpleDirectoryReader
"""
import requests
import json

# Configuration
BASE_URL = "http://127.0.0.1:8000"
CSV_FILE_PATH = r"d:\ProjectV\sample_transactions.csv"

def test_simplified_upload():
    """Test the new simplified upload endpoint"""
    
    print("🚀 Testing simplified bulk upload endpoint with SimpleDirectoryReader...")
    
    # Endpoint URL - now using bulk-uploads/upload/
    url = f"{BASE_URL}/api/v1/bulk-uploads/upload/"
    
    # Prepare file for upload
    try:
        with open(CSV_FILE_PATH, 'rb') as csv_file:
            files = {
                'file': ('sample_transactions.csv', csv_file, 'text/csv')
            }
            
            # Optional: Add company_id if needed
            data = {}
            
            print(f"📤 Uploading {CSV_FILE_PATH} to {url}")
            
            # Make the request
            response = requests.post(url, files=files, data=data)
            
            print(f"📊 Response Status: {response.status_code}")
            print(f"📝 Response Content:")
            
            if response.headers.get('content-type', '').startswith('application/json'):
                response_data = response.json()
                print(json.dumps(response_data, indent=2))
                
                if response.status_code == 201:
                    print("\n✅ Upload successful!")
                    print(f"📋 Bulk Upload ID: {response_data.get('bulk_upload_id')}")
                    print(f"📈 Data Summary: {response_data.get('data_summary')}")
                    print(f"🤖 AI Insights Preview:")
                    insights = response_data.get('ai_insights', '')
                    print(insights[:500] + "..." if len(insights) > 500 else insights)
                    
                    # Test querying the data
                    test_query_data(response_data.get('bulk_upload_id'))
                else:
                    print(f"\n❌ Upload failed with status {response.status_code}")
                    
            else:
                print(response.text)
                
    except FileNotFoundError:
        print(f"❌ CSV file not found: {CSV_FILE_PATH}")
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to {BASE_URL}. Is the Django server running?")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def test_query_data(bulk_upload_id):
    """Test querying the uploaded data"""
    if not bulk_upload_id:
        return
    
    print(f"\n🔍 Testing data querying for upload {bulk_upload_id}...")
    
    url = f"{BASE_URL}/api/v1/bulk-uploads/{bulk_upload_id}/query/"
    
    test_queries = [
        "What are the main expense categories?",
        "Show me the total revenue",
        "What's the largest transaction?",
        "Analyze the spending patterns"
    ]
    
    for query in test_queries:
        try:
            response = requests.post(url, json={'query': query})
            print(f"\n❓ Query: {query}")
            print(f"📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"💬 Answer: {result.get('answer', 'No answer')}")
            else:
                print(f"❌ Query failed: {response.text}")
                
        except Exception as e:
            print(f"❌ Query error: {str(e)}")

if __name__ == "__main__":
    test_simplified_upload()
