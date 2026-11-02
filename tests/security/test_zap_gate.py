
import json
import sys
from pathlib import Path

report_path = Path("zap-reports/zap-report.json")

if not report_path.exists():
    print("ERROR: ZAP JSON report was not generated.")
    sys.exit(1)

with report_path.open(encoding="utf-8") as file:
    report = json.load(file)

if "site" not in report:
    print("ERROR: Unexpected ZAP report structure.")
    sys.exit(1)

high_findings = []

for site in report.get("site", []):
    for alert in site.get("alerts", []):
        if str(alert.get("riskcode", "")) == "3":
            high_findings.append({
                "name": alert.get("name", "Unknown"),
                "url": site.get("@name", "Unknown URL"),
                "risk": alert.get("riskdesc", "High")
            })

if high_findings:
    print("\nHIGH-RISK vulnerabilities detected:\n")

    for finding in high_findings:
        print(f"- {finding['name']}")
        print(f"  Risk: {finding['risk']}")
        print(f"  URL: {finding['url']}\n")

    print("Pipeline blocked due to high-risk findings.")
    sys.exit(1)

print("No high-risk ZAP findings detected.")
