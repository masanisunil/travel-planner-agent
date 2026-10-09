import os
from dotenv import load_dotenv
import requests

load_dotenv()

AVIATION_STACK_API_KEY = os.getenv("AVIATION_STACK_API_KEY")

def search_flight(query):
    url="https://api.aviationstack.com/v1/flights"
    params={
        "access_key": AVIATION_STACK_API_KEY,
        "limit":5


    }

    response=requests.get(url,params=params,timeout=20)
    response.raise_for_status()

    data=response.json()
    if not isinstance(data,dict):
        raise ValueError("Flight provider returned an invalid response.")
    if "error" in data:
        raise RuntimeError("Flight provider rejected the request. Check the API key and provider limits.")

    flights=[]
    if "data" in data:
        for flight in data["data"][:5]:
            airline=(flight.get("airline") or {}).get("name","Unknown")
            departure=(flight.get("departure") or {}).get("airport","Unknown")
            arrival=(flight.get("arrival") or {}).get("airport","Unknown")
            status=flight.get("flight_status","Unknown")
            flights.append(f"{airline}: {departure} -> {arrival} ({status})")

    return "\n".join(flights)





