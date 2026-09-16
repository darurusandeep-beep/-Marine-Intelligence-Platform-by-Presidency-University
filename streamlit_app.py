import streamlit as st
from groq import Groq
import requests
from datetime import datetime
import folium
from streamlit_folium import st_folium
from urllib.parse import quote
import random
import math
import re
import hashlib
import json
import os

# ====================== CONFIG ======================
try:
    GROQ_API_KEY = "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"
except:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    st.error("GROQ_API_KEY is not configured.")
    st.stop()

client = Groq(api_key=GROQ_API_KEY)

WHATSAPP_NUMBER = "919876543210"
PHONE_NUMBER = "+919876543210"

LOCATIONS = {
    "kochi": {"lat": 9.9312, "lon": 76.2673, "name": "Kochi", "harbour_name": "Cochin Fisheries Harbour", "harbour_lat": 9.9402, "harbour_lon": 76.2598, "coast": "west"},
    "cochin": {"lat": 9.9312, "lon": 76.2673, "name": "Kochi", "harbour_name": "Cochin Fisheries Harbour", "harbour_lat": 9.9402, "harbour_lon": 76.2598, "coast": "west"},
    "mumbai": {"lat": 19.0760, "lon": 72.8777, "name": "Mumbai", "harbour_name": "Sassoon Docks Harbour", "harbour_lat": 18.9167, "harbour_lon": 72.8258, "coast": "west"},
    "chennai": {"lat": 13.0827, "lon": 80.2707, "name": "Chennai", "harbour_name": "Kasimedu Fishing Harbour", "harbour_lat": 13.1250, "harbour_lon": 80.2985, "coast": "east"},
    "goa": {"lat": 15.2993, "lon": 74.1240, "name": "Goa", "harbour_name": "Mormugao / Betul Fishing Harbour", "harbour_lat": 15.4124, "harbour_lon": 73.8052, "coast": "west"},
    "visakhapatnam": {"lat": 17.6868, "lon": 83.2185, "name": "Visakhapatnam", "harbour_name": "Vizag Fishing Harbour", "harbour_lat": 17.6980, "harbour_lon": 83.2982, "coast": "east"},
    "mangalore": {"lat": 12.9141, "lon": 74.8560, "name": "Mangalore", "harbour_name": "Old Mangalore Bunder Port", "harbour_lat": 12.8584, "harbour_lon": 74.8351, "coast": "west"},
    "tuticorin": {"lat": 8.7642, "lon": 78.1348, "name": "Tuticorin", "harbour_name": "Thoothukudi Fishing Harbour", "harbour_lat": 8.8052, "harbour_lon": 78.1630, "coast": "east"},
    "pondicherry": {"lat": 11.9416, "lon": 79.8083, "name": "Pondicherry", "harbour_name": "Thengaithittu Fishing Harbour", "harbour_lat": 11.9168, "harbour_lon": 79.8251, "coast": "east"},
    "ratnagiri": {"lat": 16.9902, "lon": 73.3120, "name": "Ratnagiri", "harbour_name": "Mirkarwada Fishing Harbour", "harbour_lat": 16.9935, "harbour_lon": 73.2840, "coast": "west"},
}

MONITORED_LOCATIONS = ["Kochi", "Mumbai", "Chennai", "Mangalore", "Visakhapatnam"]

ROUTE_COLORS = {
    0: {"hex": "#00E5FF", "label": "Primary Route (Neon Cyan)"},
    1: {"hex": "#3B82F6", "label": "Secondary Route (Electric Blue)"},
    2: {"hex": "#F59E0B", "label": "Alternate Route (Amber Gold)"}
}

RE_GREETING = re.compile(r'\b(hi|hello|hey|heyy|greetings|namaste|namaskar|vanakkam|kem\s*cho|good\s*(morning|afternoon|evening|day)|kaise\s*ho|kya\s*haal|kese\s*ho|hi\s*there|hello\s*there)\b', re.IGNORECASE)
RE_IDENTITY = re.compile(r'\b(who are you|what is your name|kya ho tum|tum kaun ho|what can you do|your features|help me|what do you do|introduce yourself|tell me about yourself|how can you help)\b', re.IGNORECASE)
RE_GRATITUDE = re.compile(r'\b(thank\s*you|thanks|dhanyawad|shukriya|bye|goodbye|alvida|see you)\b', re.IGNORECASE)
RE_MARINE_CORE = re.compile(r'\b(sea|weather|wind|safe\w*|fish\w*|wave\w*|tide\w*|ocean|cyclon\w*|storm\w*|rain|boat|harbour|harbor|port|coast|pfz|navigation|direction\w*|route\w*|distance|samundar|mausam|hawa|machli)\b', re.IGNORECASE)
RE_ALERT = re.compile(r'\b(alert|alerts|warning|warnings|danger|dangerous|risk|risky|emergency|caution|advisory|advisories|chetaavani|chetavani|khatra|khatre)\b', re.IGNORECASE)

