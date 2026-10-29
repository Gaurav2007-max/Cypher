#!/usr/bin/env python3
"""Patch tourist/dashboard.html: add Crowd Forecast button to each destination card."""
import pathlib

root = pathlib.Path(r"c:\Users\Gaurav\Desktop\Cypher 2.0")
tmpl = root / "app" / "templates" / "tourist" / "dashboard.html"

content = tmpl.read_text(encoding="utf-8")

# Find the Navigate button block and insert the Crowd Forecast button after it
old_navigate = (
    '<button class="btn btn-sm btn-outline-primary rounded-pill px-3" '
    'onclick="window.travelMap.requestDirections({{ dest.latitude }}, '
    '{{ dest.longitude }}, \'{{ dest.name|replace("\'", "\\\\\'") }}\')">\\n'
    '                                <i class="bi bi-compass me-1"></i>Navigate\\n'
    '                            </button>'
)

new_navigate = (
    '<button class="btn btn-sm btn-outline-primary rounded-pill px-3" '
    'onclick="window.travelMap.requestDirections({{ dest.latitude }}, '
    '{{ dest.longitude }}, \'{{ dest.name|replace("\'", "\\\\\'") }}\')">\\n'
    '                                <i class="bi bi-compass me-1"></i>Navigate\\n'
    '                            </button>\\n'
    '                            <button class="btn btn-sm btn-outline-info rounded-pill px-3" '
    'onclick="openCrowdForecastModal({{ dest.id }}, \'{{ dest.name|replace("\'", "\\\\\'") }}\')">\\n'
    '                                <i class="bi bi-graph-up me-1"></i>Crowd Forecast\\n'
    '                            </button>'
)

if old_navigate in content:
    content = content.replace(old_navigate, new_navigate, 1)
    tmpl.write_text(content, encoding="utf-8")
    print("dashboard.html patched successfully - added Crowd Forecast button")
else:
    # Try to find a simpler pattern
    search = 'bi bi-compass me-1"></i>Navigate'
    idx = content.find(search)
    if idx < 0:
        print("ERROR: Could not find Navigate button - manual patch needed")
        exit(1)
    # Find the end of the button element
    btn_end = content.find('</button>', idx)
    if btn_end < 0:
        print("ERROR: Could not find button close tag")
        exit(1)
    btn_end += len('</button>')
    
    new_btn = (
        '\n                            '
        '<button class="btn btn-sm btn-outline-info rounded-pill px-3" '
        'onclick="openCrowdForecastModal({{ dest.id }}, \'{{ dest.name|replace("\'", "\\\\\'") }}\')"> '
        '<i class="bi bi-graph-up me-1"></i>Crowd Forecast'
        '</button>'
    )
    content = content[:btn_end] + new_btn + content[btn_end:]
    tmpl.write_text(content, encoding="utf-8")
    print("dashboard.html patched (fallback method) - Crowd Forecast button inserted")

