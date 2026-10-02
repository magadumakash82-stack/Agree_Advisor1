import io
from datetime import datetime, timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

class ReportGeneratorService:
    """Generates professional PDF agronomic reports for Smart Soil Testing System."""

    @classmethod
    def generate_pdf(cls, device_info: dict, reading_data: dict, health_analysis: dict, crop_results: dict) -> io.BytesIO:
        """Generates a styled PDF report in memory and returns a BytesIO buffer."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        
        # Custom Typography Styles
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            textColor=colors.HexColor('#1b5e20'),
            alignment=1, # Center
            spaceAfter=4
        )

        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=13,
            textColor=colors.HexColor('#4b5563'),
            alignment=1, # Center
            spaceAfter=12
        )

        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor('#2e7d32'),
            spaceBefore=10,
            spaceAfter=6
        )

        body_style = ParagraphStyle(
            'BodyTextCustom',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#1f2937')
        )

        disclaimer_style = ParagraphStyle(
            'DisclaimerText',
            parent=styles['Italic'],
            fontName='Helvetica-Oblique',
            fontSize=8,
            leading=11,
            textColor=colors.HexColor('#6b7280'),
            spaceBefore=10
        )

        story = []

        # 1. Header Banner
        story.append(Paragraph("AgriAdvisor - SOIL HEALTH & CROP OPTIMIZATION REPORT", title_style))
        story.append(Paragraph("IoT-Based Soil Monitoring, Telemetry Analytics & Crop Suitability Platform", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2e7d32'), spaceAfter=10))

        # 2. Metadata / Device Info Grid
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        dev_id = device_info.get("device_id", "SOIL_001")
        dev_name = device_info.get("device_name", "Primary Field Sensor")
        dev_loc = device_info.get("location", "Main Agricultural Plot")
        timestamp_str = reading_data.get("formatted_time", now_str)
        sim_tag = " (Simulated Demo)" if reading_data.get("is_simulated") else " (Live Hardware)"

        meta_data = [
            [
                Paragraph(f"<b>Device ID:</b> {dev_id}{sim_tag}", body_style),
                Paragraph(f"<b>Report Date:</b> {now_str}", body_style)
            ],
            [
                Paragraph(f"<b>Device Name:</b> {dev_name}", body_style),
                Paragraph(f"<b>Reading Time:</b> {timestamp_str}", body_style)
            ],
            [
                Paragraph(f"<b>Field Location:</b> {dev_loc}", body_style),
                Paragraph(f"<b>Health Index:</b> {health_analysis.get('health_index', 'N/A')}% ({health_analysis.get('health_status', 'NORMAL')})", body_style)
            ]
        ]
        meta_table = Table(meta_data, colWidths=[270, 270])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
            ('PADDING', (0,0), (-1,-1), 5),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#86efac')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 10))

        # 3. 7-in-1 Soil Parameters Table
        story.append(Paragraph("1. Soil Parameter Measurements", section_heading))
        
        param_table_data = [
            ["Parameter", "Measured Value", "Unit", "Agronomic Status", "Condition Assessment"]
        ]
        
        params_info = health_analysis.get("parameters", {})
        param_order = [
            ("moisture", "Soil Moisture", "%"),
            ("temperature", "Soil Temperature", "°C"),
            ("ec", "Electrical Conductivity (EC)", "µS/cm"),
            ("ph", "Soil pH", "scale"),
            ("nitrogen", "Nitrogen (N)", "mg/kg"),
            ("phosphorus", "Phosphorus (P)", "mg/kg"),
            ("potassium", "Potassium (K)", "mg/kg")
        ]

        for p_key, p_name, default_unit in param_order:
            val = reading_data.get(p_key, 0.0)
            p_data = params_info.get(p_key, {})
            unit = p_data.get("unit", default_unit)
            status_label = p_data.get("label", "Normal")
            level = p_data.get("level", "normal")
            
            assessment = "Within standard recommended threshold."
            if level == "critical":
                assessment = "Requires immediate agronomic management."
            elif level == "warning":
                assessment = "Mild variance from target optimum."

            param_table_data.append([
                p_name,
                f"{val}",
                unit,
                status_label,
                assessment
            ])

        param_table = Table(param_table_data, colWidths=[130, 80, 60, 110, 160])
        param_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2e7d32')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('ALIGN', (1,0), (2,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
            ('PADDING', (0,0), (-1,-1), 4),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f9fafb')])
        ]))
        story.append(param_table)
        story.append(Spacer(1, 10))

        # 4. Soil Health & Agronomic Recommendations
        story.append(Paragraph("2. Soil Health Assessment & Management Recommendations", section_heading))
        story.append(Paragraph(f"<b>Overall Evaluation:</b> {health_analysis.get('health_summary', '')}", body_style))
        story.append(Spacer(1, 4))

        recs = health_analysis.get("recommendations", [])
        if recs:
            rec_rows = []
            for r in recs[:4]: # top 4 actionable points
                rec_rows.append([
                    Paragraph(f"• <b>{r.get('title', 'Recommendation')}:</b> {r.get('text', '')}", body_style)
                ])
            rec_table = Table(rec_rows, colWidths=[540])
            rec_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
                ('PADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(rec_table)
        story.append(Spacer(1, 10))

        # 5. Crop Suitability Results
        story.append(Paragraph("3. Crop Suitability Analysis", section_heading))
        crops_list = crop_results.get("crops", [])[:6] # Top 6 crops
        
        crop_table_data = [
            ["Crop", "Suitability", "Status", "Water Requirement", "Key Limiting / Favorable Factors"]
        ]

        for c in crops_list:
            c_name = c.get("crop_name", "")
            c_score = f"{c.get('suitability_percent', 0)}%"
            c_status = c.get("suitability_label", "")
            c_water = c.get("water_requirement", "Moderate")
            
            # Identify top favorable or limiting parameter
            c_params = c.get("parameters", {})
            favorable = []
            limiting = []
            for p, p_res in c_params.items():
                if p_res.get("score", 0) >= 95:
                    favorable.append(p.upper())
                elif p_res.get("score", 0) < 65:
                    limiting.append(p.upper())
            
            factor_summary = ""
            if favorable:
                factor_summary += f"Optimum: {', '.join(favorable[:2])}. "
            if limiting:
                factor_summary += f"Limiting: {', '.join(limiting[:2])}."
            if not factor_summary:
                factor_summary = "Even parameter distribution."

            crop_table_data.append([
                c_name,
                c_score,
                c_status,
                c_water,
                factor_summary
            ])

        crop_table = Table(crop_table_data, colWidths=[100, 70, 100, 110, 160])
        crop_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#15803d')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 8.5),
            ('ALIGN', (1,0), (1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e5e7eb')),
            ('PADDING', (0,0), (-1,-1), 4),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f9fafb')])
        ]))
        story.append(crop_table)
        story.append(Spacer(1, 12))

        # 6. Official Disclaimer
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#9ca3af'), spaceAfter=6))
        story.append(Paragraph(
            "<b>Disclaimer:</b> Indicative recommendation based on entered/measured soil parameters. "
            "Recommendations are indicative and should be validated using local agricultural guidance "
            "and, where appropriate, certified laboratory soil testing before financial or fertilizer application decisions.",
            disclaimer_style
        ))

        doc.build(story)
        buffer.seek(0)
        return buffer
