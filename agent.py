import cycls
import os
import requests
import urllib.parse
from openai import OpenAI
import dotenv
from datetime import datetime, timedelta
from ui import header, intro

dotenv.load_dotenv()
CYCLS_KEY_1 = os.getenv("CYCLS_KEY_1")
CYCLS_KEY_2 = os.getenv("CYCLS_KEY_2")

agent = cycls.Agent(keys=[CYCLS_KEY_1, CYCLS_KEY_2], pip=["requests", "openai", "python-dotenv"], copy=[".env"])

def duffel_request(endpoint: str, method: str = "GET", payload: dict = None) -> dict:
    headers = {"Authorization": f"Bearer {os.getenv('DUFFEL_API_KEY')}", "Content-Type": "application/json", "Duffel-Version": "v2"}
    try:
        r = requests.post(f"https://api.duffel.com/{endpoint}", headers=headers, json=payload, timeout=30) if method == "POST" else requests.get(f"https://api.duffel.com/{endpoint}", headers=headers, timeout=30)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def search_flights(origin: str, destination: str, departure_date: str, passengers: int = 1):
    result = duffel_request("air/offer_requests", "POST", {"data": {"slices": [{"origin": origin, "destination": destination, "departure_date": departure_date}], "passengers": [{"type": "adult"}] * passengers, "cabin_class": "economy"}}) 
    if "error" in result or "errors" in result:
        errors = result.get('errors', [result.get('error')])
        if isinstance(errors, list) and len(errors) > 0:
            error_msg = errors[0].get('message', str(errors[0])) if isinstance(errors[0], dict) else str(errors[0])
            return {"success": False, "error": "❌ Sorry, the departure date must be in the future. Please choose a date starting from tomorrow or later."} if 'must be after' in error_msg else {"success": False, "error": f"❌ {error_msg}"}
        return {"success": False, "error": f"❌ Error: {errors}"}
    offers = result.get("data", {}).get("offers", [])[:5]
    if not offers:
        return {"success": False, "error": "No flights found for your search criteria."}
    
    flights_data = [{"offer_id": offer.get("id", ""), "airline": offer["owner"]["name"], "price": f"{offer['total_amount']} {offer['total_currency']}", "duration": offer["slices"][0]["duration"], "stops": len(offer["slices"][0].get("segments", [{}])) - 1, "departure": offer["slices"][0]["segments"][0].get("departing_at", "N/A").split("T")[1][:5] if "T" in offer["slices"][0]["segments"][0].get("departing_at", "") else "N/A", "arrival": offer["slices"][0]["segments"][-1].get("arriving_at", "N/A").split("T")[1][:5] if "T" in offer["slices"][0]["segments"][-1].get("arriving_at", "") else "N/A"} for offer in offers]
    
    return {"success": True, "flights": flights_data, "origin": origin, "destination": destination}
