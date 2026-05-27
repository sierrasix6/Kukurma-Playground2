import requests

def test_pollinations():
    url = "https://text.pollinations.ai/"
    payload = {
        "messages": [
            {"role": "system", "content": "You are a professional football match outcome predictor. Give a very brief prediction."},
            {"role": "user", "content": "Predict Chelsea vs Arsenal score and brief reason without using any emojis."}
        ],
        "model": "openai"
    }
    
    print("Testing Pollinations AI text endpoint...")
    resp = requests.post(url, json=payload)
    print(f"Status: {resp.status_code}")
    print("Response text:")
    print(resp.text)

if __name__ == "__main__":
    test_pollinations()
