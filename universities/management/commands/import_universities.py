import json
from django.core.management.base import BaseCommand
from django.db import transaction
from universities.models import University, UniversityDomain


class Command(BaseCommand):
    help = "Import universities from world_universities_and_domains.json (US only)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="world_universities_and_domains.json",
            help="Path to the JSON file (default: world_universities_and_domains.json)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview the import without saving to database",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing university data before importing",
        )

    def handle(self, *args, **options):
        json_file = options["file"]
        dry_run = options["dry_run"]
        clear_existing = options["clear"]

        self.stdout.write(f"Loading data from: {json_file}")

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                universities_data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(f"File not found: {json_file}")
            )
            return
        except json.JSONDecodeError as e:
            self.stdout.write(
                self.style.ERROR(f"Invalid JSON format: {e}")
            )
            return

        # Filter for US universities only
        us_universities = [u for u in universities_data if u.get("country") == "United States"]

        self.stdout.write(
            self.style.SUCCESS(f"Found {len(us_universities)} US universities")
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No data will be saved")
            )
            # Show sample of first 5 universities
            for i, uni_data in enumerate(us_universities[:5], 1):
                self.stdout.write(f"\n{i}. {uni_data['name']}")
                self.stdout.write(f"   Domains: {', '.join(uni_data.get('domains', []))}")
                self.stdout.write(f"   State: {uni_data.get('state-province', 'N/A')}")
            self.stdout.write(f"\n... and {len(us_universities) - 5} more universities")
            return

        # Clear existing data if requested
        if clear_existing:
            with transaction.atomic():
                domain_count = UniversityDomain.objects.count()
                uni_count = University.objects.count()
                UniversityDomain.objects.all().delete()
                University.objects.all().delete()
                self.stdout.write(
                    self.style.WARNING(
                        f"Cleared {uni_count} universities and {domain_count} domains"
                    )
                )

        # Import universities
        created_universities = 0
        created_domains = 0
        skipped_universities = 0
        errors = []

        # Process in batches to avoid transaction timeout
        batch_size = 100
        for batch_start in range(0, len(us_universities), batch_size):
            batch = us_universities[batch_start:batch_start + batch_size]

            self.stdout.write(f"Processing batch {batch_start // batch_size + 1} " +
                            f"(universities {batch_start + 1}-{min(batch_start + batch_size, len(us_universities))})")

            try:
                with transaction.atomic():
                    for uni_data in batch:
                        try:
                            name = uni_data.get("name", "").strip()
                            if not name:
                                skipped_universities += 1
                                continue

                            domains_list = uni_data.get("domains", [])
                            if not domains_list:
                                skipped_universities += 1
                                continue

                            # Create or get university
                            university, created = University.objects.get_or_create(
                                name=name,
                                defaults={
                                    "country": uni_data.get("country", "United States"),
                                    "state_province": uni_data.get("state-province"),
                                    "alpha_two_code": uni_data.get("alpha_two_code", "US"),
                                    "web_pages": ", ".join(uni_data.get("web_pages", [])),
                                },
                            )

                            if created:
                                created_universities += 1

                            # Create domains
                            for i, domain in enumerate(domains_list):
                                domain = domain.strip().lower()
                                if not domain:
                                    continue

                                is_primary = i == 0  # First domain is primary

                                domain_obj, domain_created = UniversityDomain.objects.get_or_create(
                                    domain=domain,
                                    defaults={
                                        "university": university,
                                        "is_primary": is_primary,
                                    },
                                )

                                if domain_created:
                                    created_domains += 1
                        except Exception as e:
                            error_msg = f"Error importing {name}: {str(e)}"
                            errors.append(error_msg)
                            self.stdout.write(self.style.WARNING(error_msg))
                            continue
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Batch transaction failed: {e}"))
                continue

        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("Import completed!"))
        self.stdout.write(f"Universities created: {created_universities}")
        self.stdout.write(f"Domains created: {created_domains}")
        if skipped_universities > 0:
            self.stdout.write(
                self.style.WARNING(f"Universities skipped: {skipped_universities}")
            )
        if errors:
            self.stdout.write(
                self.style.ERROR(f"Errors encountered: {len(errors)}")
            )
            if len(errors) <= 10:
                for error in errors:
                    self.stdout.write(f"  - {error}")
        self.stdout.write("=" * 50)

        # Show some examples
        self.stdout.write("\nSample of imported universities:")
        sample_unis = University.objects.all()[:5]
        for uni in sample_unis:
            primary_domain = uni.get_primary_domain()
            domain_count = uni.domains.count()
            self.stdout.write(
                f"  • {uni.name} ({primary_domain}) - {domain_count} domain(s)"
            )
