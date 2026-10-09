import os 
from dotenv import load_dotenv
import requests
from tavily import TavilyClient

load_dotenv()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

client=TavilyClient(api_key=TAVILY_API_KEY,timeout=20)


def tavily_search(query):
    response=client.search(
        query=query,
        max_results=5
    )

    result=[]

    for i,r in enumerate(response["results"],1):
        title=r.get("title","unknown")
        url=r.get("url","unknown")
        snippet=r.get('content',"").strip()
        if len(snippet) > 300:
            snippet=snippet[:300].rsplit(" ",1)[0]+".."
        result.append(f"{i}. {title}\n{url}\n{snippet}\n")

    return "\n".join(result)

