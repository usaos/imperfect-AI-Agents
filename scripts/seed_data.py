import requests
import json
import random
import time

API_BASE = "http://localhost:8000"
OLLAMA_BASE = "http://localhost:11434"
OLLAMA_MODEL = "qwen2:7b"  # 可用更小的模型加速
TOTAL_COUNT = 1000  # 生成数量

SCENARIOS = [
    {
        "category": "web_scraping",
        "tasks": [
            "Scrape e-commerce product data from Cloudflare-protected site",
            "Crawl dynamic JS-rendered news list page",
            "Bypass IP rate limiting on data API",
            "Handle Google reCAPTCHA v2 on login page"
        ],
        "tags": ["web-scraping", "anti-bot", "cloudflare", "crawler"]
    },
    {
        "category": "data_analysis",
        "tasks": [
            "Clean 1GB dirty CSV with missing values",
            "Merge multiple DataFrames on mismatched keys",
            "Process large dataset with Pandas out of memory",
            "Parse inconsistent datetime formats"
        ],
        "tags": ["pandas", "data-cleaning", "memory", "python"]
    },
    {
        "category": "devops",
        "tasks": [
            "Build Docker image with Python dependency conflicts",
            "Deploy Flask app on Nginx 502 Bad Gateway",
            "Install system package missing .so shared library",
            "Start service with port already in use"
        ],
        "tags": ["docker", "devops", "deployment", "linux"]
    },
    {
        "category": "api_integration",
        "tasks": [
            "Call REST API hit 429 rate limit",
            "Verify API signature authentication failed",
            "Parse XML response with unexpected structure",
            "CORS blocked cross-origin request"
        ],
        "tags": ["api", "rest", "authentication", "cors"]
    },
    {
        "category": "algorithm",
        "tasks": [
            "Calculate floating point sum with precision loss",
            "Recursive function hit maximum recursion depth",
            "Handle integer overflow in large number calculation",
            "Edge case missing in conditional logic"
        ],
        "tags": ["algorithm", "python", "math", "edge-case"]
    }
]

PROMPT_TEMPLATE = """
Generate a realistic AI Agent failure case in strict JSON format, no extra text.
Task: {task}
Category: {category}

Output format:
{{
  "failure_action": "What the agent incorrectly did",
  "failure_error": "Exact error message",
  "pre_condition": "Environment/version condition when error occurs",
  "reflection_analysis": "1 sentence root cause",
  "corrected_action": "1 sentence correct solution",
  "uncertainty_score": 0.1-0.9 float
}}
"""

def generate_one(scenario, task):
    prompt = PROMPT_TEMPLATE.format(task=task, category=scenario["category"])
    try:
        resp = requests.post(f"{OLLAMA_BASE}/api/generate", json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "format": "json",
            "stream": False
        }, timeout=60)
        data = json.loads(resp.json()["response"])
        
        tags = ",".join(random.sample(scenario["tags"], min(2, len(scenario["tags"]))))
        
        payload = {
            "task": task,
            "failure_action": data["failure_action"],
            "failure_error": data["failure_error"],
            "reflection_analysis": data["reflection_analysis"],
            "corrected_action": data["corrected_action"],
            "uncertainty_score": data["uncertainty_score"],
            "pre_condition": data["pre_condition"],
            "tags": tags,
            "source_platform": "seed_script"
        }
        
        res = requests.post(f"{API_BASE}/api/scars/log", json=payload)
        if res.status_code == 200:
            print(f"[+] Added: {task[:40]}...")
            return True
        else:
            print(f"[-] Failed: {res.text}")
            return False
    except Exception as e:
        print(f"[!] Error: {e}")
        return False

def main():
    print(f"Generating {TOTAL_COUNT} seed scars using local Ollama...")
    success = 0
    per_scenario = TOTAL_COUNT // len(SCENARIOS)
    
    for scenario in SCENARIOS:
        for i in range(per_scenario):
            task = random.choice(scenario["tasks"])
            if generate_one(scenario, task):
                success += 1
            time.sleep(0.5)  # 避免压垮本地Ollama
    
    print(f"\nDone! Successfully generated {success} seed scars.")
    print(f"Check stats: {API_BASE}/api/stats")

if __name__ == "__main__":
    main()
