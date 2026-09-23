import os
import joblib
from django.apps import AppConfig
from django.conf import settings


class RacingConfig(AppConfig):
    name = "apps.racing"

    # Global Singletons
    ml_model = None
    ml_artifacts = None

    def ready(self):
        # Fire once when Django starts (Load into RAM, safely bypass web-thread disk IO)
        encoders_path = os.path.join(settings.BASE_DIR, "encoders.pkl")
        model_path = os.path.join(settings.BASE_DIR, "xgboost_model.pkl")

        if os.path.exists(encoders_path) and os.path.exists(model_path):
            RacingConfig.ml_artifacts = joblib.load(encoders_path)
            RacingConfig.ml_model = joblib.load(model_path)
