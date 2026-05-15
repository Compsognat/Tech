import threading
import requests
from bs4 import BeautifulSoup
import re
import csv
import time
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

BASE_URL = "https://stopgame.ru/games/catalog"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

MONTHS = {
    "января": "01",
    "февраля": "02",
    "марта": "03",
    "апреля": "04",
    "мая": "05",
    "июня": "06",
    "июля": "07",
    "августа": "08",
    "сентября": "09",
    "октября": "10",
    "ноября": "11",
    "декабря": "12"
}


class MainWindow(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title("Парсер StopGame")
        self.geometry("700x500")

        self.button = tk.Button(
            self,
            text="Запустить",
            command=self.start_parser
        )

        self.button.pack(pady=10)

        self.logs = ScrolledText(self)
        self.logs.pack(fill="both", expand=True)

    def log(self, text):
        self.logs.insert(tk.END, text + "\n")
        self.logs.see(tk.END)

    def start_parser(self):
        self.button.config(state="disabled")

        thread = threading.Thread(target=self.run_parser)
        thread.daemon = True
        thread.start()

    def run_parser(self):

        session = requests.Session()
        session.headers.update(HEADERS)

        fieldnames = [
            "title",
            "rating",
            "release",
            "developer",
            "genre"
        ]

        with open(
            "games.csv",
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames
            )

            writer.writeheader()

            links = self.get_game_links(
                session,
                limit=100
            )

            total = len(links)

            for i, link in enumerate(links, 1):

                self.log(f"{i}/{total}")

                try:
                    data = self.parse_game(
                        session,
                        link
                    )

                    writer.writerow(data)

                    self.log(
                        f"✅ {data['title']} "
                        f"| {data['rating']}"
                    )

                except Exception as e:

                    self.log(f"❌ {e}")

                time.sleep(0.3)

        self.log("ГОТОВО")

        self.button.config(state="normal")

    def get_game_links(self, session, limit=100):

        page = 1
        links = set()

        while len(links) < limit:

            try:

                url = f"{BASE_URL}?p={page}"

                self.log(f"📄 Страница {page}")

                r = session.get(
                    url,
                    timeout=10
                )

                soup = BeautifulSoup(
                    r.text,
                    "html.parser"
                )

                cards = soup.select(
                    "a[data-game-card]"
                )

                if not cards:
                    break

                for c in cards:

                    href = c.get("href")

                    if href:
                        links.add(
                            "https://stopgame.ru" + href
                        )

                self.log(
                    f"Ссылок: {len(links)}"
                )

                page += 1

                time.sleep(1)

            except Exception as e:

                self.log(f"Ошибка страницы: {e}")

        return list(links)[:limit]

    def parse_game(self, session, url):

        r = session.get(
            url,
            timeout=10
        )

        soup = BeautifulSoup(
            r.text,
            "html.parser"
        )

        title = ""

        h1 = soup.find("h1")

        if h1:
            title = h1.get_text(strip=True)

        genres = []

        if h1:

            sibling = h1.find_next_sibling()

            if sibling:

                for a in sibling.find_all(
                    "a",
                    href=True
                ):

                    href = a["href"]

                    if re.search(
                        r"/games/[^/]+$",
                        href
                    ):

                        genres.append(
                            a.get_text(strip=True)
                        )

        rating = 0.0

        btn = soup.find(
            "button",
            class_=lambda c: c and "_rating_" in c
        )

        if btn:

            try:

                rating = float(
                    btn.get_text(strip=True)
                    .replace(",", ".")
                )

            except:
                pass

        def get_dd(label):

            for dt in soup.find_all("dt"):

                if label in dt.get_text():

                    dd = dt.find_next_sibling("dd")

                    if dd:

                        return dd.get_text(
                            " ",
                            strip=True
                        )

            return ""

        release_date = ""

        raw_date = get_dd("Дата выхода")

        match = re.search(
            r"(\\d{1,2})\\s+([а-яА-Я]+)\\s+(\\d{4})",
            raw_date
        )

        if match:

            d, m, y = match.groups()

            release_date = (
                f"{d.zfill(2)}."
                f"{MONTHS.get(m, '01')}."
                f"{y}"
            )

        return {
            "title": title,
            "rating": rating,
            "release": release_date,
            "developer": get_dd("Разработчик"),
            "genre": ", ".join(genres),
        }


if __name__ == "__main__":

    app = MainWindow()

    app.mainloop()
