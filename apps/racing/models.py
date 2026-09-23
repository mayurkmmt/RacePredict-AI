from django.db import models
from django.db.models import Count, Q
from django.db.models.functions import ExtractMonth


class Course(models.Model):
    name = models.CharField(max_length=255, unique=True)
    country_code = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return self.name


class JockeyManager(models.Manager):
    def get_top_winners(self, limit=5):
        return list(
            self.annotate(wins=Count("raceentry", filter=Q(raceentry__res_win=True)))
            .order_by("-wins")[:limit]
            .values("name", "wins")
        )


class TrainerManager(models.Manager):
    def get_top_winners(self, limit=5):
        return list(
            self.annotate(wins=Count("raceentry", filter=Q(raceentry__res_win=True)))
            .order_by("-wins")[:limit]
            .values("name", "wins")
        )


class RaceManager(models.Manager):
    def get_monthly_stats(self, year=2020):
        stats = list(
            self.filter(date__year=year, entries__res_win__isnull=False)
            .annotate(month=ExtractMonth("date"))
            .values("month")
            .annotate(count=Count("id", distinct=True))
            .order_by("month")
        )
        monthly_counts = [0] * 12
        for stat in stats:
            if stat["month"] and 1 <= stat["month"] <= 12:
                monthly_counts[stat["month"] - 1] = stat["count"]
        return monthly_counts


class RaceEntryManager(models.Manager):
    def get_age_distribution(self):
        age_dist = list(
            self.filter(age__isnull=False)
            .values("age")
            .annotate(count=Count("id"))
            .order_by("age")
        )
        age_labels = list(range(2, 9))
        age_counts_dict = {int(a["age"]): a["count"] for a in age_dist}
        return age_labels, [age_counts_dict.get(a, 0) for a in age_labels]


class Horse(models.Model):
    name = models.CharField(max_length=255, unique=True)
    father = models.CharField(max_length=255, blank=True, null=True)
    mother = models.CharField(max_length=255, blank=True, null=True)
    gfather = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name


class Jockey(models.Model):
    name = models.CharField(max_length=255, unique=True)
    objects = JockeyManager()

    def __str__(self):
        return self.name


class Trainer(models.Model):
    name = models.CharField(max_length=255, unique=True)
    objects = TrainerManager()

    def __str__(self):
        return self.name


class Race(models.Model):
    kaggle_rid = models.CharField(max_length=50, unique=True, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="races")
    objects = RaceManager()
    date = models.DateField(null=True, blank=True, db_index=True)
    time = models.TimeField(null=True, blank=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    distance = models.CharField(max_length=50, blank=True, null=True)
    condition = models.CharField(max_length=100, blank=True, null=True)
    race_class = models.CharField(max_length=50, blank=True, null=True)
    winning_time = models.FloatField(null=True, blank=True)
    prize = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.title or 'Race'} at {self.course.name} ({self.date})"


class RaceEntry(models.Model):
    race = models.ForeignKey(Race, on_delete=models.CASCADE, related_name="entries")
    horse = models.ForeignKey(Horse, on_delete=models.CASCADE, related_name="entries")
    objects = RaceEntryManager()
    jockey = models.ForeignKey(Jockey, on_delete=models.SET_NULL, null=True, blank=True)
    trainer = models.ForeignKey(
        Trainer, on_delete=models.SET_NULL, null=True, blank=True
    )

    # Pre-race predictor variables
    age = models.FloatField(null=True, blank=True, db_index=True)
    saddle = models.FloatField(null=True, blank=True)
    weight_carried = models.FloatField(null=True, blank=True)
    decimal_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    is_fav = models.BooleanField(default=False)
    head_gear = models.CharField(max_length=50, blank=True, null=True)

    rpr = models.FloatField(null=True, blank=True)
    tr = models.FloatField(null=True, blank=True)
    or_rating = models.FloatField(null=True, blank=True)

    # Target variables (what we want to predict - will be null for forward.csv data)
    position = models.IntegerField(null=True, blank=True)
    margin = models.FloatField(null=True, blank=True)
    res_win = models.BooleanField(null=True, blank=True, db_index=True)

    class Meta:
        unique_together = ("race", "horse")
        verbose_name_plural = "Race Entries"
        indexes = [
            models.Index(fields=["race", "res_win"]),
        ]

    def __str__(self):
        return f"{self.horse.name} in {self.race}"
