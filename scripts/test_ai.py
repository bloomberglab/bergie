# Run with: python scripts/test_ai.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.ai_service import get_ai_response

print("=" * 60)
print("Bergie AI Service — smoke test")
print("=" * 60)

# Test 1: Fresh conversation, no history
print("\n[Test 1] Fresh greeting...")
response = get_ai_response(
    history=[],
    user_message="Hi, who are you?",
)
print(f"Response: {response.text}")
print(f"Tokens:   {response.input_tokens} in / {response.output_tokens} out")

# Test 2: With conversation history
print("\n[Test 2] Follow-up question with history...")
history = [
    {"role": "user",      "content": "Hi, who are you?"},
    {"role": "assistant", "content": response.text},
]
response2 = get_ai_response(
    history=history,
    user_message="What kind of courses does EduBerg offer?",
)
print(f"Response: {response2.text}")
print(f"Tokens:   {response2.input_tokens} in / {response2.output_tokens} out")

# Test 3: Out of scope question
print("\n[Test 3] Out of scope question...")
response3 = get_ai_response(
    history=[],
    user_message="Can you help me write a poem about the moon?",
)
print(f"Response: {response3.text}")

print("\n" + "=" * 60)
print("Smoke test complete.")
print("=" * 60)