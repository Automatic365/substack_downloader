# UI Overhaul Plan: Project "Neon Terminal"

## 1. Objective
Transform the `Substack Downloader` interface into a high-fidelity, "Hacker Aesthetic" / Cyberpunk terminal UI. The goal is to create a visually stunning, immersive experience that mimics a high-tech command interface while preserving 100% of the underlying Python functionality.

## 2. Design Philosophy
- **Visual Style**: Retro-futuristic terminal (CRT monitor style).
- **Color Palette**: 
  - Background: Deep Void Black (`#000000` or `#050505`)
  - Primary Text: Matrix Green (`#00FF41`) or Cyber Cyan (`#00F3FF`)
  - Accents: Danger Red (`#FF0055`) for errors, System Amber (`#FFB000`) for warnings.
- **Typography**: Strictly `Monospace` (Courier, Fira Code, or similar system fonts).
- **Shapes**: Brutalist. No rounded corners. 90-degree angles only.

## 3. Implementation Steps

### Phase 1: Global Configuration (`.streamlit/config.toml`)
Update Streamlit's base theme settings to establish the foundation.
```toml
[theme]
primaryColor = "#00FF41"
backgroundColor = "#000000"
secondaryBackgroundColor = "#0C0C0C"
textColor = "#00FF41"
font = "monospace"
```

### Phase 2: CSS Injection (`app.py`)
Inject a sophisticated CSS block (`st.markdown(..., unsafe_allow_html=True)`) to override default Streamlit components.

**Key CSS Features:**
1.  **CRT Scanlines**: An overlay `pointer-events: none` div with repeating linear gradients to simulate monitor scanlines.
2.  **Glow Effects**: Text-shadows on headers and input text to simulate phosphor luminescence.
    - `text-shadow: 0 0 5px #00FF41;`
3.  **Input Fields**:
    - Remove white backgrounds.
    - Set borders to 1px solid Green/Cyan.
    - Add a blinking cursor effect if possible.
4.  **Buttons**:
    - Transparent background with solid colored borders.
    - `hover` state: Invert colors (Background becomes Green, Text becomes Black).
    - "Glitch" or "Shake" animation on active state.
5.  **Containers**:
    - Add "Tech Borders" (corner brackets) to groups and expanders.

### Phase 3: Content & Copy Updates (`app.py`)
Refine the text to match the "System Interface" persona.

-   **Title**: `>_ SUBSTACK_BREACH_PROTOCOL v2.0`
-   **Headers**: 
    - `Target Acquisition` (was "Enter Substack URL")
    - `Payload Configuration` (was "Format Option")
    - `System Resources` (was "Concurrency Settings")
-   **Status Messages**:
    - "Processing..." -> `[SYSTEM] EXECUTING BATCH DOWNLOAD...`
    - "Success" -> `[SUCCESS] PAYLOAD SECURED.`
    - "Error" -> `[CRITICAL] CONNECTION SEVERED.`

## 4. Execution Plan
1.  **Backup**: Ensure `app.py` is backed up (git is already handling this).
2.  **Config**: Apply `config.toml` changes.
3.  **Injector**: Create a `load_css()` function in `app.py` containing the styles.
4.  **Refactor**: Go through `app.py` top-to-bottom, wrapping elements in the new styling containers and updating text labels.
5.  **Verify**: Run the app to ensure no functional regressions (download logic remains untouched).
