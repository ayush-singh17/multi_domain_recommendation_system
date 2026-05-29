import requests


def get_journal_link(journal_title):

    url = f"https://api.openalex.org/sources?search={journal_title}"

    try:
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()

        results = data.get("results", [])

        if len(results) == 0:
            return None

        homepage = results[0].get("homepage_url")

        return homepage

    except Exception as e:
        print("Error fetching link:", e)
        return None