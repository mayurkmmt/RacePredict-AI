import logging
from typing import Any, Dict
import pandas as pd
from django.apps import apps
from apps.racing.models import RaceEntry, Race

logger = logging.getLogger(__name__)


class MLPredictionService:
    @staticmethod
    def predict_race(race: Race, top_n: int = 3) -> Dict[str, Any]:
        """
        Orchestrates Data gathering, Pandas preprocessing, and XGBoost Inference.
        Returns serialized dict of Predicted and Actual Results.
        """
        logger.info(f"Starting ML inference for Race ID: {race.id}")
        config = apps.get_app_config("racing")
        if not config.ml_model or not config.ml_artifacts:
            logger.error("Model artifacts not found or failed to boot in AppConfig.")
            raise ValueError("Model files not found or failed to boot in AppConfig.")

        model = config.ml_model
        artifacts = config.ml_artifacts

        label_encoders = artifacts["label_encoders"]
        numeric_medians = artifacts["numeric_medians"]
        features = artifacts["features"]

        entries = RaceEntry.objects.filter(race=race).select_related(
            "horse", "jockey", "trainer", "race__course"
        )
        if not entries:
            raise ValueError("No entries found for this race.")

        data = []
        for entry in entries:
            data.append(
                {
                    "horse_name": entry.horse.name if entry.horse else "Unknown",
                    "course_name": entry.race.course.name
                    if entry.race.course
                    else "Unknown",
                    "race_distance": entry.race.distance,
                    "race_class": entry.race.race_class,
                    "jockey_name": entry.jockey.name if entry.jockey else "Unknown",
                    "trainer_name": entry.trainer.name if entry.trainer else "Unknown",
                    "head_gear": entry.head_gear,
                    "age": entry.age,
                    "weight_carried": entry.weight_carried,
                    "decimal_price": entry.decimal_price,
                    "is_fav": int(bool(entry.is_fav)),
                    "rpr": entry.rpr,
                    "tr": entry.tr,
                    "or_rating": entry.or_rating,
                    "res_win": entry.res_win,
                    "position": entry.position,
                }
            )

        df = pd.DataFrame(data)

        # Categorical processing
        categorical_cols = [
            "course_name",
            "race_distance",
            "race_class",
            "jockey_name",
            "trainer_name",
            "head_gear",
        ]
        for col in categorical_cols:
            df[col] = df[col].fillna("Unknown").astype(str)
            le = label_encoders.get(col)
            if le:
                known_mask = df[col].isin(le.classes_)
                if not known_mask.all():
                    df.loc[~known_mask, col] = le.classes_[0]
                df[col] = le.transform(df[col])

        # Numeric processing
        numeric_cols = [
            "age",
            "weight_carried",
            "decimal_price",
            "rpr",
            "tr",
            "or_rating",
        ]
        for col in numeric_cols:
            median_val = numeric_medians.get(col, 0)
            df[col] = df[col].fillna(median_val).astype(float)

        # Inference
        X = df[features]
        prob = model.predict_proba(X)[:, 1]
        df["prob"] = prob

        # Determine predictions (Top N)
        df_sorted_pred = df.sort_values(by="prob", ascending=False)
        top_pred = df_sorted_pred.head(top_n).to_dict("records")

        predicted_horses = [
            {
                "position": i + 1,
                "horse_name": row["horse_name"],
                "prob": round(row["prob"] * 100, 2),
            }
            for i, row in enumerate(top_pred)
        ]

        # Determine actuals
        actual_horses = []
        df_actual = df[df["position"].notnull()]
        if not df_actual.empty:
            df_sorted_actual = df_actual.sort_values(by="position", ascending=True)
            top_actual_rows = df_sorted_actual.head(top_n).to_dict("records")
            actual_horses = [
                {"position": int(row["position"]), "horse_name": row["horse_name"]}
                for row in top_actual_rows
            ]
        else:
            df_actual_win = df[df["res_win"] == 1]
            actual_horses = [
                {"position": 1, "horse_name": row["horse_name"]}
                for row in df_actual_win.to_dict("records")
            ]

        return {
            "predicted": predicted_horses,
            "actual": actual_horses,
            "race_title": race.title if race.title else f"Race at {race.course.name}",
        }
