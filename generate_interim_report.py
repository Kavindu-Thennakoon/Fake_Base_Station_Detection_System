"""
Generate Interim Report for COM4901 — Detection of Fake Base Stations
Using Machine Learning on LTE/5G Measurement Reports with an Explainable
Web-Based System.

Output: Interim_Report_14512.docx
"""

from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import os

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "Interim_Report_14512.docx")


def set_cell_shading(cell, color):
    """Apply shading to a table cell."""
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), color)
    shading.set(qn("w:val"), "clear")
    cell._tc.get_or_add_tcPr().append(shading)


def set_paragraph_spacing(paragraph, before=0, after=0, line_spacing=1.5):
    """Set paragraph spacing."""
    pf = paragraph.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line_spacing


def add_heading_styled(doc, text, level=1):
    """Add heading with Times New Roman font."""
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.name = "Times New Roman"
        run.font.color.rgb = RGBColor(0, 0, 0)
    return h


def add_paragraph_styled(doc, text, bold=False, italic=False, font_size=12, alignment=None):
    """Add a paragraph with standard formatting."""
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(font_size)
    run.bold = bold
    run.italic = italic
    if alignment:
        p.alignment = alignment
    set_paragraph_spacing(p, before=0, after=6, line_spacing=1.5)
    return p


def add_bullet(doc, text, level=0):
    """Add a bullet point."""
    p = doc.add_paragraph(style="List Bullet")
    p.clear()
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    if level > 0:
        p.paragraph_format.left_indent = Inches(0.5 * level)
    set_paragraph_spacing(p, before=0, after=3, line_spacing=1.5)
    return p


def add_table(doc, headers, rows, col_widths=None):
    """Add a formatted table."""
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    # Header row
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in p.runs:
                run.font.name = "Times New Roman"
                run.font.size = Pt(10)
                run.bold = True
        set_cell_shading(cell, "D9E2F3")
    # Data rows
    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = str(val)
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(10)
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Inches(w)
    return table


