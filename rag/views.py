import json
import logging
import os
import re
from groq import Groq
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from common.responses import APIResponse
from common.geocoding import geocode_address
from .services import search_listings_db, search_technicians_tool

logger = logging.getLogger(__name__)

client = Groq(api_key=os.environ["GROQ_API_KEY"])

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_listings",
            "description": "Search rental listings/products by name/keywords and optional max price. The database is the source of truth — do NOT invent listings or prices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Product name or keywords, e.g. 'washing machine', 'oven', 'chair'"},
                    "max_price": {"type": "number", "description": "Maximum price per week the user is willing to pay"}
                },
                "required": ["query"],
            },
        },
    },
]

TECHNICIAN_ROLES = {
    "carpenter", "carpentry", "plumber", "plumbing", "electrician", "electrical",
    "painter", "painting", "mechanic", "welder", "fitter", "mason", "cleaning",
}

TECHNICIAN_CONTEXT = {"technician", "repair", "service", "near me", "nearby"}

CATEGORY_ALIASES = {
    "carpenter": "Carpentry", "carpentry": "Carpentry",
    "electrician": "Electrician",
    "plumber": "Plumbing", "plumbing": "Plumbing",
    "ac": "AC Repair", "ac repair": "AC Repair", "ac technician": "AC Repair", "ac service": "AC Repair",
    "washing machine": "Washing Machine Repair", "washing machine repair": "Washing Machine Repair",
    "kitchen": "Kitchen Appliance", "kitchen appliance": "Kitchen Appliance",
}

_pending = {}


def _word_in_text(word, text):
    return bool(re.search(r'\b' + re.escape(word) + r'\b', text, re.IGNORECASE))


def _detect_technician_query(message):
    msg_lower = message.lower()

    for role in TECHNICIAN_ROLES:
        if _word_in_text(role, msg_lower):
            if role in CATEGORY_ALIASES:
                return CATEGORY_ALIASES[role]
            return role.title()

    has_context = any(_word_in_text(ctx, msg_lower) for ctx in TECHNICIAN_CONTEXT)
    if has_context:
        for kw, mapped in CATEGORY_ALIASES.items():
            if _word_in_text(kw, msg_lower):
                return mapped

    return None


def _is_new_query(message):
    msg_lower = message.lower()

    for role in TECHNICIAN_ROLES:
        if _word_in_text(role, msg_lower):
            return True

    for ctx in TECHNICIAN_CONTEXT:
        if _word_in_text(ctx, msg_lower):
            return True                                      

    if re.search(r'\b(under|per week|/week|price|cheap|rent)\b', msg_lower, re.IGNORECASE):
        return True

    for kw in CATEGORY_ALIASES:
        if _word_in_text(kw, msg_lower):
            return True

    return False


def _extract_location_text(message):
    patterns = [
        r'(?:near|in|at)\s+(.+?)(?:\s*$|\.|,)',
        r'(?:near|in|at)\s+(.+)',
    ]
    for pattern in patterns:
        m = re.search(pattern, message, re.IGNORECASE)
        if m:
            loc = m.group(1).strip()
            if loc.lower() not in ("me", "my location", ""):
                return loc
    return None


def _build_listing_answer(results, query):
    if not results:
        return f"I couldn't find any {query} matching your criteria."
    lines = [f"{l.title} — \u20B9{l.price_per_week}/week" for l in results]
    return f"I found {len(results)} {query}:\n" + "\n".join(lines)


def _serialize_listing_results(results):
    return [
        {
            "id": str(l.id),
            "title": l.title,
            "price_per_week": str(l.price_per_week),
            "image": l.images.first().image.url if l.images.exists() else None,
            "location": l.location,
        }
        for l in results
    ]


def _build_technician_answer(results, category=None):
    if isinstance(results, dict) and "error" in results:
        return results["error"]
    if isinstance(results, list) and results:
        header = f"Nearby {category} technicians:" if category else "Nearby technicians:"
        return header + "\n" + "\n".join(
            f"{t.get('full_name', 'Technician')} — {t.get('distance_km', '?')} km away" for t in results
        )
    return f"No {category} technicians found nearby." if category else "No technicians found nearby."


def _serialize_technician_results(results):
    return [
        {
            "id": t.get("id"),
            "name": t.get("full_name"),
            "category": t.get("specialization", {}).get("name") if isinstance(t.get("specialization"), dict) else None,
            "category_id": t.get("specialization", {}).get("id") if isinstance(t.get("specialization"), dict) else None,
            "profile_image": t.get("profile_image"),
            "distance_km": t.get("distance_km"),
        }
        for t in results
    ]


SYSTEM_PROMPT = """You are the RentEase AI Assistant for a rental marketplace. You help users find rental items.

When the user wants to search for rental products, use the search_listings tool with the product name and optional max price.

Rules:
- Only use information the user actually provided. Do not make up products, prices, or categories.
- If no matching results exist, say so honestly.
- Be concise and friendly. Use a natural conversational tone."""