# ====================== VOICE TRANSCRIPTION ======================
def get_audio_filename_and_mime(audio_bytes, original_name=None, mime_type=None):
    if not audio_bytes or len(audio_bytes) < 4:
        return "voice_input.wav", "audio/wav"
    header = audio_bytes[:12]
    if header.startswith(b"\x1aE\xdf\xa3") or b"webm" in audio_bytes[:64].lower():
        return "voice_input.webm", "audio/webm"
    if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WAVE":
        return "voice_input.wav", "audio/wav"
    if header.startswith(b"OggS"):
        return "voice_input.ogg", "audio/ogg"
    if header.startswith(b"ID3") or header[:2] in [b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"]:
        return "voice_input.mp3", "audio/mpeg"
    if len(header) >= 8 and header[4:8] == b"ftyp":
        return "voice_input.mp4", "audio/mp4"
    return "voice_input.webm", "audio/webm"

def transcribe_voice_query(audio_bytes, language="English"):
    if not audio_bytes or len(audio_bytes) < 100:
        return None
    filename, mime_type = get_audio_filename_and_mime(audio_bytes)
    lang_code = "en" if language == "English" else "hi"
    for model_name in ["whisper-large-v3-turbo", "whisper-large-v3"]:
        try:
            transcription = client.audio.transcriptions.create(
                file=(filename, audio_bytes, mime_type),
                model=model_name,
                language=lang_code,
                temperature=0.0
            )
            text = transcription.text.strip()
            if text:
                return text
        except Exception:
            try:
                transcription = client.audio.transcriptions.create(
                    file=(filename, audio_bytes, mime_type),
                    model=model_name,
                    temperature=0.0
                )
                text = transcription.text.strip()
                if text:
                    return text
            except Exception:
                continue
    return None

# ====================== ENHANCED WEATHER AGENT ======================
@st.cache_data(ttl=180, show_spinner=False)
def weather_agent(lat, lon):
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "weather_code"],
            "hourly": ["wave_height", "wave_direction", "wave_period", "swell_wave_height"],
            "timezone": "Asia/Kolkata",
            "forecast_days": 1
        }
        response = requests.get(url, params=params, timeout=8)
        if response.status_code != 200:
            return {"status": "error", "message": f"API Error: {response.status_code}"}

        data = response.json()
        current = data.get("current", {})
        hourly = data.get("hourly", {})

        wind_speed = current.get("wind_speed_10m", 0) or 0
        wind_gusts = current.get("wind_gusts_10m", 0) or 0
        wave_height = hourly.get("wave_height", [None])[0] if hourly.get("wave_height") else None
        swell_height = hourly.get("swell_wave_height", [None])[0] if hourly.get("swell_wave_height") else None

        risk_score = 0
        if wind_speed >= 30 or wind_gusts >= 40:
            risk_score += 3
        elif wind_speed >= 20 or wind_gusts >= 28:
            risk_score += 2
        elif wind_speed >= 12:
            risk_score += 1

        if wave_height is not None:
            if wave_height >= 2.5:
                risk_score += 3
            elif wave_height >= 1.5:
                risk_score += 2
            elif wave_height >= 1.0:
                risk_score += 1

        if risk_score >= 4:
            safety_status, safety_color = "Not Safe", "red"
            safety_message = "Dangerous conditions. High wind/waves. Do NOT go to sea."
            prediction = "Rough sea expected. Stay in harbour."
        elif risk_score >= 2:
            safety_status, safety_color = "Moderately Safe", "orange"
            safety_message = "Exercise caution. Moderate wind or waves."
            prediction = "Manageable for experienced crews only."
        else:
            safety_status, safety_color = "Safe", "green"
            safety_message = "Sea conditions appear favourable for fishing."
            prediction = "Favourable conditions expected."

        return {
            "temperature": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "wind_speed": round(wind_speed, 1),
            "wind_gusts": round(wind_gusts, 1) if wind_gusts else None,
            "wind_direction": current.get("wind_direction_10m"),
            "wave_height": round(wave_height, 2) if wave_height is not None else None,
            "swell_height": round(swell_height, 2) if swell_height is not None else None,
            "safety_status": safety_status,
            "safety_color": safety_color,
            "safety_message": safety_message,
            "prediction": prediction,
            "status": "success"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@st.cache_data(ttl=300, show_spinner=False)
def cached_continuous_monitor():
    results = []
    for name in MONITORED_LOCATIONS:
        loc = next((val for val in LOCATIONS.values() if val["name"] == name), None)
        if not loc:
            continue
        weather = weather_agent(loc["lat"], loc["lon"])
        if weather.get("status") == "success":
            results.append({
                "name": name,
                "safety_status": weather["safety_status"],
                "safety_color": weather["safety_color"],
                "wind_speed": weather["wind_speed"],
                "temperature": weather["temperature"],
                "prediction": weather.get("prediction", "No prediction"),
                "lat": loc["lat"],
                "lon": loc["lon"]
            })
    return results

# ====================== ALERT AGENT ======================
def alert_agent(weather_info, location_name, language="English"):
    if not weather_info or weather_info.get("status") != "success":
        return {"status": "error", "level": "UNKNOWN", "title": "Alert Unavailable", "message": "Could not retrieve weather data.", "color": "#64748b", "icon": "❓", "action": "Please try again later.", "whatsapp_text": ""}

    wind = weather_info.get("wind_speed", 0)
    safety = weather_info.get("safety_status", "Safe")
    temp = weather_info.get("temperature", "--")

    if wind >= 30 or safety == "Not Safe":
        level, color, icon = "CRITICAL", "#DC2626", "🚨"
        title = f"CRITICAL ALERT — {location_name}" if language == "English" else f"गंभीर चेतावनी — {location_name}"
        message = f"High wind speed of **{wind} km/h**. Sea is dangerous. **Do NOT venture out.**" if language == "English" else f"**{wind} km/h** की तेज़ हवा। समुद्र खतरनाक है। **न जाएं।**"
        action = "Return to port immediately. Contact Coast Guard if needed." if language == "English" else "तुरंत बंदरगाह लौटें।"
    elif wind >= 20 or safety == "Moderately Safe":
        level, color, icon = "WARNING", "#F59E0B", "⚠️"
        title = f"WARNING — {location_name}" if language == "English" else f"चेतावनी — {location_name}"
        message = f"Moderate to strong winds of **{wind} km/h**. Exercise extreme caution." if language == "English" else f"**{wind} km/h** की हवा। सावधानी बरतें।"
        action = "Carry life jackets, GPS and VHF radio." if language == "English" else "लाइफ जैकेट और GPS साथ रखें।"
    elif wind >= 12:
        level, color, icon = "ADVISORY", "#3B82F6", "ℹ️"
        title = f"ADVISORY — {location_name}" if language == "English" else f"सलाह — {location_name}"
        message = f"Wind speed is **{wind} km/h**. Conditions manageable but stay alert." if language == "English" else f"हवा **{wind} km/h**। सतर्क रहें।"
        action = "Check latest forecast before departure." if language == "English" else "प्रस्थान से पहले पूर्वानुमान जांचें।"
    else:
        level, color, icon = "CLEAR", "#10B981", "✅"
        title = f"ALL CLEAR — {location_name}" if language == "English" else f"सभी ठीक — {location_name}"
        message = f"Favourable conditions. Wind **{wind} km/h**." if language == "English" else f"अनुकूल स्थितियाँ। हवा **{wind} km/h**।"
        action = "Have a safe and productive trip." if language == "English" else "सुरक्षित यात्रा हो।"

    whatsapp_text = f"🌊 MARINE ALERT — {location_name}\nLevel: {level}\nWind: {wind} km/h | Temp: {temp}°C\n{message.replace('**','')}\nAction: {action}\nTime: {datetime.now().strftime('%d %b %Y, %I:%M %p')}"

    return {
        "status": "success", "level": level, "title": title, "message": message,
        "color": color, "icon": icon, "action": action, "wind_speed": wind,
        "temperature": temp, "safety_status": safety, "location": location_name,
        "whatsapp_text": whatsapp_text, "timestamp": datetime.now().strftime("%d %b %Y, %I:%M %p")
    }

def generate_active_alerts(language="English"):
    active = []
    for name in MONITORED_LOCATIONS:
        loc = next((val for val in LOCATIONS.values() if val["name"] == name), None)
        if not loc:
            continue
        weather = weather_agent(loc["lat"], loc["lon"])
        if weather.get("status") == "success":
            alert = alert_agent(weather, name, language)
            if alert["level"] in ["CRITICAL", "WARNING", "ADVISORY"]:
                active.append(alert)
    priority = {"CRITICAL": 0, "WARNING": 1, "ADVISORY": 2}
    active.sort(key=lambda x: priority.get(x["level"], 99))
    return active

def render_alert_banner(alert_data):
    if not alert_data or alert_data.get("status") != "success":
        return
    level = alert_data["level"]
    color = alert_data["color"]
    icon = alert_data["icon"]
    if level == "CRITICAL":
        border, bg, pulse = f"3px solid {color}", "linear-gradient(135deg, #7f1d1d 0%, #450a0a 100%)", "animation: pulse 1.5s infinite;"
    elif level == "WARNING":
        border, bg, pulse = f"2px solid {color}", "linear-gradient(135deg, #78350f 0%, #451a03 100%)", ""
    else:
        border, bg, pulse = f"2px solid {color}", "linear-gradient(135deg, #1e3a8a 0%, #1e293b 100%)", ""

    html = f"""
    <style>@keyframes pulse {{0% {{box-shadow:0 0 0 0 rgba(220,38,38,0.7);}} 70% {{box-shadow:0 0 0 12px rgba(220,38,38,0);}} 100% {{box-shadow:0 0 0 0 rgba(220,38,38,0);}}}}</style>
    <div style="background:{bg}; border:{border}; border-radius:16px; padding:18px 20px; color:white; margin:12px 0 18px; {pulse}">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <div style="font-size:1.15rem; font-weight:700;">{icon} {alert_data['title']}</div>
            <div style="background:{color}; color:#000; font-weight:800; font-size:0.75rem; padding:3px 10px; border-radius:20px;">{level}</div>
        </div>
        <div style="font-size:0.95rem; line-height:1.45; margin-bottom:10px;">{alert_data['message']}</div>
        <div style="font-size:0.85rem; opacity:0.9; margin-bottom:6px;"><b>Recommended Action:</b> {alert_data['action']}</div>
        <div style="font-size:0.75rem; opacity:0.7;">💨 Wind: {alert_data['wind_speed']} km/h &nbsp;|&nbsp; 🌡️ {alert_data['temperature']}°C &nbsp;|&nbsp; 🕒 {alert_data['timestamp']}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_active_alerts_panel(language="English"):
    active = generate_active_alerts(language)
    if not active:
        st.success("✅ **No active marine alerts**. Conditions are currently favourable.")
        return
    st.markdown(f"### 🚨 Active Marine Alerts ({len(active)})")
    for alert in active:
        render_alert_banner(alert)
        st.link_button(f"📤 Share {alert['location']} Alert on WhatsApp", f"https://wa.me/?text={quote(alert['whatsapp_text'])}", use_container_width=False)
        st.markdown("<br>", unsafe_allow_html=True)

# ====================== NAVIGATION ======================
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a)), 2)

def calculate_bearing(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return round((math.degrees(math.atan2(x, y)) + 360) % 360, 1)

def bearing_to_compass(bearing):
    points = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return points[round(bearing / 22.5) % 16]

def generate_marine_route(origin_lat, origin_lon, dest_lat, dest_lon, harbour_name, dest_name, boat_speed_knots=10):
    dist_km = haversine_distance(origin_lat, origin_lon, dest_lat, dest_lon)
    dist_nm = round(dist_km / 1.852, 1)
    bearing = calculate_bearing(origin_lat, origin_lon, dest_lat, dest_lon)
    compass_dir = bearing_to_compass(bearing)
    speed_kmh = boat_speed_knots * 1.852
    travel_hours = dist_km / speed_kmh
    hours, minutes = int(travel_hours), int((travel_hours - int(travel_hours)) * 60)
    fuel_est_liters = round(dist_nm * 1.5, 1)

    wp1 = [origin_lat, origin_lon]
    wp2 = [round(origin_lat + (dest_lat - origin_lat)*0.25 + (0.01 if dest_lat > origin_lat else -0.01), 4),
           round(origin_lon + (dest_lon - origin_lon)*0.25, 4)]
    wp3 = [round(origin_lat + (dest_lat - origin_lat)*0.65, 4), round(origin_lon + (dest_lon - origin_lon)*0.65, 4)]
    wp4 = [dest_lat, dest_lon]

    steps = [
        {"step": 1, "title": f"Depart {harbour_name}", "coords": wp1, "instruction": f"Cast off. Steer {bearing}° ({compass_dir}).", "distance": f"{round(dist_km*0.25,1)} km"},
        {"step": 2, "title": "Clear Harbor Fairway", "coords": wp2, "instruction": f"Exit breakwater. Maintain heading {compass_dir}.", "distance": f"{round(dist_km*0.40,1)} km"},
        {"step": 3, "title": "Mid-Course Ocean Waypoint", "coords": wp3, "instruction": "Navigate deep coastal shelf. Monitor conditions.", "distance": f"{round(dist_km*0.35,1)} km"},
        {"step": 4, "title": f"Arrival: {dest_name}", "coords": wp4, "instruction": "Arrive at Potential Fishing Zone. Deploy gear.", "distance": "Destination Reached"}
    ]
    gmaps_url = f"https://www.google.com/maps/dir/?api=1&origin={origin_lat},{origin_lon}&destination={dest_lat},{dest_lon}&travelmode=driving"
    return {"distance_km": dist_km, "distance_nm": dist_nm, "bearing": bearing, "compass_dir": compass_dir,
            "eta": f"{hours}h {minutes}m", "fuel_l": fuel_est_liters, "waypoints": [wp1, wp2, wp3, wp4],
            "steps": steps, "gmaps_url": gmaps_url}

# ====================== NLP & RESPONSE ======================
def get_natural_greeting(language="English"):
    if language == "English":
        return "👋 **Hello! Welcome to the Marine Intelligence Platform.**\n\nI am your Marine AI Assistant. Ask about sea safety, weather, alerts or Potential Fishing Zones."
    return "👋 **नमस्ते! मरीन इंटेलिजेंस प्लेटफ़ॉर्म में आपका स्वागत है।**\n\nमैं आपका समुद्री एआई सहायक हूँ।"

def get_natural_identity(language="English"):
    if language == "English":
        return "🤖 **I am the Marine Intelligence Assistant.** I help with real-time safety, weather, alerts, PFZ and navigation for Indian fishermen."
    return "🤖 **मैं मरीन इंटेलिजेंस असिस्टेंट हूँ।** मैं भारतीय मछुआरों के लिए समुद्र सुरक्षा और मत्स्यन क्षेत्रों की जानकारी देता हूँ।"

def advanced_nlp_agent(user_query):
    query = user_query.lower().strip()
    detected_location = None
    for key, value in LOCATIONS.items():
        if re.search(r'\b' + re.escape(key) + r'\b', query):
            detected_location = value
            break
    has_greeting = bool(RE_GREETING.search(query))
    has_identity = bool(RE_IDENTITY.search(query))
    has_gratitude = bool(RE_GRATITUDE.search(query))
    has_marine = bool(RE_MARINE_CORE.search(query))
    has_alert = bool(RE_ALERT.search(query))

    if has_alert and not detected_location:
        intent = "SHOW_ALERTS"
    elif has_alert and detected_location:
        intent = "LOCATION_ALERT"
    elif detected_location and (has_marine or not has_greeting):
        intent = "MARINE_LOCATION"
    elif detected_location:
        intent = "MARINE_LOCATION"
    elif not detected_location and has_marine:
        intent = "LOCATION_AMBIGUOUS"
    elif has_identity:
        intent = "BOT_IDENTITY"
    elif has_gratitude:
        intent = "GRATITUDE"
    elif has_greeting:
        intent = "GREETING"
    else:
        intent = "NORMAL_CHAT"

    return {"intent": intent, "location": detected_location, "has_greeting": has_greeting,
            "needs_weather": intent in ["MARINE_LOCATION", "LOCATION_ALERT"],
            "needs_pfz": intent == "MARINE_LOCATION",
            "needs_alert": intent in ["SHOW_ALERTS", "LOCATION_ALERT", "MARINE_LOCATION"],
            "original_query": user_query}

def pfz_agent(location_info, weather_info=None):
    location_name = location_info["name"]
    base_lat = location_info.get("harbour_lat", location_info["lat"])
    base_lon = location_info.get("harbour_lon", location_info["lon"])
    coast = location_info.get("coast", "west")
    sst = round(random.uniform(27.8, 30.2), 1)
    chlorophyll = round(random.uniform(0.7, 1.8), 2)
    wind_speed = weather_info.get("wind_speed", 12) if weather_info else 14
    total_score = int((100 if 28 <= sst <= 29.5 else 70)*0.35 + min(100, int(chlorophyll*55))*0.40 + (100 if wind_speed < 15 else 60 if wind_speed < 25 else 20)*0.25)
    lon_dir = -1 if coast == "west" else 1
    offsets = [(0.04, lon_dir*0.17), (0.12, lon_dir*0.25), (-0.07, lon_dir*0.21)]
    base_zones = []
    types = ["Primary", "Secondary", "Alternate"]
    for i, (lat_off, lon_off) in enumerate(offsets):
        zone_lat = round(base_lat + lat_off, 4)
        zone_lon = round(base_lon + lon_off, 4)
        dist_km = haversine_distance(base_lat, base_lon, zone_lat, zone_lon)
        base_zones.append({
            "name": f"{types[i]} PFZ - {location_name}", "type": types[i],
            "distance_km": dist_km, "distance_nm": round(dist_km/1.852, 1),
            "distance": f"{dist_km} km ({round(dist_km/1.852,1)} NM)", "score": max(40, total_score - i*8),
            "lat": zone_lat, "lon": zone_lon, "sst": sst, "chlorophyll": chlorophyll,
            "color_hex": ROUTE_COLORS[i]["hex"]
        })
    return {
        "status": "success", "best_zone": base_zones[0], "all_zones": base_zones,
        "overall_score": total_score, "recommendation": "Highly Recommended" if base_zones[0]["score"] >= 75 else "Moderately Recommended",
        "sst": sst, "chlorophyll": chlorophyll,
        "harbour_name": location_info.get("harbour_name", f"{location_name} Port"),
        "harbour_lat": base_lat, "harbour_lon": base_lon
    }

def call_groq_llm(messages, max_tokens=350, temperature=0.3):
    for model_name in ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
        try:
            completion = client.chat.completions.create(messages=messages, model=model_name, max_tokens=max_tokens, temperature=temperature)
            raw = completion.choices[0].message.content or ""
            clean = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
            if clean:
                return clean
        except Exception:
            continue
    return None

def response_agent(user_query, nlp_plan, weather_info=None, pfz_info=None, alert_info=None, language="English"):
    intent = nlp_plan.get("intent", "NORMAL_CHAT")
    lang_inst = "Reply in clear English." if language == "English" else "Reply in clear Hindi."

    if intent == "GREETING":
        return get_natural_greeting(language)
    if intent == "BOT_IDENTITY":
        return get_natural_identity(language)
    if intent == "GRATITUDE":
        return "🙏 **You're very welcome! Stay safe on the waters!**" if language == "English" else "🙏 **आपका धन्यवाद! सुरक्षित रहें!**"
    if intent == "LOCATION_AMBIGUOUS":
        return "🌊 **Which coastal city are you asking about?** (Goa, Kochi, Mumbai, Chennai, Visakhapatnam...)" if language == "English" else "🌊 **किस तटीय शहर के बारे में पूछ रहे हैं?**"
    if intent == "SHOW_ALERTS":
        return "🚨 **Checking active marine alerts...** See the banners below." if language == "English" else "🚨 **सक्रिय अलर्ट जाँच रहा हूँ...**"

    loc = nlp_plan.get("location")
    if loc and weather_info:
        loc_name = loc.get("name", "Coastal Port")
        context = f"Location: {loc_name}\nWeather: Temp {weather_info.get('temperature')}°C | Wind {weather_info.get('wind_speed')} km/h | Status: {weather_info.get('safety_status')}\nAdvice: {weather_info.get('safety_message')}"
        if alert_info and alert_info.get("status") == "success":
            context += f"\nAlert: {alert_info.get('level')} - {alert_info.get('message')}"
        if pfz_info and pfz_info.get("status") == "success":
            context += f"\nBest PFZ: {pfz_info['best_zone']['name']} ({pfz_info['best_zone']['distance']})"
        system_prompt = f"You are Marine AI Assistant for Indian fishermen.\n{lang_inst}\nState Safety Status and Wind clearly. Emphasize CRITICAL/WARNING alerts. Be concise.\nData:\n{context}"
        response = call_groq_llm([{"role": "system", "content": system_prompt}, {"role": "user", "content": user_query}])
        if response:
            return response
        return f"📍 **{loc_name}**: {weather_info.get('safety_status')} | Wind {weather_info.get('wind_speed')} km/h | {weather_info.get('safety_message')}"

    system_prompt = f"You are Marine AI Assistant for Indian fishermen.\n{lang_inst}\nHelp with sea safety, weather, alerts and fishing zones."
    response = call_groq_llm([{"role": "system", "content": system_prompt}, {"role": "user", "content": user_query}], 250, 0.4)
    return response or "🌊 I am your Marine AI Assistant. Ask about sea safety, weather or fishing zones."

# ====================== RENDER HELPERS ======================
def clean_text_for_tts(text):
    if not text:
        return ""
    t = re.sub(r"```[\s\S]*?```", "", text)
    t = re.sub(r"`.*?`", "", t)
    t = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", t)
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"[\U00010000-\U0010ffff]", "", t)
    t = re.sub(r"[*_~#|>]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def render_tts_button(text_to_speak, language="English", auto_play=False, msg_id=None):
    speech_text = clean_text_for_tts(text_to_speak)
    if not speech_text:
        return
    text_json = json.dumps(speech_text, ensure_ascii=False)
    lang_code = "en-IN" if language == "English" else "hi-IN"
    uid = f"tts_{abs(hash(speech_text[:40]))}" if not msg_id else f"tts_{msg_id}"
    auto_trigger = f"setTimeout(function(){{ playTTS_{uid}(); }}, 400);" if auto_play else ""

    html = f"""
    <div style="margin-top:8px; display:flex; align-items:center; gap:8px;">
        <button id="btn_play_{uid}" onclick="playTTS_{uid}();" style="background:linear-gradient(135deg,#0284c7,#0369a1); color:white; border:none; border-radius:8px; padding:6px 14px; font-size:0.82rem; font-weight:600; cursor:pointer;">
            🔊 Listen ({language})
        </button>
        <button id="btn_stop_{uid}" onclick="stopTTS_{uid}();" style="display:none; background:#334155; color:#cbd5e1; border:none; border-radius:8px; padding:6px 12px; font-size:0.82rem; cursor:pointer;">⏹️ Stop</button>
    </div>
    <script>
    (function(){{
        var text = {text_json}; var lang = '{lang_code}'; var uid = '{uid}';
        window['playTTS_'+uid] = function(){{
            if(!('speechSynthesis' in window)) return;
            window.speechSynthesis.cancel();
            var u = new SpeechSynthesisUtterance(text); u.lang = lang; u.rate = 0.95;
            u.onstart = function(){{ document.getElementById('btn_stop_'+uid).style.display='inline-flex'; }};
            var reset = function(){{ document.getElementById('btn_stop_'+uid).style.display='none'; }};
            u.onend = reset; u.onerror = reset;
            window.speechSynthesis.speak(u);
        }};
        window['stopTTS_'+uid] = function(){{ window.speechSynthesis.cancel(); }};
        {auto_trigger}
    }})();
    </script>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_monitoring_dashboard(monitor_data):
    st.subheader("📡 Live Coastal Monitoring")
    if not monitor_data:
        st.warning("Monitoring temporarily unavailable.")
        return
    cols = st.columns(len(monitor_data))
    for idx, data in enumerate(monitor_data):
        with cols[idx]:
            st.markdown(f"""
            <div style="background:#0f172a; border-radius:12px; padding:12px; color:white; text-align:center; border:1px solid rgba(255,255,255,0.08);">
                <div style="font-weight:600;">{data['name']}</div>
                <div style="margin:6px 0; padding:3px 8px; background:{data['safety_color']}; border-radius:15px; display:inline-block; font-size:0.75rem; font-weight:700;">{data['safety_status']}</div>
                <div style="font-size:0.85rem;">💨 {data['wind_speed']} km/h</div>
                <div style="font-size:0.8rem; opacity:0.8;">🌡️ {data['temperature']}°C</div>
            </div>
            """, unsafe_allow_html=True)

def render_weather_card(weather_data, location_name):
    if not weather_data or weather_data.get("status") != "success":
        return
    safety_color_map = {"green": "#10B981", "orange": "#F59E0B", "red": "#EF4444"}
    accent = safety_color_map.get(weather_data.get("safety_color", "green"), "#3B82F6")
    wind_deg = weather_data.get("wind_direction", 0) or 0
    prediction = weather_data.get("prediction", "")
    prediction_html = f'<div style="text-align:center; font-size:0.88rem; color:#93c5fd; margin-bottom:10px;">🔮 {prediction}</div>' if prediction else ''

    wave_html = ""
    if weather_data.get("wave_height") is not None:
        wave_html = f'<div style="background:rgba(255,255,255,0.06); border-radius:10px; padding:10px 5px; text-align:center;"><div>🌊</div><div style="font-weight:600;">{weather_data.get("wave_height")} m</div><div style="font-size:0.65rem; opacity:0.7;">WAVE</div></div>'

    gust_html = ""
    if weather_data.get("wind_gusts") is not None:
        gust_html = f'<div style="background:rgba(255,255,255,0.06); border-radius:10px; padding:10px 5px; text-align:center;"><div>💨</div><div style="font-weight:600;">{weather_data.get("wind_gusts")}</div><div style="font-size:0.65rem; opacity:0.7;">GUSTS</div></div>'

    html = f"""
    <div style="background:linear-gradient(160deg,#0f172a,#1e293b); border-radius:20px; padding:20px; color:white; max-width:480px; margin:10px 0 15px; border:1px solid rgba(255,255,255,0.1);">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <div style="font-size:1.15rem; font-weight:600;">📍 {location_name}</div>
            <div style="background:{accent}; color:white; padding:4px 12px; border-radius:50px; font-size:0.75rem; font-weight:700;">{weather_data.get('safety_status')}</div>
        </div>
        <div style="text-align:center; margin:8px 0;"><span style="font-size:3.2rem; font-weight:300;">{weather_data.get('temperature','--')}</span><span style="font-size:1.4rem; opacity:0.7;">°C</span></div>
        <div style="text-align:center; font-size:0.9rem; opacity:0.9; margin-bottom:8px;">{weather_data.get('safety_message','')}</div>
        {prediction_html}
        <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(90px,1fr)); gap:8px;">
            <div style="background:rgba(255,255,255,0.06); border-radius:10px; padding:10px 5px; text-align:center;"><div>💨</div><div style="font-weight:600;">{weather_data.get('wind_speed','--')}</div><div style="font-size:0.65rem; opacity:0.7;">WIND</div></div>
            {gust_html}
            <div style="background:rgba(255,255,255,0.06); border-radius:10px; padding:10px 5px; text-align:center;"><div style="transform:rotate({wind_deg}deg);">➤</div><div style="font-weight:600;">{wind_deg}°</div><div style="font-size:0.65rem; opacity:0.7;">DIR</div></div>
            {wave_html}
            <div style="background:rgba(255,255,255,0.06); border-radius:10px; padding:10px 5px; text-align:center;"><div>💧</div><div style="font-weight:600;">{weather_data.get('humidity','--')}%</div><div style="font-size:0.65rem; opacity:0.7;">HUM</div></div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_pfz_section(pfz_data):
    if not pfz_data or pfz_data.get("status") != "success":
        return
    best = pfz_data["best_zone"]
    c1, c2 = st.columns([2, 1])
    with c1:
        st.success(f"🎯 **Best PFZ:** {best['name']} ({best['distance']})")
        st.caption(f"⚓ Port: {pfz_data.get('harbour_name')}")
    with c2:
        st.metric("PFZ Score", f"{best['score']}/100", pfz_data["recommendation"])
    st.caption(f"🌡️ SST: {pfz_data['sst']}°C | 🟢 Chlorophyll: {pfz_data['chlorophyll']} mg/m³")

# ====================== ADVANCED SOS WITH LIVE LOCATION ======================
def render_sos_button(location_name=None, lat=None, lon=None):
    """Advanced Emergency SOS with Live Location (Browser GPS)"""
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #7f1d1d 0%, #450a0a 100%);
                border: 3px solid #dc2626; border-radius: 16px; padding: 22px;
                color: white; margin-bottom: 25px; text-align: center;">
        <div style="font-size: 1.6rem; font-weight: 800; margin-bottom: 6px;">
            🆘 EMERGENCY SOS
        </div>
        <div style="font-size: 0.95rem; opacity: 0.9;">
            Immediate help + Live Location for emergency team
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ========== LIVE LOCATION SECTION ==========
    st.markdown("### 📍 Live Location")

    st.markdown("""
    <script>
    function getLiveLocation() {
        if (!navigator.geolocation) {
            alert("Geolocation is not supported by your browser");
            return;
        }
        
        const status = document.getElementById("location-status");
        status.innerHTML = "⏳ Getting your live location... Please wait";
        status.style.color = "#fbbf24";

        navigator.geolocation.getCurrentPosition(
            function(position) {
                const lat = position.coords.latitude.toFixed(6);
                const lon = position.coords.longitude.toFixed(6);
                const accuracy = Math.round(position.coords.accuracy);
                
                status.innerHTML = `✅ <b>Live Location Found</b><br>
                    <b>Latitude:</b> ${lat}<br>
                    <b>Longitude:</b> ${lon}<br>
                    <b>Accuracy:</b> ±${accuracy} meters`;
                status.style.color = "#4ade80";

                const mapsBtn = document.getElementById("live-maps-btn");
                if (mapsBtn) {
                    mapsBtn.href = `https://maps.google.com/?q=${lat},${lon}`;
                    mapsBtn.style.display = "block";
                }
            },
            function(error) {
                let message = "❌ Unable to get location. ";
                if (error.code === 1) message += "Please allow location permission in your browser.";
                else if (error.code === 2) message += "Location unavailable.";
                else if (error.code === 3) message += "Request timed out. Try again.";
                else message += "Unknown error occurred.";
                
                status.innerHTML = message;
                status.style.color = "#f87171";
            },
            {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 0
            }
        );
    }
    </script>
    """, unsafe_allow_html=True)

    st.markdown("""
    <button onclick="getLiveLocation()" 
            style="width:100%; padding:14px; background:linear-gradient(135deg,#2563eb,#1d4ed8);
                   color:white; border:none; border-radius:10px; font-size:1.05rem;
                   font-weight:700; cursor:pointer; margin-bottom:12px;">
        📍 Get My Live Location
    </button>
    
    <div id="location-status" style="background:#1e293b; padding:14px; border-radius:10px; 
                color:#94a3b8; margin-bottom:12px; text-align:center; min-height:60px;">
        Click the button above to get your real-time GPS location
    </div>

    <a id="live-maps-btn" href="#" target="_blank" style="display:none; text-decoration:none;">
        <div style="background:linear-gradient(135deg,#059669,#047857); color:white; 
                    padding:14px; border-radius:10px; text-align:center; font-weight:700;
                    margin-bottom:12px;">
            🗺️ Open Live Location in Google Maps
        </div>
    </a>
    """, unsafe_allow_html=True)

    st.caption("Allow location permission when your browser asks. This helps the emergency team find you faster.")

    # ========== LAST KNOWN LOCATION ==========
    if location_name or (lat and lon):
        st.markdown("### 📌 Last Queried Location")
        loc_text = f"<b>Area:</b> {location_name}" if location_name else ""
        if lat and lon:
            loc_text += f"<br><b>Coordinates:</b> {lat:.5f}, {lon:.5f}"
        
        st.markdown(f"""
        <div style="background: #1e293b; border-left: 4px solid #3b82f6; 
                    padding: 14px 18px; border-radius: 8px; margin-bottom: 20px; color: white;">
            {loc_text}
        </div>
        """, unsafe_allow_html=True)

        if lat and lon:
            st.link_button(
                "🗺️ Open Last Known Location in Maps",
                f"https://maps.google.com/?q={lat},{lon}",
                use_container_width=True
            )

    # ========== EMERGENCY CALL BUTTONS ==========
    st.markdown("### 📞 Emergency Contacts")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <a href="tel:1554" style="text-decoration: none;">
            <div style="background: linear-gradient(135deg, #dc2626, #b91c1c);
                        color: white; padding: 20px; border-radius: 14px; text-align: center;
                        font-weight: 700; font-size: 1.15rem; margin-bottom: 12px;
                        box-shadow: 0 6px 18px rgba(220, 38, 38, 0.45);">
                📞 Coast Guard<br>
                <span style="font-size: 1.6rem;">1554</span>
            </div>
        </a>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <a href="tel:112" style="text-decoration: none;">
            <div style="background: linear-gradient(135deg, #ea580c, #c2410c);
                        color: white; padding: 20px; border-radius: 14px; text-align: center;
                        font-weight: 700; font-size: 1.15rem; margin-bottom: 12px;
                        box-shadow: 0 6px 18px rgba(234, 88, 12, 0.45);">
                📞 National Emergency<br>
                <span style="font-size: 1.6rem;">112</span>
            </div>
        </a>
        """, unsafe_allow_html=True)

    # ========== INSTRUCTIONS ==========
    st.markdown("---")
    st.markdown("### 📋 What to do in Emergency")

    st.markdown("""
    <div style="background: #0f172a; border-radius: 12px; padding: 18px; color: #e2e8f0; line-height: 1.7;">
        <b>1.</b> Click <b>“Get My Live Location”</b> and allow permission<br>
        <b>2.</b> Call <b>Coast Guard (1554)</b> or <b>Emergency (112)</b><br>
        <b>3.</b> Tell them your live GPS coordinates<br>
        <b>4.</b> You can also open Google Maps and share the location<br>
        <b>5.</b> Wear life jacket and stay calm<br>
        <b>6.</b> Stay with the boat if it is still floating
    </div>
    """, unsafe_allow_html=True)

    st.caption("Live location works best on mobile phones. Make sure GPS / Location is turned ON.")

