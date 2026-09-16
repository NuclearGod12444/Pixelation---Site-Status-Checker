from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template
import requests

app = Flask(__name__)

SITES_TO_CHECK = [
    "https://google.com",
    "https://github.com",
    "https://reddit.com",
    "https://youtube.com",
    "https://discord.com"
]
REQUEST_TIMEOUT = (2, 5)
MAX_RETRIES = 1
REQUEST_HEADERS = {"User-Agent": "PixelationStatusChecker/1.0"}


def check_site(url):
    last_error = "The request failed."

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.get(
                url,
                headers=REQUEST_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            latency = int(response.elapsed.total_seconds() * 1000)

            if 200 <= response.status_code < 400:
                class_type = "online"
                status_text = f"ONLINE ({response.status_code})"
            else:
                class_type = "issue"
                status_text = f"ISSUE ({response.status_code})"

            return {
                "url": url,
                "status_text": status_text,
                "class_type": class_type,
                "latency": latency,
                "status_code": response.status_code,
                "error": None,
            }
        except requests.exceptions.RequestException as error:
            last_error = error.__class__.__name__.replace("Error", " error")
            if attempt == MAX_RETRIES:
                break

    return {
        "url": url,
        "status_text": "DOWN",
        "class_type": "down",
        "latency": None,
        "status_code": None,
        "error": last_error,
    }


def get_status_data():
    with ThreadPoolExecutor(max_workers=len(SITES_TO_CHECK)) as executor:
        results = list(executor.map(check_site, SITES_TO_CHECK))

    return {
        "sites": results,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "online": sum(site["class_type"] == "online" for site in results),
            "issue": sum(site["class_type"] == "issue" for site in results),
            "down": sum(site["class_type"] == "down" for site in results),
        },
    }

@app.route('/')
def home():
    status_data = get_status_data()
    return render_template(
        "index.html",
        sites_data=status_data["sites"],
        checked_at=status_data["checked_at"],
        summary=status_data["summary"],
    )


@app.get('/api/status')
def status_api():
    return jsonify(get_status_data())


@app.route('/offline')
def offline():
    return render_template('offline.html')


@app.errorhandler(404)
def page_not_found(error):
    return render_template('error.html', error_code=404, error_title='Page not found'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('error.html', error_code=500, error_title='Server error'), 500

if __name__ == '__main__':
    app.run(port=5000, debug=False)
