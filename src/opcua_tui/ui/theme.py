from __future__ import annotations

from textual.theme import Theme


OPC_MODERN_THEME = Theme(
    name="opc-modern",
    primary="#4A6A7E",
    secondary="#58798A",
    accent="#B9884A",
    foreground="#E6ECF2",
    background="#0F1419",
    surface="#172028",
    panel="#1E2A34",
    success="#5F9474",
    warning="#C6A066",
    error="#B57272",
    dark=True,
    variables={
        "border": "#5D7382",
        "border-blurred": "#2F3C46",
        "footer-background": "#1E2A34",
        "footer-foreground": "#CFD9E3",
        "footer-key-foreground": "#D6AB73",
        "input-selection-background": "#58798A66",
        "block-cursor-text-style": "none",
    },
)
