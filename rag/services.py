import math
import re
from django.db.models import Q
from fastembed import TextEmbedding
from .models import ListingEmbedding
from services.models import ServiceCategory
from technicians.views import get_technicians_by_category_sorted

_embedder = None
_EMBED_DIM = 384


def _get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _embedder


def embed_text(text):
    model = _get_embedder()
    return list(model.embed([text]))[0].tolist()


def _validate_dimensions():
    first = ListingEmbedding.objects.values_list("vector", flat=True).first()
    if first and len(first) != _EMBED_DIM:
        ListingEmbedding.objects.all().delete()


def index_listing(listing):
    text = f"{listing.title} {listing.description} {listing.category} rent {getattr(listing, 'location', '')} price per week {listing.price_per_week}"
    try:
        vec = embed_text(text)
    except Exception:
        return
    ListingEmbedding.objects.update_or_create(
        listing=listing, defaults={"content_text": text, "vector": vec}
    )

def reindex_all_listings():
    from listings.models import Listing
    ListingEmbedding.objects.all().delete()
    for listing in Listing.objects.all():
        index_listing(listing)


def search_listings_db(query, max_price=None, limit=10):
    from listings.models import Listing
    words = [w.strip().lower() for w in query.split() if len(w.strip()) >= 2 and not w.strip().isdigit()]
    if not words:
        return []

    q = Q()
    for word in words:
        q &= Q(title__icontains=word) | Q(description__icontains=word)

    qs = Listing.objects.filter(q)
    if max_price is not None:
        qs = qs.filter(price_per_week__lte=max_price)

    return list(qs.select_related("owner", "category").order_by("-created_at")[:limit])


def search_technicians_tool(category_name, lat, lng):
    category = ServiceCategory.objects.filter(name__iexact=category_name).first()
    if not category:
        category = ServiceCategory.objects.filter(
            is_active=True, name__icontains=category_name
        ).first()
    if not category:
        return {"error": f"No service category matching '{category_name}'."}

    data, error = get_technicians_by_category_sorted(category.id, lat, lng)
    if error:
        return {"error": error}
    return data
