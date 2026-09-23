import json
import logging

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.core.cache import cache

from .models import Race, RaceEntry, Horse, Jockey, Course, Trainer
from .services import MLPredictionService

logger = logging.getLogger(__name__)


def dashboard_view(request: HttpRequest) -> HttpResponse:
    context = cache.get("dashboard_stats_context")

    if not context:
        total_races = Race.objects.count()
        total_horses = Horse.objects.count()
        total_jockeys = Jockey.objects.count()
        total_courses = Course.objects.count()
        total_trainers = Trainer.objects.count()

        monthly_counts = Race.objects.get_monthly_stats(year=2020)

        top_jockeys = Jockey.objects.get_top_winners(limit=5)
        jockey_names = [j["name"] for j in top_jockeys]
        jockey_wins = [j["wins"] for j in top_jockeys]

        top_trainers = Trainer.objects.get_top_winners(limit=5)
        trainer_names = [t["name"] for t in top_trainers]
        trainer_wins = [t["wins"] for t in top_trainers]

        age_labels, age_chart_data = RaceEntry.objects.get_age_distribution()

        context = {
            "total_races": total_races,
            "total_horses": total_horses,
            "total_jockeys": total_jockeys,
            "total_trainers": total_trainers,
            "total_courses": total_courses,
            "monthly_counts_json": json.dumps(monthly_counts),
            "jockey_names_json": json.dumps(jockey_names),
            "jockey_wins_json": json.dumps(jockey_wins),
            "trainer_names_json": json.dumps(trainer_names),
            "trainer_wins_json": json.dumps(trainer_wins),
            "age_labels_json": json.dumps(age_labels),
            "age_chart_data_json": json.dumps(age_chart_data),
        }

        # Cache for 24 hours (86400 seconds)
        cache.set("dashboard_stats_context", context, 86400)
    return render(request, "racing/dashboard.html", context)


def race_center_view(request: HttpRequest) -> HttpResponse:
    valid_dates_qs = (
        Race.objects.filter(date__year=2020, entries__res_win__isnull=False)
        .values_list("date", flat=True)
        .distinct()
        .order_by("date")
    )
    valid_dates = [d.strftime("%Y-%m-%d") for d in valid_dates_qs if d]

    context = {
        "valid_dates_json": json.dumps(valid_dates),
    }
    return render(request, "racing/race_center.html", context)


def races_by_date_api(request: HttpRequest) -> JsonResponse:
    date_str = request.GET.get("date")
    if not date_str:
        return JsonResponse({"error": "Date parameter required"}, status=400)

    races = (
        Race.objects.filter(date=date_str, entries__res_win__isnull=False)
        .distinct()
        .order_by("time", "id")
    )

    data = []
    for r in races:
        title = r.title if r.title else (r.course.name if r.course else "Race")
        data.append({"id": r.id, "title": f"{title} ({r.date})"})

    return JsonResponse({"races": data})


def race_predict_api(request: HttpRequest, id: int) -> JsonResponse:
    race = get_object_or_404(Race, id=id)

    try:
        data = MLPredictionService.predict_race(race)
        return JsonResponse(data)
    except ValueError as e:
        logger.warning(f"Validation error for race prediction (ID {id}): {e}")
        return JsonResponse({"error": str(e)}, status=404)
    except Exception as e:
        logger.error(f"Prediction service failed for race {id}: {e}", exc_info=True)
        return JsonResponse(
            {"error": "Prediction service failed temporarily."}, status=500
        )


def race_details_api(request: HttpRequest, id: int) -> JsonResponse:
    race = get_object_or_404(Race, id=id)

    entries_qs = RaceEntry.objects.filter(race=race).select_related(
        "horse", "jockey", "trainer"
    )
    entries_list = []
    for e in entries_qs:
        entries_list.append(
            {
                "saddle": e.saddle if e.saddle is not None else "-",
                "horse": e.horse.name if e.horse else "Unknown",
                "jockey": e.jockey.name if e.jockey else "Unknown",
                "trainer": e.trainer.name if e.trainer else "Unknown",
                "age": e.age if e.age is not None else "-",
                "weight": e.weight_carried if e.weight_carried is not None else "-",
                "odds": e.decimal_price if e.decimal_price is not None else "-",
                "rpr": e.rpr if e.rpr is not None else "-",
            }
        )

    return JsonResponse(
        {
            "title": race.title if race.title else f"Race at {race.course.name}",
            "course": race.course.name if race.course else "Unknown",
            "date": race.date.strftime("%Y-%m-%d") if race.date else None,
            "time": race.time.strftime("%H:%M") if race.time else None,
            "distance": race.distance or "N/A",
            "condition": race.condition or "N/A",
            "race_class": race.race_class or "N/A",
            "winning_time": race.winning_time or "N/A",
            "prize": race.prize or "N/A",
            "entries": entries_list,
        }
    )