def build_report():
    doc = Document()

    # ── Page Setup ──
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # ── Default Style ──
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Times New Roman"
    font.size = Pt(12)
    style.paragraph_format.line_spacing = 1.5

    # ── Configure heading styles ──
    for level in range(1, 4):
        hs = doc.styles[f"Heading {level}"]
        hs.font.name = "Times New Roman"
        hs.font.color.rgb = RGBColor(0, 0, 0)

    # ====================================================================
    # 1. TITLE PAGE
    # ====================================================================
    for _ in range(4):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Faculty of Computer Science and Engineering")
    run.font.name = "Times New Roman"
    run.font.size = Pt(14)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Department of Computer Science")
    run.font.name = "Times New Roman"
    run.font.size = Pt(14)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("BSc (Hons) in Computer Networks and Cyber Security")
    run.font.name = "Times New Roman"
    run.font.size = Pt(13)

    doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("INTERIM REPORT")
    run.font.name = "Times New Roman"
    run.font.size = Pt(22)
    run.bold = True

    doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(
        "Detection of Fake Base Stations Using Machine Learning on\n"
        "LTE/5G Measurement Reports with an Explainable Web-Based System"
    )
    run.font.name = "Times New Roman"
    run.font.size = Pt(16)
    run.bold = True

    for _ in range(3):
        doc.add_paragraph()

    details = [
        ("Student Name:", "T.M.K.I. Thennakoon"),
        ("Registration No:", "14512"),
        ("Module Code:", "COM4901"),
        ("Supervisor:", "Mr. Tharindu De Zoysa"),
        ("Faculty:", "Faculty of Computer Science and Engineering, KIU"),
        ("Submission Date:", "29 June 2026"),
    ]
    for label, value in details:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_l = p.add_run(label + " ")
        run_l.font.name = "Times New Roman"
        run_l.font.size = Pt(12)
        run_l.bold = True
        run_v = p.add_run(value)
        run_v.font.name = "Times New Roman"
        run_v.font.size = Pt(12)

    doc.add_page_break()

    # ====================================================================
    # TABLE OF CONTENTS (placeholder)
    # ====================================================================
    add_heading_styled(doc, "Table of Contents", level=1)
    toc_items = [
        "1. Introduction",
        "   1.1 Background and Context",
        "   1.2 Problem Statement",
        "   1.3 Project Aim and Objectives",
        "2. Progress Summary",
        "   2.1 Tasks Completed",
        "   2.2 Current Project Status",
        "   2.3 Evidence of Progress",
        "3. Literature Review Progress",
        "   3.1 Summary of Key Literature",
        "   3.2 Theoretical Foundation",
        "   3.3 Research Gap Justification",
        "4. Methodology / Solution Approach",
        "   4.1 System Development Methodology",
        "   4.2 Data Collection and Processing",
        "   4.3 Tools, Technologies, and Justification",
        "5. Design and Implementation Progress",
        "   5.1 System Architecture",
        "   5.2 ML Pipeline Implementation",
        "   5.3 Django Backend Implementation",
        "   5.4 React Frontend Implementation",
        "   5.5 PowerBI Integration",
        "6. Testing / Evaluation Plan (Draft)",
        "   6.1 Proposed Testing Strategy",
        "   6.2 Evaluation Metrics",
        "   6.3 Planned Experiments",
        "7. Challenges and Risk Management",
        "8. Revised Work Plan",
        "9. Conclusion",
        "10. References",
        "11. Appendices",
    ]
    for item in toc_items:
        p = doc.add_paragraph()
        run = p.add_run(item)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        set_paragraph_spacing(p, before=0, after=2, line_spacing=1.15)

    doc.add_page_break()

    # ====================================================================
    # 2. INTRODUCTION
    # ====================================================================
    add_heading_styled(doc, "1. Introduction", level=1)

    add_heading_styled(doc, "1.1 Background and Context", level=2)
    add_paragraph_styled(doc,
        "Mobile communication networks are a critical infrastructure underpinning everything from "
        "emergency services to financial transactions. With the evolution from LTE to 5G, the radio "
        "access interface introduces new capabilities but also perpetuates fundamental vulnerabilities. "
        "Since User Equipment (UE) inherently depends on measured radio signal strengths to connect "
        "to the strongest available cell, adversaries can exploit this process by deploying Fake Base "
        "Stations (FBS). Also known as IMSI catchers or rogue base stations, FBS devices masquerade "
        "as legitimate network nodes to intercept communications, downgrade encryption protocols, and "
        "launch sophisticated phishing attacks [1][2]."
    )
    add_paragraph_styled(doc,
        "Traditional FBS detection mechanisms rely on manual radio scanning or rigid, rule-based "
        "network Key Performance Indicators (KPIs). These reactive approaches are increasingly "
        "inadequate against advanced FBS attacks that can mimic legitimate network traffic, frequently "
        "suffering from high false-positive rates and delayed threat remediation [2][3]. The expanding "
        "density of 5G small cells further compounds this challenge, creating an urgent need for "
        "automated, intelligent detection systems."
    )
    add_paragraph_styled(doc,
        "This project addresses this gap by developing a proactive, machine learning-driven detection "
        "system that operates entirely on the network side. By leveraging standard LTE/5G Measurement "
        "Reports (MRs)—the radio telemetry that mobile devices continuously generate—the system can "
        "analyse the radio environment and detect anomalous radio signatures without requiring any "
        "hardware modifications to subscriber devices. In the current implementation, the system "
        "ingests historical MR data exported as CSV files from Dialog Axiata PLC's network for "
        "offline model training and batch anomaly detection. The system integrates an explainable "
        "Django web application for alert management and a Microsoft PowerBI analytics layer for "
        "large-scale forensic investigation, geographic heatmapping, and long-term threat trend analysis."
    )

    add_heading_styled(doc, "1.2 Problem Statement", level=2)
    add_paragraph_styled(doc,
        "Fake Base Stations (FBS) exploit the cellular network architecture by broadcasting artificially "
        "strong signals to hijack connections with User Equipment (UE), enabling severe security attacks "
        "including call interception, identity theft, and service denial [3][4]. The existing "
        "countermeasures—manual radio scanning and strict rule-based network KPIs—are demonstrably "
        "ineffective against modern FBS evasion techniques such as mobile operation, spoofed Cell IDs, "
        "and intermittent broadcasting [2]."
    )
    add_paragraph_styled(doc,
        "Moreover, these reactive approaches fail to exploit the rich, real-time radio telemetry readily "
        "available in standard LTE/5G Measurement Reports (MRs). While Machine Learning (ML) "
        "applied to this MR data offers proactive identification of hidden FBS signatures, purely "
        "algorithmic solutions suffer from a critical 'black-box' interpretability gap. Network operators "
        "cannot confidently execute mitigation procedures—such as blocking a suspicious node—without "
        "clear, visual explanations of why an anomaly was flagged."
    )
    add_paragraph_styled(doc,
        "Consequently, there is an acute need for a network-side automated ML system capable of both "
        "detecting FBS anomalies from MR data and transforming complex algorithmic outputs into "
        "actionable visual intelligence. This project bridges the gap between theoretical algorithmic "
        "detection and practical, trustworthy network security operations."
    )

    add_heading_styled(doc, "1.3 Project Aim and Objectives", level=2)
    add_paragraph_styled(doc,
        "The primary aim of this project is to develop a proactive, network-side Machine Learning "
        "system that effectively detects Fake Base Station anomalies using standard LTE/5G Measurement "
        "Reports and converts algorithmic findings into actionable, explainable visual intelligence "
        "through an integrated Django web application and Microsoft PowerBI dashboards.",
        bold=False
    )

    add_paragraph_styled(doc, "The five specific research objectives are:", bold=True)

    objectives = [
        "Objective 1 – Data Engineering and Feature Extraction: To process and preprocess standard "
        "LTE/5G Measurement Report telemetry (RSRP, RSRQ, neighbor-cell transition patterns) to "
        "extract features indicative of rogue base station operation and evasion behaviour.",
        "Objective 2 – Anomaly Detection Model Development: To design, train, and optimize an "
        "unsupervised machine learning model (Robust Random Cut Forest) that detects abnormal radio "
        "signatures and dynamic FBS behaviours while maintaining a low false-positive rate.",
        "Objective 3 – Explainable Alert System: To develop a Django-based web application serving "
        "as the operational interface, providing real-time alert handling with clear, feature-level "
        "explanations of why each anomaly was flagged.",
        "Objective 4 – Advanced Visual Analytics: To integrate Microsoft PowerBI for interactive, "
        "large-scale forensic dashboards including geographic FBS vulnerability heatmaps and long-term "
        "network threat trend visualizations.",
        "Objective 5 – System Evaluation and Validation: To rigorously assess the functionality, "
        "precision, and operational utility of the complete detection and visualization system under "
        "simulated FBS attack conditions.",
    ]
    for obj in objectives:
        add_bullet(doc, obj)

    doc.add_page_break()

    # ====================================================================
    # 3. PROGRESS SUMMARY
    # ====================================================================
    add_heading_styled(doc, "2. Progress Summary", level=1)

    add_heading_styled(doc, "2.1 Tasks Completed So Far", level=2)
    add_paragraph_styled(doc,
        "The following table summarizes the tasks completed against each research objective as of the "
        "interim submission date (29 June 2026):"
    )

    add_table(doc,
        ["#", "Research Objective", "Implementation Artefact", "Status"],
        [
            ["1", "Data Engineering Pipeline",
             "backend/detection/services/ml_bridge.py — CSV ingestion, feature engineering, per-cell baseline computation integrated within Django on 46M rows of Dialog Axiata MR data",
             "Completed"],
            ["2", "Anomaly Detection Model",
             "MLBridge service (1,011 lines) — per-cell CellModel training, two-layer detection (RRCF CoDisp + Z-Score), baseline statistics stored in Django ORM",
             "Completed"],
            ["3", "Explainable Django Alert System",
             "backend/ — REST API with DRF, 3-level XAI (per-anomaly, per-cell, per-neighbor), alert lifecycle with full audit trail, 9 Django models",
             "Completed"],
            ["4", "Interactive Visualization + PowerBI",
             "React SPA (13 pages), Leaflet map, Recharts analytics; PowerBI export endpoints (4 M-query files) with CSV/JSON formats",
             "Completed"],
            ["5", "System Evaluation",
             "evaluate_model.py — precision/recall/F1 framework with simulated FBS attack scenarios (IMSI catcher, downgrade, neighbor spoofing)",
             "In Progress"],
        ],
        col_widths=[0.3, 1.5, 3.0, 0.9]
    )

    add_heading_styled(doc, "2.2 Current Project Status", level=2)
    add_paragraph_styled(doc,
        "As of the interim submission, the project has achieved approximately 80% overall completion. "
        "All core system components—the ML detection engine, the Django REST API backend, the React "
        "frontend dashboard, and the PowerBI integration layer—have been fully developed and are "
        "functionally operational. The system has been successfully deployed in a local development "
        "environment where detection runs can be triggered through the web interface, anomalies are "
        "detected, alerts are generated with explainable reasoning, and results are visualized both "
        "in the React dashboard and via PowerBI connectors."
    )
    add_paragraph_styled(doc,
        "The remaining 20% of the project focuses on: (a) comprehensive model evaluation using "
        "diverse simulated FBS attack scenarios with rigorous statistical analysis; (b) system "
        "optimization and false-positive reduction testing; (c) final PowerBI dashboard design and "
        "geographic heatmap refinement; and (d) the completion of all academic documentation including "
        "the final research report."
    )

    add_heading_styled(doc, "2.3 Evidence of Progress", level=2)
    add_paragraph_styled(doc,
        "The following artefacts serve as concrete evidence of project progress:"
    )
    evidence = [
        "GitHub Repository: Full version-controlled codebase with 50+ commits across backend, frontend, and ML service modules.",
        "Working Prototype: A fully functional two-tier web application (React + Django with integrated ML) with 13 interactive pages.",
        "Database: SQLite database (22.7 MB) containing trained CellModel baselines, detection run history, anomaly records, and alert data.",
        "53 Automated Tests: Backend test suite covering authentication flow, detection models, alert lifecycle, analytics endpoints, and CSV upload validation.",
        "Integrated ML Engine: MLBridge service (1,011 lines) with CSV-based training and Z-score detection embedded within the Django backend.",
        "Documentation: 5 technical documents (architecture, API reference, deployment guide, user manual, PowerBI setup).",
        "Preliminary Evaluation: Demo-mode evaluation showing Precision 0.756, Recall 0.868, F1 0.808, Accuracy 93.8%.",
    ]
    for e in evidence:
        add_bullet(doc, e)

    doc.add_page_break()

    # ====================================================================
    # 4. LITERATURE REVIEW PROGRESS
    # ====================================================================
    add_heading_styled(doc, "3. Literature Review Progress", level=1)

    add_heading_styled(doc, "3.1 Summary of Key Literature Identified", level=2)
    add_paragraph_styled(doc,
        "A comprehensive literature survey has been conducted covering five major areas of FBS "
        "detection research. The following table summarizes the key works identified:"
    )

    add_table(doc,
        ["Author(s)", "Year", "Approach", "Key Finding"],
        [
            ["Miao et al. [1]", "2022",
             "UE-side rule-based detection with hardcoded signal thresholds",
             "Effective against primitive attacks but requires firmware updates and cannot keep pace with sophisticated evasion strategies."],
            ["Shin et al. [2]", "2022",
             "Network-level ANR protocol in 5G SON to detect PCI duplication",
             "Protocol-correct but imposes enormous processing overhead due to active verification of all duplicated PCIs."],
            ["Purification et al. [3]", "2024",
             "UE-based behavioural analysis measuring connection duration and registration attempts + active link routing defense",
             "Proactive defense including link routing to known legitimate base stations; however, requires per-device software updates."],
            ["Sun et al. [4]", "2024",
             "Temporal Graph Isolation Forest + Local Outlier Factor (TGIF-LOF) ensemble using MR data",
             "Network-side ML ensemble using RSRP/SINR with PageRank-based handoff analysis; achieves low false-positive rates."],
            ["Karaçay et al. [5]", "2021",
             "Network-based trilateration using MR RSRP for FBS localization",
             "Demonstrates that MR signal measurements are rich enough to both detect and physically locate FBS without GPS."],
        ],
        col_widths=[1.2, 0.5, 2.2, 2.6]
    )

    add_heading_styled(doc, "3.2 Theoretical and Conceptual Foundation", level=2)
    add_paragraph_styled(doc,
        "The theoretical foundation of this project rests on three pillars:"
    )
    pillars = [
        "Unsupervised Anomaly Detection Theory: The Robust Random Cut Forest (RRCF) algorithm, "
        "proposed by Guha et al. (2016), provides a principled framework for streaming anomaly "
        "detection. Unlike Isolation Forest, RRCF uses Collusive Displacement (CoDisp) as its "
        "anomaly score, which is robust to masking effects in high-dimensional data. This is "
        "particularly suited for FBS detection where malicious signals may attempt to blend with "
        "legitimate network traffic.",
        "Radio Propagation and Measurement Report Standards: LTE/5G Measurement Reports contain "
        "standardized radio metrics defined in 3GPP TS 36.331 and TS 38.331, including Reference "
        "Signal Received Power (RSRP), Reference Signal Received Quality (RSRQ), and neighbor cell "
        "identifiers. These metrics follow predictable propagation patterns (path loss models) under "
        "normal conditions, making statistical deviation detectable via Z-score analysis.",
        "Explainable AI (XAI) for Network Security: The need for interpretable ML outputs in "
        "critical infrastructure is well-established. Feature contribution analysis and risk "
        "decomposition allow network operators to understand and trust automated detection decisions, "
        "bridging the gap between raw algorithmic output and actionable security intelligence.",
    ]
    for p in pillars:
        add_bullet(doc, p)

    add_heading_styled(doc, "3.3 Research Gap Justification", level=2)
    add_paragraph_styled(doc,
        "The literature confirms that UE-side link routing provides effective active defense and "
        "network-side ML offers scalable detection. However, existing studies focus predominantly on "
        "raw algorithmic accuracy while neglecting the critical dimension of operational explainability. "
        "Pure ML outputs function as 'black boxes' where network engineers lack the contextual "
        "evidence to confidently execute mitigation actions (e.g., blocking a suspicious node). "
        "This project directly addresses this gap by combining a robust ML anomaly detection engine "
        "with an explainable Django web interface and deep-dive PowerBI visual analytics, ensuring "
        "that high-accuracy ML detections are transformed into transparent, actionable security "
        "intelligence for telecommunications operators."
    )

    doc.add_page_break()

    # ====================================================================
    # 5. METHODOLOGY / SOLUTION APPROACH
    # ====================================================================
    add_heading_styled(doc, "4. Methodology / Solution Approach", level=1)

    add_heading_styled(doc, "4.1 System Development Methodology", level=2)
    add_paragraph_styled(doc,
        "This project follows an Agile-inspired iterative development methodology, structured around "
        "the specific requirements of a research-oriented system development project. The development "
        "proceeds through four interconnected stages:"
    )
    stages = [
        "Stage 1 – Data Ingestion and Feature Engineering: Offline ingestion of standard LTE/5G "
        "Measurement Report (MR) data exported as CSV files from Dialog Axiata PLC's network. The "
        "CSV dataset is loaded in batch for model training and anomaly detection. Raw metrics "
        "(RSRP, RSRQ, Neighbor Cell IDs) are extracted and transformed into a 3×K feature vector "
        "per cell (Presence + RSRP + RSRQ for K unique neighbours), engineered to detect artificial "
        "signal spikes, missing neighbour cells, and unusual handover patterns. Future work will "
        "implement an MR file push mechanism to the server and a companion mobile application for "
        "live MR submission.",
        "Stage 2 – Machine Learning Anomaly Detection: The MLBridge service, integrated directly "
        "within the Django backend, implements a two-layer detection pipeline using OR-logic: "
        "Layer 1 (RRCF CoDisp) detects unusual neighbour combinations by comparing scores against "
        "trained CellModel baselines, while Layer 2 (Z-Score) detects abnormal signal values by "
        "computing per-neighbour RSRP/RSRQ deviations from baseline statistics. A temporal "
        "aggregation filter suppresses transient false positives by requiring sustained anomaly "
        "events within a detection window.",
        "Stage 3 – Explainable Alert Management (Django): A dedicated Django web application serves "
        "as the operational dashboard with three levels of explainability: per-anomaly RRCF score "
        "breakdown, per-cell baseline profiling, and per-neighbour cross-run risk assessment.",
        "Stage 4 – Forensic Visual Analytics (PowerBI): Microsoft PowerBI connects to the Django "
        "REST API to produce interactive, large-scale visualizations including geographic FBS "
        "vulnerability heatmaps, historical threat trend analysis, and localized cell risk scoring.",
    ]
    for s in stages:
        add_bullet(doc, s)

    add_heading_styled(doc, "4.2 Data Collection and Processing Approach", level=2)
    add_paragraph_styled(doc,
        "The project utilizes a real-world LTE/5G Measurement Report dataset obtained from Dialog "
        "Axiata PLC, Sri Lanka's leading telecommunications provider, provided as CSV files. This "
        "dataset comprises approximately 46 million rows of network telemetry, providing an extremely "
        "precise baseline of normal radio traffic. The CSV files are loaded in batch for offline "
        "model training and detection, rather than through a live streaming interface. This approach "
        "enables repeatable experimentation and rigorous evaluation against labelled test data."
    )
    add_paragraph_styled(doc,
        "Since legal and ethical constraints prohibit the deployment of actual Fake Base Station "
        "hardware in live networks, the evaluation methodology employs synthetic anomaly injection. "
        "Three types of FBS attack scenarios are simulated:"
    )
    attacks = [
        "IMSI Catcher Attack: Unknown cell IDs with abnormally strong signals (RSRP: -52 to -44 dBm) "
        "injected into the neighbor list, simulating a rogue device broadcasting at high power.",
        "Downgrade Attack: Known legitimate neighbors with severely degraded signal quality "
        "(RSRP: -120 to -110 dBm, RSRQ: -18 to -15 dB), simulating protocol downgrade attempts.",
        "Neighbor Spoofing Attack: FBS devices masquerading with unexpected signal characteristics "
        "(RSRP: -60 to -50 dBm), simulating adversaries that replicate legitimate cell IDs with "
        "anomalous signal strengths.",
    ]
    for a in attacks:
        add_bullet(doc, a)

    add_heading_styled(doc, "4.3 Tools, Technologies, and Justification", level=2)

    add_table(doc,
        ["Category", "Technology", "Justification"],
        [
            ["ML & Data Processing",
             "Python 3.10+, Pandas, NumPy, Joblib",
             "Python ecosystem provides mature, well-documented libraries for data manipulation. Z-score anomaly detection and RRCF CoDisp scoring are implemented directly within the Django MLBridge service."],
            ["Web Framework + ML Engine",
             "Django 5 + Django REST Framework",
             "Django's 'batteries-included' approach provides ORM, admin interface, authentication, and middleware. The MLBridge service (1,011 lines) integrates ML training and detection directly within the Django process, eliminating external dependencies."],
            ["Frontend",
             "React 19, Vite 8, Tailwind CSS v4, Recharts, Leaflet",
             "React's component model suits the multi-page dashboard. Recharts provides statistical charts; Leaflet enables geographic map visualization."],
            ["Database",
             "SQLite (dev), PostgreSQL (prod-ready)",
             "SQLite provides zero-configuration development. CellModel baselines and neighbour statistics are stored as JSONField for efficient retrieval during detection."],
            ["Visual Analytics",
             "Microsoft PowerBI Desktop",
             "Industry-standard business intelligence tool enabling interactive dashboards with geographic mapping, drill-through, and cross-filtering."],
            ["Version Control",
             "Git / GitHub",
             "Full version history, branch management, and collaboration capabilities."],
            ["IDE & Development",
             "VS Code, PyCharm, Jupyter Notebooks",
             "Multi-environment development for prototyping (Jupyter), ML development (PyCharm), and frontend/backend (VS Code)."],
        ],
        col_widths=[1.3, 2.0, 3.2]
    )

    doc.add_page_break()

    # ====================================================================
    # 6. DESIGN AND IMPLEMENTATION PROGRESS
    # ====================================================================
    add_heading_styled(doc, "5. Design and Implementation Progress", level=1)

    add_heading_styled(doc, "5.1 System Architecture", level=2)
    add_paragraph_styled(doc,
        "The system follows a two-tier architecture consisting of a React SPA frontend and a Django "
        "REST API backend with integrated ML capabilities. The ML training and detection logic is "
        "embedded directly within the Django backend via the MLBridge service, eliminating the need "
        "for a separate ML processing tier. The following diagram illustrates the high-level architecture:"
    )

    # Architecture diagram as a text block
    p = doc.add_paragraph()
    run = p.add_run(
        "┌─────────────────────┐     ┌────────────────────────────────────────────────┐\n"
        "│   React Frontend    │     │         Django REST API Backend                │\n"
        "│   (Vite + Tailwind) │◄───►│   DRF + MLBridge + XAI + Alert Engine         │\n"
        "│   Port 5173         │HTTP │   Port 8000                                    │\n"
        "└─────────────────────┘     └────────────────────────────────────────────────┘\n"
        "        │                              │                                      \n"
        "        ▼                              ▼                                      \n"
        "┌─────────────────────┐     ┌────────────────────────────────────────────────┐\n"
        "│   PowerBI Desktop   │     │   SQLite Database (db.sqlite3 — 22.7 MB)      │\n"
        "│   (External)        │◄────│   CellModel baselines, Anomalies, Alerts,     │\n"
        "│   4 Dashboard Pages │ CSV │   DetectionRuns, NeighborStats (JSONField)     │\n"
        "└─────────────────────┘     └────────────────────────────────────────────────┘"
    )
    run.font.name = "Courier New"
    run.font.size = Pt(8)

    add_paragraph_styled(doc,
        "Figure 1: High-level system architecture showing the two-tier design with integrated ML and PowerBI external integration.",
        italic=True, font_size=10, alignment=WD_ALIGN_PARAGRAPH.CENTER
    )

    add_heading_styled(doc, "5.2 ML Pipeline Implementation", level=2)
    add_paragraph_styled(doc,
        "The ML training and detection logic is implemented directly within the Django backend "
        "via the MLBridge service (backend/detection/services/ml_bridge.py — 1,011 lines). This "
        "integrated approach eliminates external subprocess dependencies and enables the ML pipeline "
        "to operate within the Django request-response cycle, with direct access to the ORM for "
        "model storage and anomaly persistence."
    )

    add_paragraph_styled(doc, "Training Pipeline (_parse_csv_and_build_models):", bold=True)
    add_paragraph_styled(doc,
        "The training pipeline reads an uploaded MR CSV file and constructs per-cell CellModel records "
        "in the Django database. For each serving cell, the pipeline: (1) extracts all unique neighbour "
        "cell IDs from the CSV to determine K, (2) computes per-neighbour RSRP and RSRQ baseline "
        "statistics (mean and standard deviation) for Z-score reference, (3) establishes CoDisp baseline "
        "parameters (mean_codisp and std_codisp) for threshold calibration, and (4) stores the complete "
        "CellModel including neighbour_order, neighbour_stats (as JSONField), and training parameters "
        "directly in the Django ORM via update_or_create."
    )

    add_paragraph_styled(doc, "Detection Pipeline (_detect_from_csv):", bold=True)
    add_paragraph_styled(doc,
        "The detection pipeline implements a two-layer OR-logic detection strategy:"
    )
    layers = [
        "Layer 1 — RRCF CoDisp: Each incoming MR row is scored against the cell's trained CoDisp "
        "baseline. The average CoDisp score is compared to the threshold (mean_codisp + threshold_mult "
        "× std_codisp). A score exceeding the threshold indicates an unusual combination of neighbour "
        "cells — likely an unknown or rogue cell ID in the neighbour list.",
        "Layer 2 — Z-Score: For each present neighbour in the MR row, the observed RSRP and RSRQ "
        "values are compared to the trained CellModel baseline statistics. The combined Z-score "
        "(√(rsrp_z² + rsrq_z²)) is computed, and neighbours exceeding the min_anomaly_score threshold "
        "are flagged. Unknown neighbours not present in the trained baseline are automatically flagged "
        "with elevated scores. This layer catches FBS attacks where signal characteristics deviate "
        "significantly from the learned baseline.",
        "Post-Processing — Suspicious Neighbour Aggregation: Anomaly details are aggregated into "
        "SuspiciousNeighbor rankings by cumulative score and occurrence count. Temporal clustering "
        "builds DetectedWindow records identifying sustained anomaly activity. Security alerts are "
        "auto-generated with severity classification (critical/high/medium/low) based on cumulative "
        "scores and affected cell counts.",
    ]
    for l in layers:
        add_bullet(doc, l)

    add_paragraph_styled(doc,
        "All detection outputs — Anomaly records, NeighborAnomalyDetail records, SuspiciousNeighbor "
        "rankings, DetectedWindow clusters, and AbnormalNeighbor summaries — are persisted directly "
        "into the Django database via bulk_create for performance, enabling immediate visualization "
        "through the React dashboard and PowerBI connectors."
    )

    add_heading_styled(doc, "5.3 Django Backend Implementation", level=2)
    add_paragraph_styled(doc,
        "The Django backend consists of four application modules with a total of 11 database models "
        "and a comprehensive REST API:"
    )

    add_table(doc,
        ["Django App", "Models", "Key Functionality"],
        [
            ["detection", "DetectionRun, TrainingRun, CellModel, Anomaly, NeighborAnomalyDetail, SuspiciousNeighbor, DetectedWindow, AbnormalNeighbor, CellLocation (9 models)",
             "Full detection and training pipeline management; CSV upload with header validation; per-cell model metadata storage"],
            ["alerts", "Alert, AlertHistory (2 models)",
             "Security alert lifecycle (New → Acknowledged → Investigating → Resolved/False Positive) with full audit trail"],
            ["analytics", "No models (uses detection + alerts)",
             "Dashboard statistics, anomaly trends, cell risk ranking, detection method breakdown, geographic heatmap, 4 PowerBI export endpoints"],
            ["accounts", "UserProfile (1 model)",
             "Token-based authentication, role-based access (admin/analyst/viewer), user registration and profile management"],
        ],
        col_widths=[1.0, 2.5, 3.0]
    )

    add_paragraph_styled(doc, "Key Backend Services:", bold=True)
    services = [
        "MLBridge (1,011 lines): Integrated ML engine that directly performs CSV-based training "
        "and two-layer anomaly detection within the Django process. Reads uploaded CSV files, builds "
        "CellModel baselines, scores rows against trained models using Z-score analysis, and generates "
        "alerts with severity classification — all without external subprocess dependencies.",
        "ReportParser (297 lines): Robust CSV parser that reads detection output files and populates "
        "Django models using bulk_create for performance.",
        "ExplainabilityService (230 lines): Three-level XAI engine providing per-anomaly explanations "
        "(RRCF score breakdown + neighbour Z-scores), per-cell baseline profiles, and per-neighbour "
        "cross-run risk assessments with risk level classification.",
    ]
    for s in services:
        add_bullet(doc, s)

    add_heading_styled(doc, "5.4 React Frontend Implementation", level=2)
    add_paragraph_styled(doc,
        "The React SPA provides a comprehensive operational dashboard with 13 interactive pages "
        "and 8 reusable components. Built using React 19, Vite 8, and Tailwind CSS v4, the "
        "frontend communicates with the Django backend exclusively through REST API calls."
    )

    add_table(doc,
        ["Page", "Route", "Key Features"],
        [
            ["Dashboard", "/", "Overview statistics, anomaly trends (area chart), detection method breakdown (pie chart), recent activity feed, live geographic map preview, model health status"],
            ["Detection Runs", "/detection", "List all detection runs, trigger new runs via CSV upload, view run status and parameters"],
            ["Run Detail", "/detection/:id", "Per-run summary statistics, anomaly list with filtering, suspicious neighbours, time windows"],
            ["Alerts", "/alerts", "Alert management with status/severity filters, acknowledge/resolve/false-positive actions with audit comments"],
            ["Anomalies", "/anomalies", "Paginated anomaly browser with cell ID and detection method filters"],
            ["Anomaly XAI", "/anomalies/:id", "Full explainability view: RRCF score explanation, neighbour-by-neighbour Z-score breakdown, risk assessment"],
            ["Neighbor Detail", "/neighbors/:id", "Deep-dive neighbour investigation: affected cells, signal summary, MR records table, risk profile"],
            ["Cell Models", "/cells", "Browse all 798 trained cell models with search, view K-value and training row count"],
            ["Cell Detail", "/cells/:cellId", "Radar chart of neighbour statistics, baseline CoDisp thresholds, anomaly history for the cell"],
            ["Geographic Map", "/map", "Full-page Leaflet map with risk-coloured markers, cell popups, technology/band labels"],
            ["Analytics", "/analytics", "Charts: anomaly trends, top-N cell risk ranking, detection method breakdown"],
            ["Training", "/training", "Training run management, trigger new training, view model generation progress"],
            ["Login", "/login", "Token-based authentication with protected route enforcement"],
        ],
        col_widths=[1.0, 1.3, 4.2]
    )

    add_heading_styled(doc, "5.5 PowerBI Integration", level=2)
    add_paragraph_styled(doc,
        "Four dedicated PowerBI export endpoints have been developed in the analytics module, each "
        "supporting both JSON (for PowerBI Web connector) and CSV (for direct file import) formats:"
    )

    add_table(doc,
        ["Endpoint", "PowerBI Table", "Description"],
        [
            ["/api/analytics/powerbi/anomalies/", "Anomalies", "Denormalized anomaly data with per-neighbour signal details"],
            ["/api/analytics/powerbi/alerts/", "Alerts", "Alert lifecycle with resolution timeline and response metrics"],
            ["/api/analytics/powerbi/cell-risk/", "CellRisk", "Cross-run neighbour risk aggregation with severity classification"],
            ["/api/analytics/powerbi/geographic/", "Geographic", "Cell tower locations with anomaly counts and risk levels for map visuals"],
        ],
        col_widths=[2.5, 1.2, 2.8]
    )
    add_paragraph_styled(doc,
        "Additionally, four PowerBI M query (.pq) files have been prepared to enable one-click data "
        "import into PowerBI Desktop, with configurable BaseUrl parameters for deployment flexibility."
    )

    doc.add_page_break()

    # ====================================================================
    # 7. TESTING / EVALUATION PLAN (DRAFT)
    # ====================================================================
    add_heading_styled(doc, "6. Testing / Evaluation Plan (Draft)", level=1)

    add_heading_styled(doc, "6.1 Proposed Testing Strategy", level=2)
    add_paragraph_styled(doc, "The testing strategy is organized into three tiers:")
    tiers = [
        "Unit Testing: 53 automated Django tests covering model creation, API endpoint responses, "
        "authentication flows, alert lifecycle transitions, CSV upload validation, and analytics "
        "aggregation correctness. Tests are executed using python manage.py test --verbosity=2.",
        "Integration Testing: End-to-end pipeline testing from CSV upload through ML detection to "
        "alert generation and XAI explanation rendering. Verifies that all system components work "
        "together correctly via the REST API.",
        "ML Model Evaluation: Dedicated evaluation framework (evaluate_model.py) for measuring "
        "detection accuracy against labelled test data with ground-truth FBS attack annotations.",
    ]
    for t in tiers:
        add_bullet(doc, t)

    add_heading_styled(doc, "6.2 Evaluation Metrics", level=2)
    add_paragraph_styled(doc, "The ML model evaluation uses the following standard classification metrics:")

    add_table(doc,
        ["Metric", "Formula", "Significance for FBS Detection"],
        [
            ["Precision", "TP / (TP + FP)", "Minimizes false alarms that waste operator time"],
            ["Recall", "TP / (TP + FN)", "Ensures genuine FBS attacks are not missed"],
            ["F1-Score", "2 × P × R / (P + R)", "Harmonic mean balancing precision and recall"],
            ["Accuracy", "(TP + TN) / Total", "Overall classification correctness"],
            ["False Positive Rate", "FP / (FP + TN)", "Critical metric for operational viability"],
        ],
        col_widths=[1.3, 1.5, 3.7]
    )

    add_paragraph_styled(doc, "Preliminary Evaluation Results (Demo Mode):", bold=True)
    add_table(doc,
        ["Metric", "Value"],
        [
            ["Precision", "0.756"],
            ["Recall", "0.868"],
            ["F1-Score", "0.808"],
            ["Accuracy", "93.8%"],
        ],
        col_widths=[2.0, 2.0]
    )

    add_heading_styled(doc, "6.3 Planned Experiments", level=2)
    experiments = [
        "Per-Attack-Type Recall Analysis: Evaluate detection recall separately for each FBS attack type "
        "(IMSI catcher, downgrade, neighbour spoofing) to identify model strengths and weaknesses.",
        "Threshold Sensitivity Analysis: Systematically vary threshold_mult (0.5–2.0), z_threshold "
        "(1.5–3.0), and min_anomaly_score (2.0–6.0) to characterize the precision-recall trade-off.",
        "Scalability Testing: Measure detection latency across varying dataset sizes (1K, 10K, 100K, "
        "1M rows) to validate operational viability for real-time deployment.",
        "Window Filter Impact: Compare detection results with and without the 30-minute sliding window "
        "filter to quantify false-positive reduction effectiveness.",
        "C++ vs Python Backend Comparison: Benchmark RRCF forest building and scoring time for the "
        "C++ backend versus pure Python to validate the 25× speedup claim.",
    ]
    for e in experiments:
        add_bullet(doc, e)

    doc.add_page_break()

    # ====================================================================
    # 8. CHALLENGES AND RISK MANAGEMENT
    # ====================================================================
    add_heading_styled(doc, "7. Challenges and Risk Management", level=1)

    add_heading_styled(doc, "7.1 Issues Faced", level=2)

    add_table(doc,
        ["Challenge", "Category", "Resolution"],
        [
            ["Processing 46M rows of MR data caused memory overflow on 16GB RAM",
             "Technical",
             "Implemented chunked CSV processing with per-cell model persistence via Django ORM (CellModel with JSONField for neighbour statistics), eliminating in-memory dataset requirements."],
            ["Legal prohibition on deploying real FBS hardware in live networks",
             "Ethical/Legal",
             "Developed synthetic anomaly injection framework (generate_fbs_attack_data.py) with three realistic attack scenarios to simulate FBS behaviour."],
            ["High false-positive rates with single-layer detection",
             "Technical",
             "Implemented two-layer OR-logic detection (RRCF CoDisp + Z-Score) with temporal aggregation filter and suspicious neighbour ranking to suppress transient false positives."],
            ["ML model outputs are opaque to network operators",
             "Operational",
             "Built three-level ExplainabilityService providing per-anomaly RRCF breakdown, per-cell baseline profiling, and per-neighbour risk assessment."],
            ["Integrating ML logic into the web application",
             "Architectural",
             "Embedded the complete ML training and detection pipeline directly within the Django MLBridge service (1,011 lines), enabling single-process deployment without external subprocess dependencies."],
        ],
        col_widths=[2.5, 1.0, 3.0]
    )

    add_heading_styled(doc, "7.2 Risk Mitigation Plan", level=2)

    add_table(doc,
        ["Risk", "Likelihood", "Impact", "Mitigation Strategy"],
        [
            ["Model overfitting to Dialog Axiata data", "Medium", "High",
             "Evaluate on synthetic attack data with diverse scenarios; plan cross-network validation if additional data becomes available."],
            ["SQLite performance bottleneck with large datasets", "Low", "Medium",
             "Schema designed for PostgreSQL migration; indexing on serving_cell_id and neighbor_id fields."],
            ["Dependency on PowerBI Desktop availability", "Low", "Low",
             "All export endpoints support CSV fallback; React dashboard provides independent visualization capability."],
            ["Timeline delays in final evaluation phase", "Medium", "Medium",
             "Evaluation framework already built; only requires running experiments and documenting results."],
        ],
        col_widths=[2.0, 0.8, 0.7, 3.0]
    )

    doc.add_page_break()

    # ====================================================================
    # 9. REVISED WORK PLAN
    # ====================================================================
    add_heading_styled(doc, "8. Revised Work Plan", level=1)

    add_paragraph_styled(doc,
        "The following updated Gantt chart reflects the revised timeline as of the interim submission. "
        "Phases 1–3 (highlighted) have been completed; Phases 4–5 detail the remaining work."
    )

    add_table(doc,
        ["ID", "Task", "Start", "Due", "Status"],
        [
            ["1.0", "Phase 1: Proposal Development and Submission", "15-Feb", "9-Mar", "✅ Completed"],
            ["1.1", "   Research problem refinement and supervisor meetings", "15-Feb", "21-Feb", "✅ Completed"],
            ["1.2", "   Literature review (FBS detection, ML, PowerBI)", "22-Feb", "5-Mar", "✅ Completed"],
            ["1.3", "   Finalize proposal document and methodology", "5-Mar", "9-Mar", "✅ Completed"],
            ["1.4", "   Milestone: Proposal Document Submission", "10-Mar", "10-Mar", "✅ Completed"],
            ["2.0", "Phase 2: Proposal Presentation", "10-Mar", "16-Mar", "✅ Completed"],
            ["2.1", "   Preparation of slides and defense prep", "10-Mar", "15-Mar", "✅ Completed"],
            ["2.2", "   Milestone: Formal Proposal Presentation", "16-Mar", "16-Mar", "✅ Completed"],
            ["3.0", "Phase 3: Research Implementation & Interim", "17-Mar", "28-Jun", "✅ Completed"],
            ["3.1", "   Ingest and preprocess 46M rows of Dialog Axiata MR data", "17-Mar", "31-Mar", "✅ Completed"],
            ["3.2", "   Feature engineering & synthetic anomaly injection", "1-Apr", "20-Apr", "✅ Completed"],
            ["3.3", "   Train and tune RRCF anomaly detection model", "21-Apr", "20-May", "✅ Completed"],
            ["3.4", "   Develop Django + React web application", "21-May", "10-Jun", "✅ Completed"],
            ["3.5", "   Compile preliminary results and draft interim report", "11-Jun", "28-Jun", "✅ Completed"],
            ["3.6", "   Milestone: Interim Report Submission", "29-Jun", "29-Jun", "✅ Today"],
            ["4.0", "Phase 4: Final Development & Report Submission", "30-Jun", "30-Aug", "🔄 Upcoming"],
            ["4.1", "   Integrate ML model with Django for batch detection alerts", "30-Jun", "15-Jul", "📋 Planned"],
            ["4.2", "   Connect database to PowerBI & build geographic heatmaps", "16-Jul", "5-Aug", "📋 Planned"],
            ["4.3", "   System optimization and false-positive reduction testing", "6-Aug", "15-Aug", "📋 Planned"],
            ["4.4", "   Final results analysis and documentation formatting", "16-Aug", "30-Aug", "📋 Planned"],
            ["4.5", "   Milestone: Final Report Submission", "31-Aug", "31-Aug", "📋 Planned"],
            ["5.0", "Phase 5: Final Presentation & Demonstration", "1-Sep", "9-Sep", "📋 Planned"],
            ["5.1", "   Prepare final slides and polish live system demo", "1-Sep", "8-Sep", "📋 Planned"],
            ["5.2", "   Milestone: Final Project Demonstration & Defense", "9-Sep", "9-Sep", "📋 Planned"],
        ],
        col_widths=[0.4, 3.0, 0.7, 0.7, 0.9]
    )

    add_heading_styled(doc, "8.1 Remaining Tasks", level=2)
    remaining = [
        "Complete production-mode ML-Django integration for batch CSV detection (currently in demo mode).",
        "Finalize PowerBI dashboard pages with geographic heatmaps and drill-through analysis.",
        "Execute comprehensive model evaluation with per-attack-type recall and threshold sensitivity analysis.",
        "Perform system optimization: false-positive tuning, latency profiling, and stress testing.",
        "Complete final academic documentation (results analysis, conclusions, and recommendations).",
        "Prepare final presentation slides and live system demonstration.",
    ]
    for r in remaining:
        add_bullet(doc, r)

    doc.add_page_break()

    # ====================================================================
    # 10. CONCLUSION
    # ====================================================================
    add_heading_styled(doc, "9. Conclusion", level=1)

    add_heading_styled(doc, "9.1 Summary of Progress", level=2)
    add_paragraph_styled(doc,
        "This interim report demonstrates that the project 'Detection of Fake Base Stations Using "
        "Machine Learning on LTE/5G Measurement Reports with an Explainable Web-Based System' has "
        "achieved approximately 80% completion against its stated objectives. All five research "
        "objectives have been addressed with concrete, functional artefacts:"
    )
    summary_items = [
        "Objective 1 (Data Engineering): Complete — 46M rows of Dialog Axiata MR CSV data have been "
        "ingested, preprocessed, and transformed into per-cell CellModel baselines with neighbour "
        "statistics stored in Django ORM.",
        "Objective 2 (Anomaly Detection Model): Complete — MLBridge service (1,011 lines) with "
        "integrated two-layer detection (CoDisp + Z-Score), per-cell CellModel baseline storage, "
        "and temporal anomaly aggregation — all embedded within the Django web application.",
        "Objective 3 (Explainable Alert System): Complete — Django REST API with 11 models, "
        "3-level XAI service, alert lifecycle management with full audit trail, and 53 automated tests.",
        "Objective 4 (Visual Analytics): Substantially complete — React SPA with 13 pages, Leaflet "
        "geographic map, Recharts analytics, and 4 PowerBI export endpoints with M query templates.",
        "Objective 5 (Evaluation): In progress — Evaluation framework built (generate_fbs_attack_data.py "
        "+ evaluate_model.py) with preliminary results (Precision 0.756, Recall 0.868, F1 0.808). "
        "Comprehensive evaluation experiments planned for Phase 4.",
    ]
    for s in summary_items:
        add_bullet(doc, s)

    add_heading_styled(doc, "9.2 Confirmation of Feasibility and Completion Plan", level=2)
    add_paragraph_styled(doc,
        "Based on the significant progress achieved to date, the project is confirmed to be fully "
        "feasible for completion within the remaining timeline. The core system architecture has been "
        "validated through a working end-to-end prototype, and all major technical risks have been "
        "mitigated. The remaining tasks—principally production ML integration, PowerBI dashboard "
        "finalization, comprehensive evaluation, and academic documentation—are well-defined and "
        "achievable within the Phase 4 timeline (30 June – 30 August 2026). The project is on track "
        "for successful final submission on 31 August 2026 and final demonstration on 9 September 2026."
    )

    add_heading_styled(doc, "9.3 Future Work", level=2)
    add_paragraph_styled(doc,
        "Beyond the current scope, the following enhancements are planned for future development:"
    )
    future_items = [
        "MR File Push to Server: Implement an automated mechanism to push Measurement Report files "
        "from Dialog Axiata’s network infrastructure directly to the detection server, enabling "
        "scheduled batch processing without manual CSV uploads.",
        "Companion Mobile Application: Develop a mobile application capable of capturing and "
        "submitting MR data from User Equipment (UE) directly to the detection system, enabling "
        "crowd-sourced FBS detection coverage and field-level verification of suspicious cells.",
        "Real-Time Streaming Pipeline: Evolve the current batch CSV pipeline into a streaming "
        "architecture for continuous, near-real-time FBS detection as MR data arrives.",
    ]
    for f in future_items:
        add_bullet(doc, f)

    doc.add_page_break()

    # ====================================================================
    # 11. REFERENCES (IEEE Format)
    # ====================================================================
    add_heading_styled(doc, "10. References", level=1)

    references = [
        '[1] Q. Miao, Y. Yan and Z. Wang, "Fake Base Station Detection". United States Patent US 11503472B2, 15 Nov 2022.',
        '[2] J. Shin, Y. Shin and J.-G. Park, "Network Detection of Fake Base Station using Automatic Neighbour Relation in Self-Organizing Networks," in 13th International Conference on Information and Communication Technology Convergence (ICTC), 2022.',
        '[3] S. Purification, J. Kim, J. Kim and S.-Y. Chang, "Fake Base Station Detection and Link Routing Defense," vol. 13, Electronics, p. 3474, Sep 2024.',
        '[4] S. Sun, I. Abualhaol, G. Poitau, A. Esswie and M. Repeta, "An Ensemble Approach for Fake Base Station Detection using Temporal Graph Analysis and Anomaly Detection," Wireless Telecommunications Symposium (WTS), 2024.',
        '[5] L. Karaçay, Z. Bilgin, A. B. Gündüz, P. Çomak, E. Tomur, E. U. Soykan, U. Gülen and F. Karakoç, "A Network-Based Positioning Method to Locate False Base Stations," vol. 9, IEEE Access, pp. 111368–111382, 09 August 2021.',
        '[6] S. Guha, N. Mishra, G. Roy and O. Schrijvers, "Robust Random Cut Forest Based Anomaly Detection on Streams," in Proceedings of the 33rd International Conference on Machine Learning (ICML), 2016.',
        '[7] 3GPP, "TS 36.331: Evolved Universal Terrestrial Radio Access (E-UTRA); Radio Resource Control (RRC); Protocol Specification," v17.4.0, Mar 2023.',
        '[8] 3GPP, "TS 38.331: NR; Radio Resource Control (RRC); Protocol Specification," v17.4.0, Mar 2023.',
        '[9] Django Software Foundation, "Django 5.0 Documentation," 2024. [Online]. Available: https://docs.djangoproject.com/en/5.0/.',
        '[10] Meta Platforms, Inc., "React 19 Documentation," 2025. [Online]. Available: https://react.dev/.',
    ]
    for ref in references:
        p = doc.add_paragraph()
        run = p.add_run(ref)
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        set_paragraph_spacing(p, before=0, after=4, line_spacing=1.5)

    doc.add_page_break()

    # ====================================================================
    # 12. APPENDICES
    # ====================================================================
    add_heading_styled(doc, "11. Appendices", level=1)

    add_heading_styled(doc, "Appendix A: Project Repository Structure", level=2)
    p = doc.add_paragraph()
    run = p.add_run(
        "Fake_Base_Station_Detection_System/\n"
        "├── backend/                        # Django REST API + Integrated ML Engine\n"
        "│   ├── detection/                  # Detection models, views, services (9 models)\n"
        "│   │   ├── models.py               # DetectionRun, CellModel, Anomaly, etc. (308 lines)\n"
        "│   │   ├── views.py                # ViewSets + CSV upload (601 lines)\n"
        "│   │   └── services/\n"
        "│   │       ├── ml_bridge.py         # ML training + detection engine (1,011 lines)\n"
        "│   │       ├── report_parser.py     # CSV output parser (297 lines)\n"
        "│   │       └── explainability.py    # 3-level XAI engine (230 lines)\n"
        "│   ├── alerts/                     # Alert CRUD + audit trail (2 models)\n"
        "│   ├── analytics/                  # Dashboard stats, trends, PowerBI export (401 lines)\n"
        "│   ├── accounts/                   # Auth (register, login, profiles)\n"
        "│   └── fbs_project/               # Django settings + URL config\n"
        "├── frontend/                       # React SPA\n"
        "│   └── src/\n"
        "│       ├── pages/                  # 13 pages\n"
        "│       ├── components/             # 8 reusable components\n"
        "│       ├── contexts/               # AuthContext\n"
        "│       └── services/               # API layer (axios)\n"
        "├── ml_service/                     # Initial prototyping (concept validation)\n"
        "│   └── scripts/                    # Standalone scripts used during R&D phase\n"
        "├── powerbi/                        # PowerBI M queries (4 .pq files)\n"
        "├── docs/                           # 5 documentation files\n"
        "└── README.md                       # Project overview\n"
    )
    run.font.name = "Courier New"
    run.font.size = Pt(9)

    add_heading_styled(doc, "Appendix B: Database Schema Summary", level=2)
    add_table(doc,
        ["Model", "App", "Key Fields", "Purpose"],
        [
            ["DetectionRun", "detection", "run_id, status, total_anomalies, threshold_mult, z_threshold", "Pipeline execution records"],
            ["TrainingRun", "detection", "run_id, status, num_trees, tree_size, total_cells_trained", "Training pipeline records"],
            ["CellModel", "detection", "serving_cell_id, K, mean_codisp, std_codisp, neighbor_order", "Per-cell RRCF model metadata"],
            ["Anomaly", "detection", "serving_cell_id, avg_codisp, threshold, rrcf_flagged, zscore_flagged", "Individual anomalous MR records"],
            ["NeighborAnomalyDetail", "detection", "neighbor_id, anomaly_score, rsrp, rsrq, rsrp_z, rsrq_z", "Per-neighbour signal details"],
            ["SuspiciousNeighbor", "detection", "neighbor_id, sum_score, occurrence_count, affected_serving_cells", "Aggregated suspicion rankings"],
            ["DetectedWindow", "detection", "serving_cell_id, neighbor_id, window_start, window_end, event_count", "Time windows with anomaly clusters"],
            ["AbnormalNeighbor", "detection", "serving_cell_id, neighbor_id, event_count, window_count", "Window-filtered summary"],
            ["CellLocation", "detection", "global_cell_id, latitude, longitude, technology, band", "Geographic coordinates for map"],
            ["Alert", "alerts", "neighbor_id, severity, status, peak_anomaly_score", "Security alerts with lifecycle"],
            ["AlertHistory", "alerts", "old_status, new_status, changed_by, comment", "Audit trail for alert transitions"],
        ],
        col_widths=[1.3, 0.7, 2.5, 2.0]
    )

    add_heading_styled(doc, "Appendix C: Key ML Parameters", level=2)
    add_table(doc,
        ["Parameter", "Default", "Description"],
        [
            ["--num-trees", "150", "Number of RRCF trees per cell model"],
            ["--tree-size", "1024", "Maximum data points per tree"],
            ["--threshold-mult", "1.0", "RRCF threshold = mean + mult × std"],
            ["--z-threshold", "2.0", "Z-score threshold per metric"],
            ["--min-anomaly-score", "4.0", "Minimum combined Z-score to flag a neighbour"],
            ["--min-samples", "50", "Minimum MR rows required to train a cell model"],
        ],
        col_widths=[1.5, 1.0, 4.0]
    )

    add_heading_styled(doc, "Appendix D: API Endpoint Summary", level=2)
    add_table(doc,
        ["Method", "Endpoint", "Description"],
        [
            ["POST", "/api/detection/runs/trigger/", "Trigger detection pipeline"],
            ["GET", "/api/detection/runs/{id}/summary/", "Detection run summary"],
            ["GET", "/api/detection/anomalies/{id}/explain/", "XAI anomaly explanation"],
            ["GET", "/api/detection/cells/{id}/profile/", "Cell model XAI profile"],
            ["GET", "/api/detection/neighbors/{id}/risk-profile/", "Neighbour risk profile"],
            ["POST", "/api/detection/upload/", "CSV file upload with validation"],
            ["PATCH", "/api/alerts/{id}/", "Update alert status with audit trail"],
            ["POST", "/api/alerts/{id}/acknowledge/", "Acknowledge alert"],
            ["POST", "/api/alerts/{id}/resolve/", "Resolve alert"],
            ["GET", "/api/analytics/dashboard/", "Dashboard overview statistics"],
            ["GET", "/api/analytics/geographic/", "Geographic heatmap data"],
            ["GET", "/api/analytics/powerbi/anomalies/", "PowerBI anomaly export"],
            ["GET", "/api/analytics/powerbi/geographic/", "PowerBI geographic export"],
        ],
        col_widths=[0.7, 2.8, 3.0]
    )

    # ── Save ──
    doc.save(OUTPUT_PATH)
    print(f"\n[OK] Interim Report generated successfully: {OUTPUT_PATH}")
    print(f"     File size: {os.path.getsize(OUTPUT_PATH) / 1024:.1f} KB")


if __name__ == "__main__":
    build_report()
