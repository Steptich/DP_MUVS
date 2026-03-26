
import streamlit as st

def theme_mode():
    ms = st.session_state

    # --- Inicializace session_state ---
    if "theme_mode" not in ms:
        ms.theme_mode = "light"  # default

    if "theme_applied" not in ms:
        ms.theme_applied = False

    # --- Definice témat ---
    themes = {
        "light": {
            "theme.base": "light",
            "theme.primaryColor": "#F7931A",
        },
        "dark": {
            "theme.base": "dark",
            "theme.primaryColor": "#F7931A",
        },
    }

    # --- Aplikace theme při prvním run ---
    if not ms.theme_applied:
        for k, v in themes[ms.theme_mode].items():
            st._config.set_option(k, v)
        ms.theme_applied = True
        st.rerun()  # nutné pro aplikaci theme

    # --- Segmented control pro změnu ---
    selected = st.segmented_control(
        "Motiv",
        options=["light", "dark"],
        format_func=lambda x: "🌞 Světlý" if x == "light" else "🌜 Tmavý",
        default=ms.theme_mode,
        key="theme_selector",
        width="stretch"
    )

    # --- Pokud uživatel změní mode ---
    if selected != ms.theme_mode:
        ms.theme_mode = selected
        for k, v in themes[selected].items():
            st._config.set_option(k, v)
        st.rerun()  # rerun po změně

    return ms.theme_mode

def theme_button():
    ms = st.session_state

    # --- Inicializace témat ---
    if "themes" not in ms:
        ms.themes = {
            "current_theme": None,
            "refreshed": True,
            "name": None,
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
        ms.themes["name"] = "Tmavý motiv" if previous_theme == "light" else "Světlý motiv"
        ms.themes["refreshed"] = False

    # --- První run (fallback) ---
    if ms.themes["current_theme"] is None:
        ms.themes["current_theme"] = "light"
        ms.themes["name"] = "Světlý motiv"
        tdict = ms.themes["dark"]
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

    st.sidebar.button(label=f"{ms.themes["name"]}",icon=btn_face, on_click=ChangeTheme)

    # --- Rerun ---
    if ms.themes["refreshed"] == False:
        ms.themes["refreshed"] = True
        st.rerun()