from django.core.management.base import BaseCommand
from services.models import ServiceCategory


class Command(BaseCommand):
    help = "Seeds initial RentEase service categories."

    def handle(self, *args, **kwargs):
        categories = [
            ("Kitchen Appliance", "Repair and maintenance of kitchen appliances like mixers, ovens, and refrigerators."),
            ("Electrician", "Electrical wiring, repairs, and installations."),
            ("Carpentry", "Furniture repair, custom woodwork, and installations."),
            ("Plumbing", "Pipe repairs, leak fixes, and fixture installations."),
            ("AC Repair", "Air conditioner servicing, repair, and installation."),
            ("Washing Machine Repair", "Washing machine servicing and repair."),
        ]

        for name, description in categories:
            obj, created = ServiceCategory.objects.get_or_create(
                name=name, defaults={"description": description}
            )
            status_msg = "Created" if created else "Already exists"
            self.stdout.write(self.style.SUCCESS(f"{status_msg}: {name}"))