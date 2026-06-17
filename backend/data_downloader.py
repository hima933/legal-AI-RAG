import requests
from bs4 import BeautifulSoup
import os

DATA_DIR = "data"

os.makedirs(DATA_DIR, exist_ok=True)


def download_text_from_url(url, filename):
    print(f"Downloading: {url}")

    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # remove scripts
    for script in soup(["script", "style"]):
        script.extract()

    text = soup.get_text(separator=" ")
    text = " ".join(text.split())

    path = os.path.join(DATA_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"Saved: {filename}")


def main():

    # IPC sample source
    download_text_from_url(
        "https://indiankanoon.org/doc/1569250/",
        "ipc_sections.txt"
    )

    # Constitution
    download_text_from_url(
        "https://indiankanoon.org/doc/367586/",
        "constitutional_articles.txt"
    )

    # Contract Act
    download_text_from_url(
        "https://indiankanoon.org/doc/1211281/",
        "contract_act.txt"
    )

    # CrPC
    download_text_from_url(
        "https://indiankanoon.org/doc/876544/",
        "criminal_procedure.txt"
    )


if __name__ == "__main__":
    main()