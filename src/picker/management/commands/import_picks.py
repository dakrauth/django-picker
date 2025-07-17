import json
from django.core.management.base import BaseCommand
from picker import models as picker


class Command(BaseCommand):
    help = "Loads a new sports league"
    requires_migrations_checks = True
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("filenames", nargs="+")

    def handle(self, *args, **options):
        for arg in options["filenames"]:
            with open(arg) as fin:
                data = json.loads(fin.read())

            schema = data["schema"]
            if schema == "complete" or schema == "league":
                league_info, teams_info = picker.League.import_league(data)
                self.stdout.write(
                    "{} league {}\n".format(
                        "Created" if league_info[1] else "Updated", league_info[0]
                    )
                )
                for t, created in teams_info:
                    self.stdout.write("{} team {}\n".format("Created" if created else "Updated", t))

            if schema == "complete" or schema == "season":
                results = picker.League.import_season(data)
                count = len(results)
                created = sum(1 for r in results if r[1])
                print(
                    "Processed {} gamesets: {} new, {} updated".format(
                        count, created, count - created
                    )
                )