@agent("flight-agent",header=header, intro=intro)
async def flight_agent(context):
    import os
    from openai import OpenAI
    import dotenv
    from datetime import datetime, timedelta
    import json
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
- If user clicks "Book Flight X", acknowledge the selection and proceed with booking confirmation
- Ask for passenger details: full name, email, phone number
- Confirm the booking details before finalizing
- Be conversational and friendly throughout"""}]
    messages.extend([{"role": msg["role"], "content": msg["content"]} for msg in context.messages])
    
    completion = openai_client.chat.completions.create(model="gpt-4o", messages=messages, tools=[{"type": "function", "function": {"name": "search_flights", "description": "Search for flights between two airports on a specific date", "parameters": {"type": "object", "properties": {"origin": {"type": "string", "description": "Origin airport code (e.g., 'JFK', 'CAI')"}, "destination": {"type": "string", "description": "Destination airport code (e.g., 'LAX', 'JFK')"}, "departure_date": {"type": "string", "description": "Date in YYYY-MM-DD format (must be tomorrow or later)"}, "passengers": {"type": "integer", "description": "Number of passengers", "default": 1}}, "required": ["origin", "destination", "departure_date"]}}}], tool_choice="auto", temperature=0.7)
    response_msg = completion.choices[0].message
    
    if response_msg.tool_calls:
        for tool_call in response_msg.tool_calls:
            if tool_call.function.name == "search_flights":
                args = json.loads(tool_call.function.arguments)
                result = search_flights(origin=args.get("origin"), destination=args.get("destination"), departure_date=args.get("departure_date"), passengers=args.get("passengers", 1))
                
                if result.get("success"):
                    flights = result.get("flights", [])
                    origin = result.get("origin")
                    destination = result.get("destination")
                    all_cards = f'<dev><div style="max-width:1200px;margin:0 auto;padding:20px;"><h2 style="text-align:center;color:#1f2937;font-size:24px;font-weight:700;margin-bottom:24px;">✈️ Found {len(flights)} flights from {origin} to {destination}</h2>'
                    
                    for idx, flight in enumerate(flights, 1):
                        price_parts = flight['price'].split()
                        price_amount = price_parts[0]
                        price_currency = price_parts[1] if len(price_parts) > 1 else ''
                        stops_text = 'Direct' if flight['stops'] == 0 else f"{flight['stops']} Stop{'s' if flight['stops'] > 1 else ''}"
                        stops_color = '#0d9488' if flight['stops'] == 0 else '#ea580c'
                        stop_indicator = '' if flight['stops'] == 0 else f'<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:8px;height:8px;background:{stops_color};border-radius:50%;"></div>'
                        offer_id = flight.get('offer_id', '')
                        airline = flight['airline']
                        booking_message = f'Book Flight {idx}: {airline} from {origin} to {destination} at {price_amount} {price_currency}'
                        booking_url = f"https://cycls.com/send/{urllib.parse.quote(booking_message)}"
                        all_cards += f'<div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:16px;box-shadow:0 10px 30px rgba(0,0,0,0.3);overflow:hidden;margin-bottom:20px;transition:transform 0.3s,box-shadow 0.3s;"><div style="display:grid;grid-template-columns:1fr;"><div style="padding:24px;color:white;"><div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid rgba(255,255,255,0.2);"><div style="background:rgba(255,255,255,0.15);padding:8px;border-radius:8px;"><svg style="width:20px;height:20px;color:white;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg></div><div style="flex:1;"><h3 style="font-weight:700;font-size:18px;margin:0;">{flight["airline"]}</h3><p style="font-size:11px;color:rgba(255,255,255,0.7);margin:2px 0 0 0;">Flight {idx} • Offer ID: {offer_id[:8]}...</p></div><span style="margin-left:auto;background:{stops_color};color:white;font-size:11px;font-weight:600;padding:4px 12px;border-radius:12px;">{stops_text}</span></div><div style="display:flex;align-items:center;justify-content:space-between;"><div style="text-align:center;flex:1;"><span style="font-weight:700;font-size:28px;display:block;margin-bottom:4px;">{flight["departure"]}</span><span style="color:rgba(255,255,255,0.8);font-size:13px;display:block;">{origin}</span><span style="font-size:10px;color:rgba(255,255,255,0.6);display:block;margin-top:4px;">Departure</span></div><div style="display:flex;flex-direction:column;align-items:center;margin:0 16px;flex:1;"><span style="color:rgba(255,255,255,0.8);font-size:11px;margin-bottom:8px;">{flight["duration"]}</span><div style="position:relative;width:120px;"><div style="border-top:2px solid rgba(255,255,255,0.5);width:100%;"></div>{stop_indicator}</div><span style="font-size:10px;color:rgba(255,255,255,0.6);margin-top:8px;"><svg style="width:14px;height:14px;display:inline;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg></span></div><div style="text-align:center;flex:1;"><span style="font-weight:700;font-size:28px;display:block;margin-bottom:4px;">{flight["arrival"]}</span><span style="color:rgba(255,255,255,0.8);font-size:13px;display:block;">{destination}</span><span style="font-size:10px;color:rgba(255,255,255,0.6);display:block;margin-top:4px;">Arrival</span></div></div><div style="display:flex;flex-wrap:wrap;gap:12px;margin-top:16px;padding-top:12px;border-top:1px solid rgba(255,255,255,0.2);font-size:11px;color:rgba(255,255,255,0.8);"><div style="display:flex;align-items:center;gap:4px;"><svg style="width:12px;height:12px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg><span>Economy</span></div><div style="display:flex;align-items:center;gap:4px;"><svg style="width:12px;height:12px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"></path></svg><span>23kg Baggage</span></div></div><div style="background:rgba(0,0,0,0.2);padding:20px;display:flex;flex-direction:column;align-items:center;border-radius:12px;margin-top:20px;"><span style="color:rgba(255,255,255,0.8);font-size:13px;margin-bottom:8px;">Price per person</span><span style="font-size:32px;font-weight:700;color:white;margin-bottom:4px;">{price_amount}</span><span style="color:rgba(255,255,255,0.8);font-size:13px;margin-bottom:16px;">{price_currency}</span><a href="{booking_url}" style="background:#10b981;color:white;font-weight:600;padding:12px 24px;border-radius:8px;text-decoration:none;text-align:center;display:block;width:100%;transition:all 0.3s;box-sizing:border-box;" onmouseover="this.style.background=\'#059669\';this.style.transform=\'scale(1.02)\';" onmouseout="this.style.background=\'#10b981\';this.style.transform=\'scale(1)\';">Select Flight →</a><p style="font-size:10px;color:rgba(255,255,255,0.6);margin-top:12px;margin-bottom:0;">Click to complete booking • Taxes included</p></div></div></div></div>'
                    
                    all_cards += '<div style="text-align:center;color:#6b7280;font-size:14px;margin-top:24px;padding-top:24px;border-top:1px solid #e5e7eb;">💳 All prices include taxes and fees • 📞 24/7 Customer support available</div></div></dev>'
                    return all_cards
                else:
                    return f"<div style='padding: 20px; color: red; background: #fee; border-radius: 8px; font-family: sans-serif;'>{result.get('error')}</div>"
    
    return response_msg.content or "Hello! I'm your flight booking assistant. Where would you like to fly today?"
    
agent.push(prod=True)

