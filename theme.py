
import streamlit as st

def theme_button():
    ms = st.session_state

    # --- Inicializace témat ---
    if "themes" not in ms:
        ms.themes = {
            "current_theme": None,
            "refreshed": True,
            "light": {
                "theme.base": "light",
                "theme.primaryColor": "#F7931A",
                "button_face": "🌞",
            },
            "dark": {
                "theme.base": "dark",
                "theme.primaryColor": "#F7931A",
                "button_face": "🌜",
            },
        }

    # --- Funkce pro změnu theme ---
    def ChangeTheme():
        previous_theme = ms.themes["current_theme"]
        tdict = ms.themes["light"] if previous_theme == "light" else ms.themes["dark"]

        for vkey, vval in tdict.items():
            if vkey.startswith("theme"):
                st._config.set_option(vkey, vval)

        ms.themes["current_theme"] = "dark" if previous_theme == "light" else "light"
        ms.themes["refreshed"] = False

    # --- První run (fallback) ---
    if ms.themes["current_theme"] is None:
        ms.themes["current_theme"] = "light"

        tdict = ms.themes["light"]
        for vkey, vval in tdict.items():
            if vkey.startswith("theme"):
                st._config.set_option(vkey, vval)

        ms.themes["refreshed"] = False

    # --- Button ---
    btn_face = (
        ms.themes["light"]["button_face"]
        if ms.themes["current_theme"] == "light"
        else ms.themes["dark"]["button_face"]
    )

    st.sidebar.button(btn_face, on_click=ChangeTheme)

    # --- Rerun ---
    if ms.themes["refreshed"] == False:
        ms.themes["refreshed"] = True
        st.rerun()