from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
import aiohttp
import urllib.parse
from bs4 import BeautifulSoup
import re
import json

# MCP - API
SERP_ZONE = "websearchserpapi"
UNLOCKER_ZONE = "web_unlocker1"
API_KEY = "4d14d08a741cced6900c019181da67017ea84ac99bcfaea871ae230c555193de"  # Replace with your actual key

SERP_ENDPOINT = "https://api.brightdata.com/request"
SCRAPER_ENDPOINT = "https://api.brightdata.com/request"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Initialize FastAPI app
app = FastAPI()

# Pydantic model for input parameters
class InputParameters(BaseModel):
    query: str

# MCP Tool: Search & Scrape logic
async def extract_links_from_serp(session, query, max_results=5):
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num={max_results}"
    data = {
        "zone": SERP_ZONE,
        "url": url,
        "format": "raw"
    }
    async with session.post(SERP_ENDPOINT, headers=HEADERS, json=data) as response:
        html = await response.text()
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for h3 in soup.find_all("h3"):
            title = h3.get_text(strip=True)
            a_tag = h3.find_parent("a")
            if a_tag and a_tag.get("href"):
                href = a_tag["href"]
                if href.startswith("/url?q="):
                    href = href.split("/url?q=")[1].split("&")[0]
                links.append({"title": title, "url": href})
        return links

async def scrape_url(session, title, url):
    data = {
        "zone": UNLOCKER_ZONE,
        "url": url,
        "format": "raw"
    }
    try:
        async with session.post(SCRAPER_ENDPOINT, headers=HEADERS, json=data) as response:
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            text = soup.get_text()
            text = re.sub(r"\s+", " ", text).strip()
            return {
                "title": title,
                "url": url,
                "scraped_content": {"content": text[:2000]},
                "status": "success"
            }
    except Exception as e:
        return {
            "title": title,
            "url": url,
            "scraped_content": {"content": f"Scrape error: {str(e)}"},
            "status": "error"
        }

# FastAPI endpoint for MCP call
@app.post("/invoke")
async def invoke_tool(input_parameters: InputParameters):
    query = input_parameters.query
    print(f"🔍 Searching for: {query}")
    
    async with aiohttp.ClientSession() as session:
        # Extract links from search
        links = await extract_links_from_serp(session, query)
        print(f"🔗 Found {len(links)} links")

        # Scrape the URLs
        tasks = [scrape_url(session, item["title"], item["url"]) for item in links]
        results = await asyncio.gather(*tasks)

    # Prepare final data to return
    final_data = {
        "outputParameters": {
            "results": results
        }
    }
    
    return final_data