class AskView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        message = request.data.get("message")
        if not message or not isinstance(message, str) or not message.strip():
            return APIResponse.error(
                message="Please provide a valid question.",
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_id = str(request.user.id)
        msg = message.strip()

        category = _detect_technician_query(msg)
        if category:
            _pending.pop(user_id, None)
            user_lat = request.user.latest_latitude
            user_lng = request.user.latest_longitude
            loc_text = _extract_location_text(msg)

            if loc_text:
                coords = geocode_address(loc_text)
                if coords:
                    results = search_technicians_tool(category, coords[0], coords[1])
                    if isinstance(results, dict) and "error" in results:
                        return APIResponse.success(
                            data={"answer": results["error"], "result_type": None, "results": []},
                            message="Answer generated.",
                            status=status.HTTP_200_OK,
                        )
                    return APIResponse.success(
                        data={
                            "answer": _build_technician_answer(results, category),
                            "result_type": "technicians",
                            "results": _serialize_technician_results(results),
                        },
                        message="Answer generated.",
                        status=status.HTTP_200_OK,
                    )
                return APIResponse.success(
                    data={"answer": f"Could not find location '{loc_text}'. Please try a different place name.", "result_type": None, "results": []},
                    message="Geocoding failed.",
                    status=status.HTTP_200_OK,
                )

            if user_lat and user_lng:
                results = search_technicians_tool(category, float(user_lat), float(user_lng))
                if isinstance(results, dict) and "error" in results:
                    return APIResponse.success(
                        data={"answer": results["error"], "result_type": None, "results": []},
                        message="Answer generated.",
                        status=status.HTTP_200_OK,
                    )
                return APIResponse.success(
                    data={
                        "answer": _build_technician_answer(results, category),
                        "result_type": "technicians",
                        "results": _serialize_technician_results(results),
                    },
                    message="Answer generated.",
                    status=status.HTTP_200_OK,
                )

            _pending[user_id] = {"waiting_location": True, "category": category}
            return APIResponse.success(
                data={
                    "answer": "Sure. What location should I search around?",
                    "need_location": True,
                },
                message="Location needed.",
                status=status.HTTP_200_OK,
            )

        if user_id in _pending and _pending[user_id].get("waiting_location"):
            if not _is_new_query(msg):
                loc_text = _extract_location_text(msg) or msg
                coords = geocode_address(loc_text)
                if not coords:
                    return APIResponse.success(
                        data={"answer": f"Could not find location '{loc_text}'. Please try a different place name."},
                        message="Geocoding failed.",
                        status=status.HTTP_200_OK,
                    )
                lat, lng = coords
                cat = _pending[user_id]["category"]
                del _pending[user_id]
                results = search_technicians_tool(cat, lat, lng)
                if isinstance(results, dict) and "error" in results:
                    return APIResponse.success(
                        data={"answer": results["error"], "result_type": None, "results": []},
                        message="Answer generated.",
                        status=status.HTTP_200_OK,
                    )
                return APIResponse.success(
                    data={
                        "answer": _build_technician_answer(results, cat),
                        "result_type": "technicians",
                        "results": _serialize_technician_results(results),
                    },
                    message="Answer generated.",
                    status=status.HTTP_200_OK,
                )
            _pending.pop(user_id, None)

        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": msg},
                ],
                tools=tools,
                tool_choice="auto",
            )

            choice = resp.choices[0]
            gm = choice.message 

            if not gm.tool_calls:
                return APIResponse.success(
                    data={"answer": gm.content or "How can I help you?", "result_type": None, "results": []},
                    message="Answer generated.",
                    status=status.HTTP_200_OK,
                )

            tool_call = gm.tool_calls[0]
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            if name == "search_listings":
                results = search_listings_db(args["query"], max_price=args.get("max_price"))
                return APIResponse.success(
                    data={
                        "answer": _build_listing_answer(results, args["query"]),
                        "result_type": "listings" if results else None,
                        "results": _serialize_listing_results(results),
                    },
                    message="Answer generated.",
                    status=status.HTTP_200_OK,
                )

            return APIResponse.success(
                data={"answer": "I'm not sure how to help with that.", "result_type": None, "results": []},
                message="Answer generated.",
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.exception("RAG AskView failed for user=%s message=%r", request.user, msg[:120])
            msg_lower = str(e).lower()
            if "quota" in msg_lower or "rate_limit" in msg_lower or "429" in str(e):
                safe = "AI service is currently at capacity. Please try again later."
            elif "api key" in msg_lower or "unauthorized" in msg_lower or "auth" in msg_lower:
                safe = "AI service configuration error. Please contact support."
            else:
                safe = "Failed to generate answer. Please try again."
            return APIResponse.error(message=safe, status=status.HTTP_200_OK)
