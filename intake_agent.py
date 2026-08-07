import ollama
import json
import os 
import re
from datetime import datetime

MODEL = "llama3.1:8b"
FORMS_FOLDER = "sample_forms"

EXTRACTION_PROMPT = """Extract the following fields from this lab sample submission form.
Return ONLY valid JSON, no other text, using this exact structure:

{{
  "sample_id": "...",
  "patient_id": "...",
  "collection_date": "...",
  "sample_type": "...",
  "storage_condition": "...",
  "priority": "...",
  "submitting_lab": "...",
  "ordering_physician": "...",
  "tests_requested": "..."
}}

If a field is missing or blank in the document, use an empty string "" for that field — do not invent a value.

Document:
{document_text}
"""

VALID_PRIORITIES = {"routine", "urgent", "stat"}
VALID_SAMPLE_TYPES = {
    "blood", "blood - serum", "blood - plasma", "urine", 
    "tissue biopsy", "swab", "saliva", "csf"
}
REQUIRED_FIELDS = [
    "sample_id", "patient_id", "collection_date", "sample_type",
    "storage_condition", "priority", "submitting_lab"
]

def extract_fields(document_text):
    prompt = EXTRACTION_PROMPT.format(document_text = document_text)
    response = ollama.chat(model = MODEL, messages = [{"role": "user", "content": prompt}])
    text = response["message"]["content"].strip().replace("'''json", "").replace("'''", "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError: 
        return None 

def is_valid_date(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False

def validate_record(fields):
    issues = []

    for field in REQUIRED_FIELDS:
        if not fields.get(field, "").strip():
            issues.append(f"Missing required field: {field}")

    if fields.get("collection_date") and not is_valid_date(fields["collection_date"]):
        issues.append(f"Invalid or incomplete collection_date: '{fields['collection_date']}' (expected YYYY-MM-DD)")

    priority = fields.get("priority", "").strip().lower()
    if priority and priority not in VALID_PRIORITIES:
        issues.append(f"Invalid priority value: '{fields['priority']}' (expected Routine/Urgent/STAT)")

    sample_type = fields.get("sample_type", "").strip().lower()
    if sample_type and sample_type not in VALID_SAMPLE_TYPES:
        issues.append(f"Unrecognized sample_type: '{fields['sample_type']}' — flagged for manual review")

    return issues

def process_form(filepath):
    with open(filepath) as f:
        document_text = f.read()

    fields = extract_fields(document_text)

    if fields is None:
        return {
            "filename": os.path.basename(filepath),
            "status": "EXTRACTION_FAILED",
            "record": None,
            "issues": ["LLM did not return valid JSON"]
        }

    issues = validate_record(fields)
    status = "CLEAN" if not issues else "NEEDS_REVIEW"

    return {
        "filename": os.path.basename(filepath),
        "status": status,
        "record": fields,
        "issues": issues
    }


if __name__ == "__main__":
    results = []
    for filename in sorted(os.listdir(FORMS_FOLDER)):
        filepath = os.path.join(FORMS_FOLDER, filename)
        print(f"Processing {filename}...")
        result = process_form(filepath)
        results.append(result)

        print(f"  Status: {result['status']}")
        if result["issues"]:
            for issue in result["issues"]:
                print(f"  - {issue}")
        print()

    with open("processed_records.json", "w") as f:
        json.dump(results, f, indent=2)

    clean_count = sum(1 for r in results if r["status"] == "CLEAN")
    print(f"Done. {clean_count}/{len(results)} forms clean, rest flagged for review.")
    print("Full results saved to processed_records.json")