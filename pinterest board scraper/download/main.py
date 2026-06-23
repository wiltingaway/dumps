from json import dump
from os import makedirs
from asyncio import gather, run
from argparse import ArgumentParser
from os.path import exists, join, splitext

from curl_cffi.requests import AsyncSession
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
            "secure": c.secure
        }
        for c in jar
    ]


def extract_pin(pin: dict) -> dict:
    pid = pin.get("id")

    return {
        "id": pid,
        "title": pin.get("title") or pin.get("description", ""),
        "description": pin.get("description", ""),
        "link": pin.get("link"),
        "domain": pin.get("domain"),
        "image": (
            pin.get("images", {}).get("orig", {}).get("url")
            or pin.get("images", {}).get("564x", {}).get("url")
        ),
        "pin_url": f"https://www.pinterest.com/pin/{pid}/" if pid else "",
    }


async def download_one(session: AsyncSession, pin: dict, img_dir: str) -> int:
    pid = pin.get("id")

    img_url = (
        pin.get("images", {}).get("orig", {}).get("url")
        or pin.get("images", {}).get("564x", {}).get("url")
    )

    if not img_url or not pid:
        return 0

    ext = splitext(img_url.split("?")[0])[1] or ".jpg"
    fpath = join(img_dir, f"{pid}{ext}")

    if exists(fpath):
        return 0

    try:
        resp = await session.get(img_url)

        if resp.status_code == 200:
            with open(fpath, "wb") as f:
                f.write(resp.content)

            return 1
        
    except Exception as e:
        print(f"[warn] {pid}: {e}")

    return 0


async def scrape_board(username: str, board: str):

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

    meta_dir = join("dump", board, "metadata")
    img_dir = join("dump", board, "images")

    makedirs(meta_dir, exist_ok=True)
    makedirs(img_dir, exist_ok=True)

    for pin in all_pins:
        pid = pin.get("id")

        with open(join(meta_dir, f"{pid}.json"), "w", encoding="utf-8") as f:
            dump(extract_pin(pin), f, indent=2, ensure_ascii=False)

    async with AsyncSession(impersonate="chrome") as session:
        tasks = [download_one(session, pin, img_dir) for pin in all_pins]
        results = await gather(*tasks)
        downloaded = sum(results)

    print(f"dumped {len(all_pins)} metadata files to {meta_dir}/")
    print(f"downloaded {downloaded} to {img_dir}/")


if __name__ == "__main__":
    parser = ArgumentParser()
    
    parser.add_argument("--name", required=True)
    parser.add_argument("--board", required=True)

    args = parser.parse_args()

    run(scrape_board(args.name, args.board))