import string
from typing import List, Dict, Any

from tools.weather_tool import get_current_weather, get_daily_forecast
from tools.geocode_tool import get_coordinates
from tools.llm_tool import generate_response


# ----------------------------------------------------------
#  CITY MATCHING (fixes spelling like "banglore")
# ----------------------------------------------------------
DEFAULT_CITY = "bangalore"

CITY_ALIASES = {
    "bangalore": ["bangalore", "banglore", "blr", "bengaluru", "bengalooru"],
    "chennai": ["chennai", "madras"],
    "mumbai": ["mumbai", "bombay"],
    "delhi": ["delhi", "dilli", "new delhi"],
    "hyderabad": ["hyderabad", "hyd"],
    "kolkata": ["kolkata", "calcutta"],
}


def resolve_city_alias(user_text: str) -> str:
    t = user_text.lower()
    for city, aliases in CITY_ALIASES.items():
        for a in aliases:
            if a in t:
                return city
    return ""


# ----------------------------------------------------------
#  WEATHER INTENT DETECTION (SMART)
# ----------------------------------------------------------
def is_weather_question(text: str) -> bool:
    text = text.lower()
    keywords = [
        "weather", "temperature", "climate",
        "hot", "cold", "warm", "cool",
        "rain", "raining", "rainfall",
        "wind", "windy",
        "forecast", "umbrella", "jacket",
        "outside", "tell me in", "how is it in", "climate in"
    ]
    return any(word in text for word in keywords)


# ----------------------------------------------------------
#  FORECAST HORIZON DETECTION
# ----------------------------------------------------------
def detect_forecast_horizon(text: str) -> str:
    t = text.lower()

    if "tomorrow" in t:
        return "tomorrow"
    if "next 3 days" in t or "next three days" in t:
        return "next_3_days"
    if "next week" in t or "next 7 days" in t or "next seven days" in t:
        return "next_7_days"

    return "now"


# ----------------------------------------------------------
#  Extract City Name (Fallback logic)
# ----------------------------------------------------------
def clean_city_name(name: str) -> str:
    return name.translate(str.maketrans("", "", string.punctuation)).strip()


def extract_city(text: str) -> str:
    """
    Extract city using:
    1. alias matching
    2. 'in <city>' pattern
    3. last meaningful word
    """
    # Try alias resolution first
    alias_city = resolve_city_alias(text)
    if alias_city:
        return alias_city

    ignore_words = {"tomorrow", "today", "now", "next", "week", "day", "weather", "temperature", "climate"}

    words = text.lower().split()

    if "in" in words:
        idx = words.index("in")
        city_words = []
        for w in words[idx + 1:]:
            if w in ignore_words:
                break
            city_words.append(w)
        if city_words:
            return " ".join(city_words).strip()

    # fallback: last relevant word
    for w in reversed(words):
        if w not in ignore_words:
            return w

    return ""


# ----------------------------------------------------------
#  RULE-BASED ADVICE ENGINE
# ----------------------------------------------------------
def generate_weather_advice(temp: float, wind: float) -> str:
    advice = ""

    if temp is None:
        return "Weather data is incomplete."

    if temp >= 35:
        advice += "It's extremely hot — avoid noon sun. "
    elif temp >= 30:
        advice += "It's hot — wear light clothes and drink water. "
    elif temp >= 20:
        advice += "The weather is pleasant — light clothing is fine. "
    elif temp >= 10:
        advice += "It's cool — a light jacket is good. "
    else:
        advice += "Very cold — wear warm clothing. "

    if wind is not None:
        if wind >= 30:
            advice += "Strong winds — avoid two-wheelers."
        elif wind >= 15:
            advice += "Slightly windy — be cautious."

    return advice.strip()