# ====================== UI SETUP ======================
st.set_page_config(page_title="Marine Intelligence Platform", page_icon="🌊", layout="wide")

for key, default in {
    "language": "English", "messages": [], "map_location": None, "pfz_data": None,
    "selected_zone_index": 0, "last_audio_hash": None, "pending_prompt": None,
    "auto_speak": True, "show_alerts_panel": False
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.markdown("""
<style>
.st-key-chat_dock_container {
    position: fixed !important; bottom: 15px !important; left: 50% !important;
    transform: translateX(-50%) !important; width: min(920px, 94vw) !important;
    z-index: 999999 !important; background: rgba(15, 23, 42, 0.95) !important;
    backdrop-filter: blur(16px) !important; border: 1px solid rgba(56, 189, 248, 0.45) !important;
    border-radius: 20px !important; padding: 8px 14px !important;
    box-shadow: 0 -8px 30px rgba(0,0,0,0.65);
}
.bottom-scroll-spacer { height: 120px; }
</style>
""", unsafe_allow_html=True)

now = datetime.now()
st.title("🌊 Marine Intelligence Platform")
st.markdown(f"### 📅 {now.strftime('%d %B %Y')} &nbsp;&nbsp;|&nbsp;&nbsp; 🕒 {now.strftime('%I:%M %p')}")
st.write("AI-powered safety, weather, PFZ, navigation & **Live Location SOS** for Indian fishermen.")
st.divider()

# ====================== SIDEBAR ======================
with st.sidebar:
    st.header("🌐 Language")
    language = st.radio("Select Language", ["English", "Hindi"], index=0 if st.session_state.language == "English" else 1)
    st.session_state.language = language

    st.markdown("---")
    st.header("🔊 Voice")
    st.session_state.auto_speak = st.toggle("Auto-Speak Responses", value=st.session_state.auto_speak)

    st.markdown("---")
    st.header("🆘 Emergency")
    current_loc = st.session_state.get("map_location")
    if current_loc:
        render_sos_button(
            current_loc.get("name"),
            current_loc.get("harbour_lat") or current_loc.get("lat"),
            current_loc.get("harbour_lon") or current_loc.get("lon")
        )
    else:
        render_sos_button()

    st.markdown("---")
    st.header("🆘 Helpline")
    st.link_button("💬 WhatsApp Helpline", f"https://wa.me/{WHATSAPP_NUMBER}?text={quote('Hello, I need fishing advisory help.')}", use_container_width=True)
    st.markdown(f'<a href="tel:{PHONE_NUMBER}"><button style="width:100%;padding:10px;background:#25D366;color:white;border:none;border-radius:8px;font-size:16px;cursor:pointer;">📞 Call Helpline</button></a>', unsafe_allow_html=True)

# ====================== MAIN TABS ======================
tab1, tab2, tab3 = st.tabs(["📡 Live Dashboard", "🆘 Emergency SOS", "🗺️ Navigation & PFZ"])

with tab1:
    monitor_data = cached_continuous_monitor()
    render_monitoring_dashboard(monitor_data)
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚨 View Active Alerts", use_container_width=True, type="primary"):
            st.session_state.show_alerts_panel = True
    with c2:
        if st.button("🔄 Refresh Monitoring", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    if st.session_state.show_alerts_panel:
        st.markdown("---")
        render_active_alerts_panel(st.session_state.language)
        if st.button("Close Alerts Panel"):
            st.session_state.show_alerts_panel = False
            st.rerun()

with tab2:
    current_loc = st.session_state.get("map_location")
    if current_loc:
        render_sos_button(
            current_loc.get("name"),
            current_loc.get("harbour_lat") or current_loc.get("lat"),
            current_loc.get("harbour_lon") or current_loc.get("lon")
        )
    else:
        render_sos_button()

with tab3:
    if st.session_state.map_location:
        loc = st.session_state.map_location
        st.subheader(f"🛰️ Satellite Map & Routes — {loc['name']}")
        st.info("Map and multi-route navigation will appear here when a location is queried via chat.")
    else:
        st.info("Ask a question about a coastal location (e.g. 'Is it safe in Goa?' or 'Best PFZ near Kochi') to see the map.")

# Chat History
for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        if msg.get("weather_data"):
            render_weather_card(msg["weather_data"], msg.get("location_name", "Location"))
        if msg.get("alert_data"):
            render_alert_banner(msg["alert_data"])
        if msg.get("pfz_data"):
            render_pfz_section(msg["pfz_data"])
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            render_tts_button(msg["content"], st.session_state.language, auto_play=False, msg_id=f"hist_{idx}")

st.markdown("<div class='bottom-scroll-spacer'></div>", unsafe_allow_html=True)

# ====================== STICKY CHAT DOCK ======================
def submit_text():
    text = st.session_state.get("user_typed_input", "").strip()
    if text:
        st.session_state.pending_prompt = text
        st.session_state.user_typed_input = ""

with st.container(key="chat_dock_container"):
    input_col, send_col = st.columns([6, 1])
    with input_col:
        st.text_input("Marine Question", placeholder="Ask about sea safety, weather, alerts or PFZ...", key="user_typed_input", on_change=submit_text, label_visibility="collapsed")
    with send_col:
        st.button("Send ➤", on_click=submit_text, use_container_width=True, type="primary")

    with st.expander("🎙️ Voice Input (Groq Whisper)", expanded=False):
        audio_file = st.audio_input("Record Audio", label_visibility="collapsed", key="dock_mic_input")

# Handle audio
if 'audio_file' in locals() and audio_file is not None:
    try:
        audio_bytes = audio_file.getvalue()
    except:
        audio_bytes = audio_file.read()
    if audio_bytes and len(audio_bytes) > 200:
        audio_hash = hashlib.md5(audio_bytes).hexdigest()
        if st.session_state.last_audio_hash != audio_hash:
            st.session_state.last_audio_hash = audio_hash
            with st.spinner("🎧 Transcribing..."):
                transcribed = transcribe_voice_query(audio_bytes, st.session_state.language)
                if transcribed:
                    st.session_state.pending_prompt = transcribed
                    st.toast(f"🗣️ Transcribed: {transcribed}", icon="🎙️")

# ====================== AGENT ORCHESTRATION ======================
active_prompt = None
if st.session_state.pending_prompt:
    active_prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if active_prompt:
    st.session_state.messages.append({"role": "user", "content": active_prompt})
    with st.chat_message("user"):
        st.markdown(active_prompt)

    with st.chat_message("assistant"):
        nlp_plan = advanced_nlp_agent(active_prompt)
        weather_data = pfz_data = alert_data = location_name = None
        agent_log = [f"NLP ({nlp_plan['intent']})"]

        if nlp_plan["intent"] in ["GREETING", "BOT_IDENTITY", "GRATITUDE", "NORMAL_CHAT"]:
            st.session_state.map_location = None
            st.session_state.pfz_data = None

        if nlp_plan["intent"] == "SHOW_ALERTS":
            agent_log.append("Alert Agent")
            st.session_state.show_alerts_panel = True
            render_active_alerts_panel(st.session_state.language)

        if nlp_plan["needs_weather"] and nlp_plan.get("location"):
            loc = nlp_plan["location"]
            location_name = loc["name"]
            weather_data = weather_agent(loc["lat"], loc["lon"])
            st.session_state.map_location = loc
            agent_log.append("Weather Agent")
            render_weather_card(weather_data, location_name)
            alert_data = alert_agent(weather_data, location_name, st.session_state.language)
            agent_log.append(f"Alert ({alert_data['level']})")
            render_alert_banner(alert_data)
            if nlp_plan.get("needs_pfz"):
                pfz_data = pfz_agent(loc, weather_data)
                st.session_state.pfz_data = pfz_data
                st.session_state.selected_zone_index = 0
                agent_log.append("PFZ Agent")
                render_pfz_section(pfz_data)

        agent_log.append("Response Agent")
        final_answer = response_agent(active_prompt, nlp_plan, weather_data, pfz_data, alert_data, st.session_state.language)
        st.markdown(final_answer)

        should_speak = st.session_state.auto_speak
        render_tts_button(final_answer, st.session_state.language, auto_play=should_speak, msg_id="latest")

        st.caption(f"🧠 Agents: {' → '.join(agent_log)}")

    st.session_state.messages.append({
        "role": "assistant", "content": final_answer,
        "weather_data": weather_data, "pfz_data": pfz_data,
        "alert_data": alert_data, "location_name": location_name, "agent_log": agent_log
    })
    st.rerun()
