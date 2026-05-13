app_name = "brain"
app_title = "brAIn"
app_publisher = "Styloworld"
app_description = "AI intelligence layer for Styloworld — operate the entire platform with natural language"
app_email = "hello@styloworld.io"
app_license = "mit"
app_logo_url = "/assets/brain/images/brain-logo.png"

# Inject brAIn UI into every Frappe desk page
app_include_js = ["/assets/brain/js/brain.js"]
app_include_css = ["/assets/brain/css/brain.css"]

# DocType classes
doctype_js = {}

# No before_request hooks — brAIn is purely additive
