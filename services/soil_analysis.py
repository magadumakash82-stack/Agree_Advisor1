from typing import Dict, Any, List
from config import Config

class SoilAnalysisService:
    """Evaluates soil readings, health index, alerts, and parameter guidance."""

    DISCLAIMER = (
        "Recommendations are indicative and should be validated using local "
        "agricultural guidance and, where appropriate, certified laboratory soil testing."
    )

    @classmethod
    def get_thresholds(cls) -> Dict[str, Any]:
        return Config.SOIL_PARAM_THRESHOLDS

    @classmethod
    def analyze_parameter(cls, param_key: str, value: float) -> Dict[str, Any]:
        """Classifies an individual parameter as CRITICAL_LOW, LOW, NORMAL, HIGH, or CRITICAL_HIGH."""
        thresholds = cls.get_thresholds().get(param_key)
        if not thresholds:
            return {"status": "NORMAL", "label": "Normal", "level": "normal", "score": 100}

        val = float(value)
        c_low = thresholds["critical_low"]
        low = thresholds["low"]
        n_min = thresholds["normal_min"]
        n_max = thresholds["normal_max"]
        high = thresholds["high"]
        c_high = thresholds["critical_high"]

        if val < c_low:
            return {"status": "CRITICAL_LOW", "label": "Critical Low", "level": "critical", "score": 30}
        elif val < low:
            return {"status": "LOW", "label": "Low", "level": "warning", "score": 60}
        elif val < n_min:
            return {"status": "SLIGHTLY_LOW", "label": "Slightly Low", "level": "warning", "score": 80}
        elif val <= n_max:
            return {"status": "NORMAL", "label": "Normal / Optimal", "level": "normal", "score": 100}
        elif val <= high:
            return {"status": "SLIGHTLY_HIGH", "label": "Slightly High", "level": "warning", "score": 80}
        elif val <= c_high:
            return {"status": "HIGH", "label": "High", "level": "warning", "score": 60}
        else:
            return {"status": "CRITICAL_HIGH", "label": "Critical High", "level": "critical", "score": 30}

    @classmethod
    def evaluate_reading(cls, reading: Dict[str, Any]) -> Dict[str, Any]:
        """Performs comprehensive soil health analysis and generates recommendations and alerts."""
        analysis_params = {}
        total_score = 0
        param_keys = ["moisture", "temperature", "ec", "ph", "nitrogen", "phosphorus", "potassium"]
        alerts: List[Dict[str, str]] = []
        recommendations: List[Dict[str, str]] = []

        for key in param_keys:
            val = float(reading.get(key, 0.0))
            param_meta = cls.get_thresholds().get(key, {})
            unit = param_meta.get("unit", "")
            name = param_meta.get("name", key.capitalize())

            eval_res = cls.analyze_parameter(key, val)
            total_score += eval_res["score"]

            analysis_params[key] = {
                "name": name,
                "value": val,
                "unit": unit,
                "status": eval_res["status"],
                "label": eval_res["label"],
                "level": eval_res["level"],
                "score": eval_res["score"]
            }

            # Generate alerts for non-optimal values
            if eval_res["level"] == "critical":
                alerts.append({
                    "severity": "critical",
                    "parameter": name,
                    "message": f"{name} is at a critical level ({val} {unit}). Immediate agronomic intervention recommended."
                })
            elif eval_res["level"] == "warning":
                alerts.append({
                    "severity": "warning",
                    "parameter": name,
                    "message": f"{name} is {eval_res['label'].lower()} ({val} {unit}). Monitor and calibrate inputs."
                })

        # Calculate overall Soil Health Index (0 - 100%)
        health_index = round(total_score / len(param_keys), 1)

        if health_index >= 85:
            health_status = "EXCELLENT"
            health_summary = "Soil condition is well-balanced across all vital physical, electrical, and primary nutrient parameters."
        elif health_index >= 70:
            health_status = "GOOD"
            health_summary = "Soil demonstrates fair fertility with minor parameters requiring mild adjustment."
        elif health_index >= 50:
            health_status = "MODERATE"
            health_summary = "Moderate soil imbalance detected. Specific nutrient replenishment or moisture management is advisable."
        else:
            health_status = "POOR"
            health_summary = "Substantial soil limitations observed. Soil amendment and reclamation measures should be evaluated."

        # Actionable Agronomic Guidance
        m_val = reading.get("moisture", 0.0)
        ph_val = reading.get("ph", 7.0)
        ec_val = reading.get("ec", 0.0)
        n_val = reading.get("nitrogen", 0.0)
        p_val = reading.get("phosphorus", 0.0)
        k_val = reading.get("potassium", 0.0)
        t_val = reading.get("temperature", 0.0)

        # Moisture recommendations
        if m_val < 35.0:
            recommendations.append({
                "category": "Irrigation",
                "title": "Low Soil Moisture Detected",
                "text": "Moisture is below the configured target range. Consider evaluating irrigation scheduling or applying organic mulch to improve moisture retention."
            })
        elif m_val > 80.0:
            recommendations.append({
                "category": "Drainage",
                "title": "High Soil Saturation",
                "text": "Soil is approaching waterlogged conditions. Verify drainage channels to prevent root hypoxia and fungal infestations."
            })

        # pH recommendations
        if ph_val < 5.8:
            recommendations.append({
                "category": "Soil Chemistry",
                "title": "Acidic Soil Condition",
                "text": f"Soil pH ({ph_val}) is acidic. Consider agricultural lime (calcium carbonate) or dolomite application after verifying soil buffering capacity."
            })
        elif ph_val > 7.8:
            recommendations.append({
                "category": "Soil Chemistry",
                "title": "Alkaline / Calcareous Soil",
                "text": f"Soil pH ({ph_val}) is alkaline. Consider gypsum application, sulfur amendment, or organic composting to enhance nutrient availability."
            })

        # EC recommendations
        if ec_val > 2200.0:
            recommendations.append({
                "category": "Salinity Management",
                "title": "Elevated Electrical Conductivity (EC)",
                "text": f"EC is {ec_val} µS/cm indicating elevated soluble salt concentrations. Consider leaching irrigation if drainage permits and limit saline fertilizer salts."
            })

        # Primary nutrients (N-P-K) recommendations
        if n_val < 35.0:
            recommendations.append({
                "category": "Nutrient Management (N)",
                "title": "Nitrogen Below Target Range",
                "text": "Nitrogen is below the configured target range. Consider confirming nutrient status with a validated soil test before applying nitrogenous fertilizer or legume cover cropping."
            })
        elif n_val > 90.0:
            recommendations.append({
                "category": "Nutrient Management (N)",
                "title": "Excessive Nitrogen Levels",
                "text": "Nitrogen is elevated. Avoid further urea/ammonium supplementation to reduce vegetative overgrowth risk and groundwater leaching."
            })

        if p_val < 25.0:
            recommendations.append({
                "category": "Nutrient Management (P)",
                "title": "Phosphorus Below Target Range",
                "text": "Phosphorus levels are suboptimal for strong root development. Consider phosphate solubilizing biofertilizers or targeted SSP/DAP upon agronomic validation."
            })

        if k_val < 40.0:
            recommendations.append({
                "category": "Nutrient Management (K)",
                "title": "Potassium Below Target Range",
                "text": "Potassium is low. Potassium regulates plant water potential and disease resistance; evaluate muriate of potash (MOP) or sulfate of potash (SOP) needs."
            })

        # Temperature
        if t_val > 35.0:
            recommendations.append({
                "category": "Thermal Stress",
                "title": "Elevated Soil Temperature",
                "text": f"Soil temperature ({t_val} °C) is high. Mulching and shade canopy management can protect shallow root systems and microbial activity."
            })

        if not recommendations:
            recommendations.append({
                "category": "Maintenance",
                "title": "Balanced Soil Parameters",
                "text": "Measured parameters lie within standard vegetative ranges. Maintain standard organic replenishment and moisture maintenance."
            })

        return {
            "health_index": health_index,
            "health_status": health_status,
            "health_summary": health_summary,
            "parameters": analysis_params,
            "alerts": alerts,
            "recommendations": recommendations,
            "disclaimer": cls.DISCLAIMER
        }
