def apply_cleaning_issue(ambulance_doc):
	ambulance_doc.cleanliness_status = "Cleaning Required"


MECHANICAL_SEVERITY_TO_STATUS = {
	"Observation": "Observation",  # non-blocking per spec §6.2/§8.7 — visible as a warning only
	"Attention Required": "Maintenance Required",
	"Breakdown": "Breakdown",
}


def apply_mechanical_issue(ambulance_doc, severity):
	ambulance_doc.mechanical_status = MECHANICAL_SEVERITY_TO_STATUS.get(severity, "Maintenance Required")


def resolve_cleaning(ambulance_doc):
	ambulance_doc.cleanliness_status = "Clean"


def resolve_mechanical(ambulance_doc):
	ambulance_doc.mechanical_status = "Fit"
