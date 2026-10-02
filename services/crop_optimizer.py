import json
from pathlib import Path
from typing import Dict, Any, List
from config import Config

class CropOptimizerService:
    """Crop Suitability Optimization Engine with transparent parameter scoring."""

    DISCLAIMER = (
        "Indicative recommendation based on entered/measured soil parameters. "
        "Recommendations are indicative and should be validated using local agricultural guidance "
        "and, where appropriate, laboratory soil testing."
    )

    _crops_cache = None

    @classmethod
    def load_crops(cls) -> List[Dict[str, Any]]:
        """Loads crop profiles from data/crops.json."""
        if cls._crops_cache is not None:
            return cls._crops_cache

        crops_file = Config.DATA_DIR / "crops.json"
        if crops_file.exists():
            with open(crops_file, "r", encoding="utf-8") as f:
                cls._crops_cache = json.load(f)
        else:
            cls._crops_cache = []
        return cls._crops_cache

    @classmethod
    def reload_crops(cls):
        cls._crops_cache = None
        return cls.load_crops()

    @classmethod
    def calculate_param_score(cls, actual: float, min_val: float, max_val: float, param_name: str) -> Dict[str, Any]:
        """
        Calculates transparency score (0 - 100) and status for a single parameter.
        Within [min_val, max_val] => 100% (Optimal/Suitable)
        Close to range => Moderate (70-90%)
        Farther => Low (40-69%)
        Extreme => Critical/Incompatible (<40%)
        """
        actual = float(actual)
        min_val = float(min_val)
        max_val = float(max_val)
        span = max_val - min_val if max_val > min_val else 1.0

        if min_val <= actual <= max_val:
            score = 100.0
            status = "Suitable"
            details = f"Optimal (Measured: {actual}, Target: {min_val} - {max_val})"
            grade = "optimal"
        elif actual < min_val:
            deficit = min_val - actual
            penalty = (deficit / (span * 0.5)) * 40.0
            score = max(15.0, 100.0 - penalty)
            if score >= 75.0:
                status = "Moderate"
                grade = "moderate"
            elif score >= 50.0:
                status = "Suboptimal"
                grade = "suboptimal"
            else:
                status = "Low"
                grade = "low"
            details = f"Deficit by {round(deficit, 1)} (Measured: {actual}, Min: {min_val})"
        else:
            excess = actual - max_val
            penalty = (excess / (span * 0.5)) * 40.0
            score = max(15.0, 100.0 - penalty)
            if score >= 75.0:
                status = "Moderate"
                grade = "moderate"
            elif score >= 50.0:
                status = "Suboptimal"
                grade = "suboptimal"
            else:
                status = "High / Incompatible"
                grade = "low"
            details = f"Excess by {round(excess, 1)} (Measured: {actual}, Max: {max_val})"

        return {
            "score": round(score, 1),
            "status": status,
            "grade": grade,
            "details": details,
            "min": min_val,
            "max": max_val,
            "actual": actual
        }

    @classmethod
    def evaluate_crop(cls, crop: Dict[str, Any], soil_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluates a single crop against current soil conditions with transparent parameter breakdown."""
        param_weights = {
            "ph": 0.20,           # Soil pH is crucial for nutrient uptake
            "moisture": 0.18,     # Water availability
            "ec": 0.14,           # Salinity tolerance
            "nitrogen": 0.14,     # Primary macronutrient
            "phosphorus": 0.12,   # Root and flower formation
            "potassium": 0.12,    # Disease and water regulation
            "temperature": 0.10   # Environmental suitability
        }

        evaluations = {}
        weighted_score_sum = 0.0

        for param, weight in param_weights.items():
            actual = float(soil_data.get(param, 0.0))
            min_val = float(crop.get(f"{param}_min", 0.0))
            max_val = float(crop.get(f"{param}_max", 100.0))

            param_eval = cls.calculate_param_score(actual, min_val, max_val, param)
            evaluations[param] = param_eval
            weighted_score_sum += param_eval["score"] * weight

        suitability_percent = round(weighted_score_sum, 1)

        # Suitability class & descriptive badge
        if suitability_percent >= 85:
            suitability_label = "Highly Suitable"
            badge_class = "success"
        elif suitability_percent >= 70:
            suitability_label = "Suitable"
            badge_class = "primary"
        elif suitability_percent >= 55:
            suitability_label = "Moderately Suitable"
            badge_class = "warning"
        else:
            suitability_label = "Low Suitability"
            badge_class = "danger"

        return {
            "crop_id": crop.get("id"),
            "crop_name": crop.get("name"),
            "scientific_name": crop.get("scientific_name", ""),
            "category": crop.get("category", "General"),
            "description": crop.get("description", ""),
            "water_requirement": crop.get("water_requirement", "Moderate"),
            "preferred_soil": crop.get("preferred_soil", "Loam"),
            "suitability_percent": suitability_percent,
            "suitability_label": suitability_label,
            "badge_class": badge_class,
            "parameters": evaluations
        }

    @classmethod
    def evaluate_all(cls, soil_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluates all configured crops and ranks them by suitability percentage."""
        crops = cls.load_crops()
        results = []

        for crop in crops:
            res = cls.evaluate_crop(crop, soil_data)
            results.append(res)

        # Rank strictly by calculated suitability percentage descending
        results.sort(key=lambda x: x["suitability_percent"], reverse=True)

        return {
            "crops": results,
            "soil_measured": soil_data,
            "total_crops": len(results),
            "disclaimer": cls.DISCLAIMER
        }
