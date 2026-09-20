from django.core.management.base import BaseCommand

from collectable.models import DuplicateReport


class Command(BaseCommand):
    help = "Merge the collectables reported as duplicates into their original"

    def handle(self, *args, **options):
        count = 0
        for report in DuplicateReport.objects.filter(duplicate__hidden=False):
            # Fetched one by one on purpose: the same collectable can be
            # reported several times, and is only merged once.
            duplicate = report.duplicate
            if duplicate.hidden:
                continue

            duplicate.merge_into(report.original)
            self.stdout.write(f"{duplicate.id} merged into {report.original_id}")
            count += 1

        self.stdout.write(self.style.SUCCESS(f"{count} collectables merged."))
