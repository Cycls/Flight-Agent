import cycls
import os
import json
import requests
from typing import Dict, List
from openai import OpenAI
import dotenv
from datetime import datetime, timedelta
dotenv.load_dotenv()
CYCLS_API_KEY = os.getenv("CYCLS_API_KEY")
agent = cycls.Agent(api_key=CYCLS_API_KEY, pip=["requests", "openai", "python-dotenv"], copy=[".env"])

DUFFEL_BASE_URL = "https://api.duffel.com"

def duffel_request(endpoint: str, method: str = "GET", payload: Dict = None) -> Dict:
    headers = {"Authorization": f"Bearer {os.getenv('DUFFEL_API_KEY')}","Content-Type": "application/json","Duffel-Version": "v2"}
    try:
        if method == "POST":
            r = requests.post(f"{DUFFEL_BASE_URL}/{endpoint}", headers=headers, json=payload, timeout=30)
        else:
            r = requests.get(f"{DUFFEL_BASE_URL}/{endpoint}", headers=headers, timeout=30)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def search_flights(origin: str, destination: str, departure_date: str, passengers: int = 1) -> str:
    payload = {
        "data": {"slices": [{"origin": origin, "destination": destination, "departure_date": departure_date}],"passengers": [{"type": "adult"}] * passengers,"cabin_class": "economy"}}
    result = duffel_request("air/offer_requests", "POST", payload)
    if "error" in result or "errors" in result:
        errors = result.get('errors', [result.get('error')])
        if isinstance(errors, list) and len(errors) > 0:
            error_msg = errors[0].get('message', str(errors[0])) if isinstance(errors[0], dict) else str(errors[0])
            if 'must be after' in error_msg:
                return "❌ Sorry, the departure date must be in the future. Please choose a date starting from tomorrow or later."
            return f"❌ {error_msg}"
        return f"❌ Error: {errors}"
    
    offers = result.get("data", {}).get("offers", [])[:5]
    if not offers:
        return "No flights found for your search criteria."

    flight_list = f"✈️ **Top {len(offers)} Flights from {origin} to {destination}**\n\n"
    for i, offer in enumerate(offers, 1):
        airline = offer["owner"]["name"]
        price = f"{offer['total_amount']} {offer['total_currency']}"
        duration = offer["slices"][0]["duration"]
        stops = len(offer["slices"][0].get("segments", [{}])) - 1
        flight_list += f"{i}. **{airline}** - {price} | Duration: {duration} | Stops: {stops}\n"  
    return flight_list
@agent()
async def flight_agent(context):
    import os
    from openai import OpenAI
    import dotenv
    from datetime import datetime, timedelta 
    dotenv.load_dotenv()
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  
    today = datetime.now()
    tomorrow = today + timedelta(days=1)  
    messages = [{"role": "system", "content": f"""You are a helpful flight booking assistant.
Your job is to help users find and book flights.
- Greet users warmly and ask how you can help with their travel plans
- When they want to search flights, ask for: origin, destination, and departure date
- IMPORTANT: Today is {today.strftime('%Y-%m-%d')}. When user says "tomorrow", use {tomorrow.strftime('%Y-%m-%d')}
- Departure dates must be {tomorrow.strftime('%Y-%m-%d')} or later (no same-day bookings)
- Once you have all details, use the search_flights tool
- Present results clearly and help them choose
- Be conversational and friendly throughout"""}]
    messages.extend([{"role": msg["role"], "content": msg["content"]} for msg in context.messages])  
    tools = [{"type": "function", "function": {
        "name": "search_flights",
        "description": "Search for flights between two airports on a specific date",
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {"type": "string", "description": "Origin airport code (e.g., 'JFK', 'CAI')"},
                "destination": {"type": "string", "description": "Destination airport code (e.g., 'LAX', 'JFK')"},
                "departure_date": {"type": "string", "description": "Date in YYYY-MM-DD format (must be tomorrow or later)"},
                "passengers": {"type": "integer", "description": "Number of passengers", "default": 1}
            },
            "required": ["origin", "destination", "departure_date"]
        }
    }}]
    completion = openai_client.chat.completions.create(
        model="gpt-4o", messages=messages, tools=tools, tool_choice="auto", temperature=0.7
    )
    response_msg = completion.choices[0].message
    if response_msg.tool_calls:
        args = json.loads(response_msg.tool_calls[0].function.arguments)
        flight_results = search_flights(args["origin"], args["destination"], args["departure_date"], args.get("passengers", 1))
        return flight_results   
    return response_msg.content

agent.cycls(prod=True)
