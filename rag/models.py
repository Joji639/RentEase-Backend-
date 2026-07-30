from django.db import models

# Create your models here.
from django.db import models

class ListingEmbedding(models.Model):
    listing = models.OneToOneField('listings.Listing', on_delete=models.CASCADE, related_name='embedding')
    content_text = models.TextField()
    vector = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)