# ----------------------------------------------------------
#  MAIN AGENT LOOP
# ----------------------------------------------------------
def run_agent():
    print("Agent is running.")
    print("Ask about current weather or forecast. Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ")

        if not user_input.strip():
            continue

        if user_input.lower() == "exit":
            print("Agent: Goodbye!")
            break

        # If not weather → echo
        if not is_weather_question(user_input):
            print(f"Agent: You said → {user_input}\n")
            continue

        # 1) Time horizon
        horizon = detect_forecast_horizon(user_input)

        # 2) City extraction
        city_guess = extract_city(user_input)

        # if no city found → use default
        if not city_guess:
          city_guess = DEFAULT_CITY


        # 3) Geocoding
        geo = get_coordinates(city_guess)
        if "error" in geo:
            print("Agent:", geo["error"])
            print("Try: 'weather in Bangalore'\n")
            continue

        lat = geo["lat"]
        lon = geo["lon"]
        resolved_city = geo["city"]
        country = geo.get("country", "")
        
        # ---------------- NOW WEATHER ----------------
        if horizon == "now":
            weather = get_current_weather(lat, lon)
            if "error" in weather:
                print("Agent: Error fetching weather:", weather["error"])
                print()
                continue

            temp = weather["temperature"]
            wind = weather["windspeed"]

            advice = generate_weather_advice(temp, wind)

            context = f"""
User question: {user_input}
Location: {resolved_city}, {country}
Current temperature: {temp}°C
Wind speed: {wind} km/h
Rule-based advice: {advice}
"""
            final_message = generate_response(context)
            print("Agent:", final_message)
            print()
            continue

        # ---------------- FORECAST ----------------
        else:
            if horizon == "tomorrow":
                days = 2
            elif horizon == "next_3_days":
                days = 3
            else:
                days = 7

            forecast = get_daily_forecast(lat, lon, days=days)
            if "error" in forecast:
                print("Agent: Error fetching forecast:", forecast["error"])
                print()
                continue

            # Build summary
            lines: List[str] = []
            for d in forecast["days"]:
                lines.append(
                    f"Date: {d['date']}, Max: {d['temp_max']}°C, Min: {d['temp_min']}°C, Rain chance: {d['precip_prob']}%"
                )

            forecast_context = "\n".join(lines)

            context = f"""
User question: {user_input}
Location: {resolved_city}, {country}

Forecast Data:
{forecast_context}

Explain this forecast clearly for a non-technical user.
Mention if they should carry umbrella, jacket, etc.
"""

            final_message = generate_response(context)
            print("Agent:", final_message)
            print()
            continue
def run_agent_once(user_input: str) -> str:
    """
    Processes a single message and returns the agent's reply.
    Used by Streamlit instead of the interactive run_agent().
    """

    if not is_weather_question(user_input):
        return f"You said → {user_input}"

    # 1. Forecast horizon
    horizon = detect_forecast_horizon(user_input)

    # 2. Extract city
    city_guess = extract_city(user_input)
    if not city_guess:
        city_guess = DEFAULT_CITY

    # 3. Geocode
    geo = get_coordinates(city_guess)
    if "error" in geo:
        return "Could not find that city. Try: 'weather in Bangalore'."

    lat = geo["lat"]
    lon = geo["lon"]
    resolved_city = geo["city"]
    country = geo.get("country", "")

    # -------------- CURRENT WEATHER -------------- #
    if horizon == "now":
        weather = get_current_weather(lat, lon)
        if "error" in weather:
            return "Error fetching weather."

        temp = weather["temperature"]
        wind = weather["windspeed"]

        advice = generate_weather_advice(temp, wind)

        context = f"""
User question: {user_input}
Location: {resolved_city}, {country}
Current temperature: {temp}°C
Wind speed: {wind} km/h
Rule-based advice: {advice}
"""
        return generate_response(context)

    # -------------- FORECAST -------------- #
    if horizon == "tomorrow":
        days = 2
    elif horizon == "next_3_days":
        days = 3
    else:
        days = 7

    forecast = get_daily_forecast(lat, lon, days=days)
    if "error" in forecast:
        return "Error fetching forecast."

    lines = []
    for d in forecast["days"]:
        lines.append(
            f"Date: {d['date']}, Max: {d['temp_max']}°C, Min: {d['temp_min']}°C, Rain chance: {d['precip_prob']}%"
        )

    forecast_context = "\n".join(lines)

    context = f"""
User question: {user_input}
Location: {resolved_city}, {country}

Forecast:
{forecast_context}

Explain clearly for a normal user.
"""
    return generate_response(context)
