import requests

url = "http://127.0.0.1:8000/api/run-detection/"

files = {
    'file': open('data/detect_30_filtered.csv', 'rb')
}

response = requests.post(url, files=files)

print(response.json())