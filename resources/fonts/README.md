# Fonts directory

XeLaTeX may not find the **FontAwesome** font by name. To fix the "Font Awesome cannot be found" error:

1. Locate the font in your TeX tree:
   ```bash
   kpsewhich FontAwesome.otf
   ```
2. Copy it here so the resume can load it by path:
   ```bash
   cp "$(kpsewhich FontAwesome.otf)" "$(dirname "$0")/resources/fonts/"
   ```
   Or from the project root: `cp $(kpsewhich FontAwesome.otf) resources/fonts/`

If your TeX distribution does not include the font (e.g. minimal TeX Live), install the `fontawesome` package or download Font Awesome 4 and place `FontAwesome.otf` in this directory.
