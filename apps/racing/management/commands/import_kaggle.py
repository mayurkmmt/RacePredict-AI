import csv
import glob
import os
import hashlib
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.racing.models import Course, Horse, Jockey, Trainer, Race, RaceEntry


class Command(BaseCommand):
    help = "Import Kaggle horse racing data (races, horses, forward) into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            help="Path to the Kagglehub version 3 directory",
            default="kagglehub/datasets/hwaitt/horse-racing/versions/3",
        )

    def to_float(self, val):
        try:
            return float(val) if val else None
        except ValueError:
            return None

    def to_int(self, val):
        try:
            # Handle cases where int is formatted as 10.0
            return int(float(val)) if val else None
        except ValueError:
            return None

    def handle(self, *args, **options):
        base_path = Path(options["path"])

        if not base_path.exists():
            self.stdout.write(self.style.ERROR(f"Directory {base_path} not found!"))
            return

        self.stdout.write(
            self.style.SUCCESS("Starting the ETL process for historical races...")
        )

        # 1. Process Historical Races (races_YYYY.csv)
        race_files = sorted(glob.glob(str(base_path / "races_*.csv")))
        for r_file in race_files:
            self.stdout.write(f"Processing matches in {os.path.basename(r_file)}")
            self.process_historical_races(r_file)

        # 2. Process Historical Horses (horses_YYYY.csv)
        horse_files = sorted(glob.glob(str(base_path / "horses_*.csv")))
        for h_file in horse_files:
            self.stdout.write(f"Processing entries in {os.path.basename(h_file)}")
            self.process_historical_horses(h_file)

        # 3. Process Future Races (forward.csv)
        forward_file = base_path / "forward.csv"
        if forward_file.exists():
            self.stdout.write("Processing future predictions in forward.csv")
            self.process_forward(forward_file)

        self.stdout.write(self.style.SUCCESS("Data ingestion complete!"))

    @transaction.atomic
    def process_historical_races(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                course, _ = Course.objects.get_or_create(
                    name=row.get("course", "").strip(),
                    defaults={"country_code": row.get("countryCode", "")},
                )

                # Parse date and time safely
                date_str = row.get("date")
                time_str = row.get("time")
                parsed_date = None
                parsed_time = None

                try:
                    if date_str:  # e.g. 20/01/01
                        parsed_date = datetime.strptime(date_str, "%y/%m/%d").date()
                    if time_str:
                        parsed_time = datetime.strptime(time_str, "%H:%M").time()
                except ValueError:
                    pass

                Race.objects.update_or_create(
                    kaggle_rid=row.get("rid"),
                    defaults={
                        "course": course,
                        "date": parsed_date,
                        "time": parsed_time,
                        "title": row.get("title"),
                        "distance": row.get("distance"),
                        "condition": row.get("condition"),
                        "race_class": row.get("class") or row.get("rclass"),
                        "winning_time": self.to_float(row.get("winningTime")),
                        "prize": row.get("prize"),
                    },
                )

    @transaction.atomic
    @transaction.atomic
    def process_historical_horses(self, file_path):
        import csv

        self.stdout.write("Parsing CSV into memory for bulk import...")

        rows = []
        horse_data = {}
        jockey_names = set()
        trainer_names = set()
        race_rids = set()

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rid = row.get("rid")
                h_name = row.get("horseName", "").strip()
                if not rid or not h_name:
                    continue

                rows.append(row)
                race_rids.add(rid)

                j_name = row.get("jockeyName", "").strip()
                if j_name:
                    jockey_names.add(j_name)

                t_name = row.get("trainerName", "").strip()
                if t_name:
                    trainer_names.add(t_name)

                if h_name not in horse_data:
                    horse_data[h_name] = {
                        "father": row.get("father"),
                        "mother": row.get("mother"),
                        "gfather": row.get("gfather"),
                    }

        existing_jockeys = set(
            Jockey.objects.filter(name__in=jockey_names).values_list("name", flat=True)
        )
        Jockey.objects.bulk_create(
            [Jockey(name=j) for j in jockey_names if j not in existing_jockeys],
            ignore_conflicts=True,
        )
        jockey_map = {j.name: j for j in Jockey.objects.filter(name__in=jockey_names)}

        existing_trainers = set(
            Trainer.objects.filter(name__in=trainer_names).values_list(
                "name", flat=True
            )
        )
        Trainer.objects.bulk_create(
            [Trainer(name=t) for t in trainer_names if t not in existing_trainers],
            ignore_conflicts=True,
        )
        trainer_map = {
            t.name: t for t in Trainer.objects.filter(name__in=trainer_names)
        }

        existing_horses = set(
            Horse.objects.filter(name__in=horse_data.keys()).values_list(
                "name", flat=True
            )
        )
        new_horses = [
            Horse(name=k, father=v["father"], mother=v["mother"], gfather=v["gfather"])
            for k, v in horse_data.items()
            if k not in existing_horses
        ]
        Horse.objects.bulk_create(new_horses, ignore_conflicts=True)
        horse_map = {
            h.name: h for h in Horse.objects.filter(name__in=horse_data.keys())
        }

        race_map = {
            r.kaggle_rid: r for r in Race.objects.filter(kaggle_rid__in=race_rids)
        }

        entries_to_create = []
        for row in rows:
            rid = row.get("rid")
            race = race_map.get(rid)
            if not race:
                continue

            horse = horse_map.get(row.get("horseName", "").strip())
            jockey = jockey_map.get(row.get("jockeyName", "").strip())
            trainer = trainer_map.get(row.get("trainerName", "").strip())

            res_win_val = row.get("res_win", "")
            try:
                is_winner = float(res_win_val) == 1.0 if res_win_val else False
            except ValueError:
                is_winner = False

            is_fav = row.get("isFav", "") == "1"

            entries_to_create.append(
                RaceEntry(
                    race=race,
                    horse=horse,
                    jockey=jockey,
                    trainer=trainer,
                    age=self.to_float(row.get("age")),
                    saddle=self.to_float(row.get("saddle")),
                    weight_carried=self.to_float(row.get("weightSt")),
                    decimal_price=self.to_float(row.get("decimalPrice")),
                    is_fav=is_fav,
                    head_gear=row.get("headGear"),
                    rpr=self.to_float(row.get("RPR")),
                    tr=self.to_float(row.get("TR")),
                    or_rating=self.to_float(row.get("OR")),
                    position=self.to_int(row.get("position")),
                    margin=self.to_float(row.get("margin")),
                    res_win=is_winner,
                )
            )

        if entries_to_create:
            RaceEntry.objects.bulk_create(
                entries_to_create,
                update_conflicts=True,
                unique_fields=["race", "horse"],
                update_fields=[
                    "jockey",
                    "trainer",
                    "age",
                    "saddle",
                    "weight_carried",
                    "decimal_price",
                    "is_fav",
                    "head_gear",
                    "rpr",
                    "tr",
                    "or_rating",
                    "position",
                    "margin",
                    "res_win",
                ],
            )

    @transaction.atomic
    def process_forward(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                course_name = row.get("course", "").strip()
                if not course_name:
                    continue

                course, _ = Course.objects.get_or_create(
                    name=course_name,
                    defaults={"country_code": row.get("countryCode", "")},
                )

                # Forward.csv uses marketTime e.g "2020-09-11 12:45:00+01:00"
                market_time = row.get("marketTime", "")
                parsed_date, parsed_time = None, None
                if market_time and len(market_time) >= 10:
                    try:
                        dt = datetime.fromisoformat(market_time)
                        parsed_date = dt.date()
                        parsed_time = dt.time()
                    except ValueError:
                        pass

                title = row.get("title", "")
                # Derive a synthetic kaggle_rid since future races don't have one!
                synth_str = f"FWD_{course_name}_{market_time}_{title}"
                synth_rid = hashlib.md5(synth_str.encode()).hexdigest()[:15]

                race, _ = Race.objects.get_or_create(
                    kaggle_rid=synth_rid,
                    defaults={
                        "course": course,
                        "date": parsed_date,
                        "time": parsed_time,
                        "title": title,
                        "condition": row.get("condition"),
                        "race_class": row.get("rclass"),
                        "prize": row.get("prize"),
                    },
                )

                horse_name = row.get("horseName", "").strip()
                if horse_name:
                    horse, _ = Horse.objects.get_or_create(name=horse_name)

                    jockey = None
                    if row.get("jockeyName"):
                        jockey, _ = Jockey.objects.get_or_create(
                            name=row.get("jockeyName").strip()
                        )

                    trainer = None
                    if row.get("trainerName"):
                        trainer, _ = Trainer.objects.get_or_create(
                            name=row.get("trainerName").strip()
                        )

                    RaceEntry.objects.update_or_create(
                        race=race,
                        horse=horse,
                        defaults={
                            "jockey": jockey,
                            "trainer": trainer,
                            "age": self.to_float(row.get("age")),
                            "weight_carried": self.to_float(row.get("weightSt")),
                            "decimal_price": self.to_float(row.get("decimalPrice")),
                            "or_rating": self.to_float(row.get("OR")),
                            "rpr": self.to_float(row.get("RPRc")),
                            "tr": self.to_float(row.get("TRc")),
                            # Predict targets are all NULL because this is future data!
                            "position": None,
                            "res_win": None,
                            "margin": None,
                        },
                    )
