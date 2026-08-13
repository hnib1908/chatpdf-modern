import streamlit as st

LIGHT = {
    "bg": "#FFFFFF",
    "bg_secondary": "#F7F7F8",
    "sidebar_bg": "#F9F9FA",
    "text": "#1E1E1E",
    "text_muted": "#6B7280",
    "border": "#E5E7EB",
    "accent": "#4F46E5",
    "accent_soft": "#EEF2FF",
    "user_bubble": "#4F46E5",
    "user_bubble_text": "#FFFFFF",
    "assistant_bubble": "#F3F4F6",
    "assistant_bubble_text": "#1E1E1E",
    "success": "#16A34A",
    "error": "#DC2626",
}

DARK = {
    "bg": "#0F1117",
    "bg_secondary": "#181B23",
    "sidebar_bg": "#14161D",
    "text": "#E5E7EB",
    "text_muted": "#9CA3AF",
    "border": "#2A2D37",
    "accent": "#818CF8",
    "accent_soft": "#1E2030",
    "user_bubble": "#4F46E5",
    "user_bubble_text": "#FFFFFF",
    "assistant_bubble": "#1E2029",
    "assistant_bubble_text": "#E5E7EB",
    "success": "#22C55E",
    "error": "#F87171",
}


def inject_theme_css(dark: bool):
    c = DARK if dark else LIGHT
    st.markdown(
        f"""
        <style>
        :root {{
            --bg: {c['bg']};
            --bg-secondary: {c['bg_secondary']};
            --sidebar-bg: {c['sidebar_bg']};
            --text: {c['text']};
            --text-muted: {c['text_muted']};
            --border: {c['border']};
            --accent: {c['accent']};
            --accent-soft: {c['accent_soft']};
            --user-bubble: {c['user_bubble']};
            --user-bubble-text: {c['user_bubble_text']};
            --assistant-bubble: {c['assistant_bubble']};
            --assistant-bubble-text: {c['assistant_bubble_text']};
            --success: {c['success']};
            --error: {c['error']};
        }}

        .stApp {{
            background-color: var(--bg);
            color: var(--text);
        }}

        section[data-testid="stSidebar"] {{
            background-color: var(--sidebar-bg);
            border-right: 1px solid var(--border);
        }}

        /* Chat bubbles */
        div[data-testid="stChatMessage"] {{
            background: transparent;
            padding: 4px 0;
        }}

        .status-pill {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
            padding: 4px 10px;
            border-radius: 999px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            color: var(--text-muted);
            margin-bottom: 10px;
        }}
        .status-dot {{
            width: 8px; height: 8px; border-radius: 50%;
        }}
        .status-dot.online {{ background: var(--success); }}
        .status-dot.offline {{ background: var(--error); }}

        .doc-chip {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 6px 10px;
            border-radius: 8px;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            font-size: 13px;
            margin-bottom: 6px;
        }}
        .doc-chip.active {{
            border-color: var(--accent);
            background: var(--accent-soft);
        }}

        .citation-block {{
            font-size: 13px;
            color: var(--text-muted);
            background: var(--bg-secondary);
            border-left: 3px solid var(--accent);
            padding: 8px 12px;
            border-radius: 6px;
            margin-top: 4px;
            white-space: pre-wrap;
        }}

        h3, .stSubheader {{
            font-weight: 600 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
