"""Board registry; shared parsers retain board-specific segmentation rules."""

REGISTRY = {
    "Cebraspe": "cebraspe_fundatec",
    "Fundatec": "cebraspe_fundatec",
    "FCC": "fcc_esaf_vunesp",
    "ESAF": "fcc_esaf_vunesp",
    "Vunesp": "fcc_esaf_vunesp",
    "FGV": "fgv",
}
SYLLABUS = {
    "Cebraspe": "cebraspe_editais",
    "FCC": "fcc_vunesp_editais",
    "Vunesp": "fcc_vunesp_editais",
    "FGV": "fgv_editais",
}
