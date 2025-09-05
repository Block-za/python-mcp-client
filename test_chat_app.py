#!/usr/bin/env python3
"""
Test script for the Chat Application
This script tests the basic functionality of the chat application.
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:5000"

def test_auth():
    """Test authentication endpoints"""
    print("Testing authentication...")
    
    # Test login
    response = requests.post(f"{BASE_URL}/api/auth/login", 
                           json={"email": "test@example.com"})
    
    if response.status_code == 200:
        print("✓ Login successful")
    else:
        print(f"✗ Login failed: {response.status_code}")
        return False
    
    # Test auth status
    response = requests.get(f"{BASE_URL}/api/auth/status")
    if response.status_code == 200:
        data = response.json()
        if data.get('logged_in'):
            print("✓ Auth status check successful")
        else:
            print("✗ Auth status check failed")
            return False
    else:
        print(f"✗ Auth status check failed: {response.status_code}")
        return False
    
    return True

def test_conversations():
    """Test conversation management"""
    print("Testing conversation management...")
    
    # Test get conversations (should be empty initially)
    response = requests.get(f"{BASE_URL}/api/conversations")
    if response.status_code == 200:
        print("✓ Get conversations successful")
    else:
        print(f"✗ Get conversations failed: {response.status_code}")
        return False
    
    # Test create conversation
    response = requests.post(f"{BASE_URL}/api/conversations", 
                           json={"title": "Test Conversation"})
    
    if response.status_code == 200:
        data = response.json()
        conversation_id = data['conversation']['id']
        print("✓ Create conversation successful")
    else:
        print(f"✗ Create conversation failed: {response.status_code}")
        return False
    
    return conversation_id

def test_messages(conversation_id):
    """Test message sending"""
    print("Testing message sending...")
    
    # Test send message
    response = requests.post(f"{BASE_URL}/api/conversations/{conversation_id}/messages",
                           json={"content": "Hello, this is a test message!"})
    
    if response.status_code == 200:
        data = response.json()
        print("✓ Send message successful")
        print(f"  User message: {data['user_message']['content'][:50]}...")
        print(f"  Assistant response: {data['assistant_message']['content'][:50]}...")
    else:
        print(f"✗ Send message failed: {response.status_code}")
        return False
    
    return True

def test_conversation_retrieval(conversation_id):
    """Test conversation retrieval"""
    print("Testing conversation retrieval...")
    
    response = requests.get(f"{BASE_URL}/api/conversations/{conversation_id}")
    
    if response.status_code == 200:
        data = response.json()
        messages = data['messages']
        print(f"✓ Retrieve conversation successful ({len(messages)} messages)")
        
        for msg in messages:
            print(f"  {msg['role']}: {msg['content'][:50]}...")
    else:
        print(f"✗ Retrieve conversation failed: {response.status_code}")
        return False
    
    return True

def test_logout():
    """Test logout"""
    print("Testing logout...")
    
    response = requests.post(f"{BASE_URL}/api/auth/logout")
    
    if response.status_code == 200:
        print("✓ Logout successful")
    else:
        print(f"✗ Logout failed: {response.status_code}")
        return False
    
    return True

def main():
    """Main test function"""
    print("=== Chat Application Test Suite ===")
    print()
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/api/auth/status", timeout=5)
        print("✓ Server is running")
    except requests.exceptions.RequestException:
        print("✗ Server is not running. Please start the application first:")
        print("  python app.py")
        sys.exit(1)
    
    print()
    
    # Run tests
    tests_passed = 0
    total_tests = 5
    
    try:
        # Test authentication
        if test_auth():
            tests_passed += 1
        
        print()
        
        # Test conversation creation
        conversation_id = test_conversations()
        if conversation_id:
            tests_passed += 1
        
        print()
        
        # Test message sending
        if test_messages(conversation_id):
            tests_passed += 1
        
        print()
        
        # Test conversation retrieval
        if test_conversation_retrieval(conversation_id):
            tests_passed += 1
        
        print()
        
        # Test logout
        if test_logout():
            tests_passed += 1
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
    
    print()
    print("=== Test Results ===")
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("✓ All tests passed! The chat application is working correctly.")
    else:
        print("✗ Some tests failed. Please check the application setup.")
    
    print()
    print("You can now access the chat application at:")
    print(f"  {BASE_URL}")
    print()
    print("To test the original MCP interface:")
    print(f"  {BASE_URL}/mcp")

if __name__ == "__main__":
    main()
