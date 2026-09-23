import pandas as pd
from django.core.management.base import BaseCommand
from django.db.models import F
from apps.racing.models import RaceEntry
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
from sklearn.metrics import precision_score
import joblib


class Command(BaseCommand):
    help = "Train an XGBoost model on historical data (1990-2019) and evaluate on 2020 racing data."

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS("Starting data extraction from the database...")
        )

        # 1. Query Data
        qs = (
            RaceEntry.objects.select_related(
                "race", "jockey", "trainer", "race__course"
            )
            .annotate(
                race_date=F("race__date"),
                race_distance=F("race__distance"),
                course_name=F("race__course__name"),
                jockey_name=F("jockey__name"),
                trainer_name=F("trainer__name"),
                race_class=F("race__race_class"),
            )
            .filter(race__date__isnull=False, res_win__isnull=False)
            .values(
                "race_id",
                "race_date",
                "course_name",
                "race_distance",
                "race_class",
                "jockey_name",
                "trainer_name",
                "age",
                "weight_carried",
                "decimal_price",
                "is_fav",
                "head_gear",
                "rpr",
                "tr",
                "or_rating",
                "res_win",
            )
        )

        df = pd.DataFrame.from_records(qs)

        if df.empty:
            self.stdout.write(
                self.style.ERROR("No data found! Did you run import_kaggle?")
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Extracted {len(df)} records. Beginning preprocessing..."
            )
        )

        # Convert to datetime and sort
        df["race_date"] = pd.to_datetime(df["race_date"])

        # 2. Temporal Split
        train_mask = df["race_date"] < pd.Timestamp("2020-01-01")
        test_mask = (df["race_date"] >= pd.Timestamp("2020-01-01")) & (
            df["race_date"] < pd.Timestamp("2021-01-01")
        )

        train_df = df[train_mask].copy()
        test_df = df[test_mask].copy()

        self.stdout.write(f"Training shape: {train_df.shape} (1990-2019)")
        self.stdout.write(f"Testing shape: {test_df.shape} (2020)")

        # 3. Handle categorical columns (Label Encoding for simplicity)
        categorical_cols = [
            "course_name",
            "race_distance",
            "race_class",
            "jockey_name",
            "trainer_name",
            "head_gear",
        ]

        label_encoders = {}
        for col in categorical_cols:
            train_df[col] = train_df[col].fillna("Unknown").astype(str)
            test_df[col] = test_df[col].fillna("Unknown").astype(str)

            # Simple Label Encoding
            le = LabelEncoder()
            all_classes = pd.concat([train_df[col], test_df[col]]).unique()
            le.fit(all_classes)

            train_df[col] = le.transform(train_df[col])
            test_df[col] = le.transform(test_df[col])
            label_encoders[col] = le

        # 4. Handle numeric missing values (Fill with median)
        numeric_cols = [
            "age",
            "weight_carried",
            "decimal_price",
            "rpr",
            "tr",
            "or_rating",
        ]

        numeric_medians = {}
        for col in numeric_cols:
            median_val = train_df[col].median()
            train_df[col] = train_df[col].fillna(median_val)
            test_df[col] = test_df[col].fillna(median_val)
            numeric_medians[col] = median_val

        # Convert is_fav boolean to int
        train_df["is_fav"] = train_df["is_fav"].astype(int)
        test_df["is_fav"] = test_df["is_fav"].astype(int)

        # Target variable
        y_train = train_df["res_win"].astype(int)
        y_test = test_df["res_win"].astype(int)

        # Features
        features = categorical_cols + numeric_cols + ["is_fav"]
        X_train = train_df[features]
        X_test = test_df[features]

        # 5. Train XGBoost Model
        from sklearn.model_selection import GridSearchCV

        self.stdout.write(
            self.style.SUCCESS(
                "Tuning XGBoost Classifier with GridSearchCV... (This will take a few minutes)"
            )
        )
        scale_pos_weight = (len(y_train) - y_train.sum()) / max(y_train.sum(), 1)

        base_model = XGBClassifier(
            scale_pos_weight=scale_pos_weight,
            random_state=42,
            n_jobs=-1,
            eval_metric="logloss",
        )

        param_grid = {
            "max_depth": [3, 5, 7],
            "learning_rate": [0.05, 0.1, 0.2],
            "n_estimators": [100, 150, 200],
        }

        grid_search = GridSearchCV(
            estimator=base_model,
            param_grid=param_grid,
            scoring="precision",
            cv=3,
            verbose=1,
            n_jobs=1,  # XGBoost manages its own threads
        )

        grid_search.fit(X_train, y_train)

        self.stdout.write(
            self.style.SUCCESS(f"Best parameters found: {grid_search.best_params_}")
        )
        model = grid_search.best_estimator_

        # 6. Evaluation
        self.stdout.write(self.style.SUCCESS("Evaluating Model on 2020 Data..."))
        y_pred = model.predict(X_test)

        prec = precision_score(y_test, y_pred, zero_division=0)

        self.stdout.write("-" * 50)
        self.stdout.write(
            self.style.SUCCESS(f"PRECISION (Threshold 0.5): {prec * 100:.2f}%")
        )
        self.stdout.write("-" * 50)

        # Race-Wise Evaluation
        self.stdout.write(
            self.style.SUCCESS("Evaluating Race-Wise Top-1 Predictions...")
        )
        test_df["win_prob"] = model.predict_proba(X_test)[:, 1]

        # Group by race_id, pick the horse with highest probability
        idx_max_prob = test_df.groupby("race_id")["win_prob"].idxmax()
        predicted_winners = test_df.loc[idx_max_prob]

        total_races = len(predicted_winners)
        correct_predictions = predicted_winners["res_win"].sum()
        top_1_accuracy = correct_predictions / total_races if total_races > 0 else 0

        self.stdout.write("-" * 50)
        self.stdout.write(
            self.style.SUCCESS(f"Total 2020 Races Evaluated: {total_races}")
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Races Correctly Predicted:  {int(correct_predictions)}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"TOP-1 RACE ACCURACY:        {top_1_accuracy * 100:.2f}%"
            )
        )
        self.stdout.write("-" * 50)

        self.stdout.write(
            "Note: Top-1 Accuracy means the horse the model gave the highest probability to actually won the race."
        )

        # Save LabelEncoder dict, medians and XGBClassifier
        artifacts = {
            "label_encoders": label_encoders,
            "numeric_medians": numeric_medians,
            "features": features,
        }
        joblib.dump(artifacts, "encoders.pkl")
        joblib.dump(model, "xgboost_model.pkl")
        self.stdout.write(
            self.style.SUCCESS(
                "Saved encoders.pkl and xgboost_model.pkl in root folder"
            )
        )
