from json import load
from asyncio import run
from random import choice
from os import path, listdir
from argparse import ArgumentParser

from http.cookiejar import MozillaCookieJar
from playwright.async_api import async_playwright


def load_cookies(path: str) -> list:
    jar = MozillaCookieJar(path)
    jar.load(ignore_discard=True, ignore_expires=True)
    return [
        {
            "name": c.name,
            "value": c.value,
            "domain": c.domain,
            "path": c.path,
            "secure": c.secure,
        }
        for c in jar
    ]


async def get_pins(username: str, board: str):

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        await context.add_cookies(load_cookies("cookies.txt"))

        page = await context.new_page()

        seen = set()
        all_pins = []

        async def gather_pins(response):
            if "BoardFeedResource/get" not in response.url:
                return
            
            try:
                body = await response.json()
                for pin in body.get("resource_response", {}).get("data", []):
                    pid = pin.get("id")

                    if pid and pid not in seen:
                        seen.add(pid)
                        all_pins.append(pin)

            except Exception as e:
                print(f"[warn] gather_pins: {e}")

        page.on("response", gather_pins)

        await page.goto(
            f"https://pinterest.com/{username}/{board}/",
            wait_until="domcontentloaded",
            timeout=30000,
        )

        await page.wait_for_timeout(5000)

        prev_count = 0

        for _ in range(20):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(3000)
            
            if len(all_pins) == prev_count and prev_count > 0:
                break

            prev_count = len(all_pins)

        await browser.close()

    urls = []

    for pin in all_pins:
        u = (
            pin.get("images", {}).get("orig", {}).get("url")
            or pin.get("images", {}).get("564x", {}).get("url")
        )

        if u:
            urls.append(u)

    return list(set(urls))


def get_image_urls(board: str):
    meta_path = path.join("dump", board, "metadata")
    urls = []

    for fname in listdir(meta_path):
        with open(path.join(meta_path, fname), encoding="utf-8") as f:
            data = load(f)

            if data.get("image"):
                urls.append(data["image"])

    return urls

if __name__ == "__main__":
    parser = ArgumentParser()

    parser.add_argument("--name", required=True)
    parser.add_argument("--board", required=True)
    parser.add_argument("--all", action="store_true")

    args = parser.parse_args()

    meta_path = path.join("dump", args.board, "metadata")
    
    if path.isdir(meta_path) and listdir(meta_path):
        urls = get_image_urls(args.board)

    else:
        urls = run(get_pins(args.name, args.board))

    if not urls:
        print("no urls found")

    elif args.all:
        for u in urls:
            print(u)

    else:
        print(choice(urls))