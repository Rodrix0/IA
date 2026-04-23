import httpx
import asyncio

async def test():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.sofascore.com/",
        "Origin": "https://www.sofascore.com"
    }
    client = httpx.AsyncClient(headers=headers)
    r = await client.get('https://api.sofascore.com/api/v1/search/all?q=boca&page=0')
    print(r.status_code, r.text)

asyncio.run(test())
