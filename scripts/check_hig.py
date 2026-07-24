from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / ".build" / "site"
CUSTOM_CSS = ROOT / "stylesheets" / "extra.css"
GENERATED_CUSTOM_CSS = SITE / "stylesheets" / "extra.css"
SITE_URL = "https://belugarex.github.io/foggy-notes/"
SITE_HOST = urlparse(SITE_URL).netloc
MINIMUM_CONTRAST = 4.5
INCREASED_CONTRAST = 7.0
MINIMUM_BODY_TEXT = 17.0
MINIMUM_TOUCH_TARGET = 44.0
MINIMUM_POINTER_TARGET = 28.0
ASCII_ROUTE_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
DESKTOP_LAYOUT_MEDIA = "@media screen and (min-width: 52.5em)"
SECONDARY_HIDE_MEDIA = (
    "@media screen and (min-width: 52.5em) and (max-width: 89.9844em)"
)
SECONDARY_SHOW_MEDIA = "@media screen and (min-width: 90em)"
WIDE_LAYOUT_MEDIA = "@media screen and (min-width: 80em)"


class PageInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.html_lang = ""
        self.viewport = ""
        self.has_main = False
        self.has_nav = False
        self.has_skip_link = False
        self.article_depth = 0
        self.headings: list[int] = []
        self.missing_alt: list[str] = []
        self.page_urls: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())

        if tag == "html":
            self.html_lang = attributes.get("lang") or ""
        elif tag == "meta" and attributes.get("name") == "viewport":
            self.viewport = attributes.get("content") or ""
        elif tag == "main":
            self.has_main = True
        elif tag == "nav":
            self.has_nav = True
        elif tag == "a":
            href = attributes.get("href")
            if href:
                self.page_urls.append(href)
            if "md-skip" in classes:
                self.has_skip_link = True
        elif tag == "link" and "canonical" in (
            attributes.get("rel") or ""
        ).split():
            href = attributes.get("href")
            if href:
                self.page_urls.append(href)
        elif tag == "meta" and attributes.get("property") == "og:url":
            content = attributes.get("content")
            if content:
                self.page_urls.append(content)
        elif tag == "article" and "md-content__inner" in classes:
            self.article_depth += 1
        elif self.article_depth and re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))
        elif tag == "img":
            is_decorative = (
                attributes.get("aria-hidden") == "true"
                or attributes.get("role") in {"none", "presentation"}
            )
            if not is_decorative and not (attributes.get("alt") or "").strip():
                self.missing_alt.append(attributes.get("src") or "<unknown>")

    def handle_endtag(self, tag: str) -> None:
        if tag == "article" and self.article_depth:
            self.article_depth -= 1


def parse_hex_color(value: str) -> tuple[int, int, int]:
    return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))


def linearize(channel: int) -> float:
    value = channel / 255
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def relative_luminance(color: str) -> float:
    red, green, blue = (linearize(channel) for channel in parse_hex_color(color))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground: str, background: str) -> float:
    lighter, darker = sorted(
        (relative_luminance(foreground), relative_luminance(background)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def extract_blocks(css: str, selector: str) -> list[str]:
    blocks: list[str] = []
    offset = 0
    while True:
        start = css.find(selector, offset)
        if start < 0:
            return blocks
        opening_brace = css.find("{", start + len(selector))
        if opening_brace < 0 or css[start + len(selector) : opening_brace].strip():
            offset = start + len(selector)
            continue
        body, closing_brace = extract_braced_body(css, opening_brace)
        blocks.append(body)
        offset = closing_brace + 1


def parse_color_variables(block: str) -> dict[str, str]:
    return {
        name: value.lower()
        for name, value in re.findall(
            r"(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;", block
        )
    }


def extract_braced_body(css: str, opening_brace: int) -> tuple[str, int]:
    depth = 0
    for index in range(opening_brace, len(css)):
        if css[index] == "{":
            depth += 1
        elif css[index] == "}":
            depth -= 1
            if depth == 0:
                return css[opening_brace + 1 : index], index
    raise ValueError("unterminated CSS block")


def extract_media_body(css: str, media_query: str) -> str:
    start = css.find(media_query)
    if start < 0:
        raise ValueError(f"missing {media_query}")
    opening_brace = css.find("{", start)
    try:
        body, _ = extract_braced_body(css, opening_brace)
        return body
    except ValueError as error:
        raise ValueError(f"unterminated {media_query}") from error


def parse_rules(css: str) -> dict[str, dict[str, str]]:
    rules: dict[str, dict[str, str]] = {}
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        declarations = {
            name.strip(): value.strip()
            for name, value in re.findall(r"([a-z-]+)\s*:\s*([^;]+);", body)
        }
        for selector in selectors.split(","):
            rules.setdefault(selector.strip(), {}).update(declarations)
    return rules


def length_to_pixels(value: str, root_pixels: float) -> float:
    match = re.fullmatch(r"([0-9.]+)(rem|px)", value)
    if match is None:
        raise ValueError(f"unsupported CSS length: {value}")
    number = float(match.group(1))
    return number * root_pixels if match.group(2) == "rem" else number


def material_root_pixels(theme_css: str, failures: list[str]) -> float | None:
    root_match = re.search(
        r"html\s*\{[^}]*font-size:\s*([0-9.]+)%", theme_css
    )
    if root_match is None:
        failures.append("Material CSS: missing root font size")
        return None
    try:
        return 16 * float(root_match.group(1)) / 100
    except ValueError:
        failures.append("Material CSS: invalid root font size")
        return None


def check_body_text_size(
    custom_css: str, root_pixels: float, failures: list[str]
) -> None:
    first_media = custom_css.find("@media")
    base_scope = custom_css if first_media < 0 else custom_css[:first_media]
    font_size = parse_rules(base_scope).get(".md-typeset", {}).get("font-size")
    if font_size is None:
        failures.append(".md-typeset: missing base font-size")
        return
    try:
        pixels = length_to_pixels(font_size, root_pixels)
    except ValueError as error:
        failures.append(f".md-typeset: {error}")
        return
    if pixels < MINIMUM_BODY_TEXT:
        failures.append(
            f".md-typeset: body text computes to {pixels:.1f}px, expected at "
            f"least {MINIMUM_BODY_TEXT:.0f}px"
        )


def check_generated_custom_css(css: str, failures: list[str]) -> None:
    if not GENERATED_CUSTOM_CSS.is_file():
        failures.append("generated extra.css is missing")
        return
    if GENERATED_CUSTOM_CSS.read_text(encoding="utf-8") != css:
        failures.append(
            "generated extra.css is stale; run prepare_site.py and rebuild"
        )


def check_no_glass(css: str, failures: list[str]) -> None:
    forbidden_markers = (
        "backdrop-filter",
        "blur(",
        "rgba(",
        "hsla(",
        "--fog-material",
        "--fog-header-material",
        "--fog-sidebar-material",
    )
    for marker in forbidden_markers:
        if marker in css:
            failures.append(f"extra.css: glass or translucency is forbidden: {marker}")


def check_document_style(css: str, failures: list[str]) -> None:
    first_media = css.find("@media")
    base_scope = css if first_media < 0 else css[:first_media]
    rules = parse_rules(base_scope)

    expected_rules = {
        ".md-typeset": {
            "font-size": "0.85rem",
            "line-height": "1.65",
        },
        ".md-header__title": {
            "font-size": "0.9rem",
            "font-weight": "600",
        },
        ".md-typeset h1": {
            "padding-bottom": "0",
            "border-bottom": "0",
        },
        ".md-typeset h1 + p": {
            "color": "var(--md-default-fg-color--light)",
            "font-size": "1.02rem",
        },
        ".md-typeset table:not([class])": {
            "border-radius": "0",
            "box-shadow": "none",
        },
        ".md-typeset img": {
            "box-shadow": "none",
        },
        ".md-typeset .fog-home-cta": {
            "box-shadow": "none",
        },
        ".md-top": {
            "box-shadow": "none",
        },
        ".md-footer": {
            "background-color": "var(--fog-surface-muted)",
        },
    }
    for selector, expected in expected_rules.items():
        declarations = rules.get(selector, {})
        for property_name, value in expected.items():
            if declarations.get(property_name) != value:
                failures.append(
                    f"{selector}: expected {property_name}: {value}"
                )

    root_blocks = extract_blocks(base_scope, ":root")
    if len(root_blocks) != 1:
        failures.append("extra.css: expected one :root token block")
        return
    radius_tokens = dict(
        re.findall(
            r"(--fog-radius-[a-z]+)\s*:\s*([0-9.]+rem)\s*;",
            root_blocks[0],
        )
    )
    expected_radii = {
        "--fog-radius-sm": "0.2rem",
        "--fog-radius-md": "0.3rem",
        "--fog-radius-lg": "0.4rem",
    }
    if radius_tokens != expected_radii:
        failures.append(
            "extra.css: document radii must remain the 4/6/8px token scale"
        )

    expected_chrome = {
        "default": {
            "--fog-header-bg": "#f5f5f7",
            "--fog-header-fg": "#1d1d1f",
            "--fog-header-control": "#ffffff",
            "--fog-header-control-hover": "#e8e8ed",
            "--fog-header-border": "#d2d2d7",
            "--fog-header-muted": "#6e6e73",
        },
        "slate": {
            "--fog-header-bg": "#1d1d1f",
            "--fog-header-fg": "#f5f5f7",
            "--fog-header-control": "#2c2c2e",
            "--fog-header-control-hover": "#3a3a3c",
            "--fog-header-border": "#424245",
            "--fog-header-muted": "#aeaeb2",
        },
    }
    for scheme, expected in expected_chrome.items():
        selector = f'[data-md-color-scheme="{scheme}"]'
        blocks = extract_blocks(base_scope, selector)
        if len(blocks) != 1:
            failures.append(f"{scheme}: expected one solid chrome token block")
            continue
        variables = parse_color_variables(blocks[0])
        for token, value in expected.items():
            if variables.get(token) != value:
                failures.append(f"{scheme}: expected {token}: {value}")


def check_wide_layout(css: str, failures: list[str]) -> None:
    try:
        rules = parse_rules(extract_media_body(css, WIDE_LAYOUT_MEDIA))
    except ValueError as error:
        failures.append(str(error))
        return

    max_width = rules.get(".md-main__inner", {}).get("max-width")
    if max_width is None:
        failures.append(".md-main__inner: missing wide-layout max-width")
    else:
        for requirement in ("clamp(", "vw", "rem", "calc(100vw"):
            if requirement not in max_width:
                failures.append(
                    ".md-main__inner: wide-layout max-width must combine "
                    "viewport growth with a readable rem cap"
                )
                break

    for selector in (".md-grid", ".md-header__inner"):
        if "max-width" in rules.get(selector, {}):
            failures.append(
                f"{selector}: wide layout must not stretch the shared header grid"
            )


def check_adaptive_sidebars(css: str, failures: list[str]) -> None:
    try:
        desktop_rules = parse_rules(
            extract_media_body(css, DESKTOP_LAYOUT_MEDIA)
        )
        hidden_rules = parse_rules(
            extract_media_body(css, SECONDARY_HIDE_MEDIA)
        )
        shown_rules = parse_rules(
            extract_media_body(css, SECONDARY_SHOW_MEDIA)
        )
    except ValueError as error:
        failures.append(str(error))
        return

    primary_basis = desktop_rules.get(".md-sidebar--primary", {}).get("flex")
    if primary_basis is None or "min(" not in primary_basis or "vw" not in primary_basis:
        failures.append(
            ".md-sidebar--primary: width must adapt to viewport and text growth"
        )

    hidden_display = hidden_rules.get(
        ".md-sidebar--secondary:not([hidden])", {}
    ).get("display")
    if hidden_display != "none":
        failures.append(
            ".md-sidebar--secondary: tertiary navigation must collapse before 90em"
        )

    secondary = shown_rules.get(".md-sidebar--secondary", {})
    if secondary.get("display") != "block":
        failures.append(
            ".md-sidebar--secondary: tertiary navigation must return at 90em"
        )
    for property_name, expected in (
        ("position", "sticky"),
        ("height", "calc(100vh - 2.4rem)"),
        ("overflow", "hidden"),
        ("background-color", "var(--fog-sidebar-primary)"),
    ):
        if secondary.get(property_name) != expected:
            failures.append(
                ".md-sidebar--secondary: expected a full-height control layer "
                f"({property_name}: {expected})"
            )
    secondary_basis = secondary.get("flex")
    if (
        secondary_basis is None
        or "min(" not in secondary_basis
        or "vw" not in secondary_basis
    ):
        failures.append(
            ".md-sidebar--secondary: width must adapt to viewport and text growth"
        )


def check_reading_surface(css: str, failures: list[str]) -> None:
    first_media = css.find("@media")
    base_scope = css if first_media < 0 else css[:first_media]
    rules = parse_rules(base_scope)
    expected = {
        "box-sizing": "border-box",
        "width": "100%",
        "max-width": "var(--fog-reading-width)",
        "background-color": "transparent",
        "border": "0",
        "border-radius": "0",
        "box-shadow": "none",
    }
    reading_surface = rules.get(".md-content__inner", {})
    for property_name, value in expected.items():
        if reading_surface.get(property_name) != value:
            failures.append(
                f".md-content__inner: expected {property_name}: {value}"
            )

    centered_surface = rules.get(
        "[dir] .md-main__inner > .md-content > "
        ".md-content__inner.md-typeset",
        {},
    )
    if centered_surface.get("margin-inline") != "auto":
        failures.append(
            ".md-content__inner: missing high-specificity auto inline margins"
        )

    content_layer = rules.get(".md-content", {})
    if content_layer.get("background-color") != "var(--fog-surface)":
        failures.append(".md-content: expected a stable solid content surface")
    for property_name in ("backdrop-filter", "-webkit-backdrop-filter"):
        if property_name in content_layer or property_name in reading_surface:
            failures.append(
                f".md-content: {property_name} belongs on controls, not content"
            )

    header = rules.get(".md-header", {})
    if header.get("background-color") != "var(--fog-header-bg)":
        failures.append(".md-header: expected a solid header background")
    for property_name in ("backdrop-filter", "-webkit-backdrop-filter"):
        if property_name in header:
            failures.append(f".md-header: solid chrome must not use {property_name}")

    try:
        desktop_rules = parse_rules(
            extract_media_body(css, DESKTOP_LAYOUT_MEDIA)
        )
    except ValueError as error:
        failures.append(str(error))
        return
    desktop_content = desktop_rules.get(".md-content", {})
    if desktop_content.get("border-inline") != (
        "0.05rem solid var(--fog-border)"
    ):
        failures.append(
            ".md-content: desktop split view needs semantic pane separators"
        )
    primary_sidebar = desktop_rules.get(".md-sidebar--primary", {})
    if primary_sidebar.get("background-color") != "var(--fog-sidebar-primary)":
        failures.append(
            ".md-sidebar--primary: expected a solid navigation surface"
        )
    primary_label = desktop_rules.get(
        ".md-sidebar--primary .md-sidebar__inner::before", {}
    )
    if primary_label.get("content") != '"目录"':
        failures.append(".md-sidebar--primary: expected a concise 目录 label")
    primary_active = desktop_rules.get(
        ".md-sidebar--primary .md-nav__link--active", {}
    )
    for property_name, value in (
        ("background-color", "transparent"),
        ("border-inline-start-color", "var(--md-accent-fg-color)"),
        ("border-radius", "0"),
    ):
        if primary_active.get(property_name) != value:
            failures.append(
                ".md-sidebar--primary: active navigation must use a plain "
                f"text-and-rule treatment ({property_name}: {value})"
            )

    home_action = rules.get(".md-typeset .fog-home-cta", {})
    if home_action.get("min-height") != "2.2rem":
        failures.append(".fog-home-cta: expected a 2.2rem minimum height")

    mobile_media = "@media screen and (max-width: 44.9844em)"
    try:
        mobile_rules = parse_rules(extract_media_body(css, mobile_media))
    except ValueError as error:
        failures.append(str(error))
        return
    mobile_surface = mobile_rules.get(".md-content__inner", {})
    for property_name, value in (
        ("background-color", "transparent"),
        ("border", "0"),
        ("border-radius", "0"),
        ("box-shadow", "none"),
    ):
        if mobile_surface.get(property_name) != value:
            failures.append(
                ".md-content__inner: mobile reading surface must become "
                f"edge-to-edge ({property_name}: {value})"
            )


def is_internal_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme and parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc and parsed.netloc != SITE_HOST:
        return False
    return True


def check_ascii_url(url: str, context: str, failures: list[str]) -> None:
    if not is_internal_url(url):
        return
    parsed = urlparse(url)
    decoded = unquote("?".join((parsed.path, parsed.query))).rstrip("?")
    if parsed.fragment:
        decoded = f"{decoded}#{unquote(parsed.fragment)}"
    if any(ord(character) > 127 for character in decoded):
        failures.append(f"{context}: internal URL is not ASCII: {url}")


def check_contrast(css: str, failures: list[str]) -> None:
    semantic_pairs = (
        ("--md-default-fg-color", "--md-default-bg-color"),
        ("--md-default-fg-color--light", "--md-default-bg-color"),
        ("--md-default-fg-color--lighter", "--md-default-bg-color"),
        ("--md-typeset-a-color", "--md-default-bg-color"),
        ("--md-accent-fg-color", "--md-default-bg-color"),
        ("--fog-muted", "--md-default-bg-color"),
        ("--md-default-fg-color", "--fog-surface"),
        ("--md-default-fg-color--light", "--fog-surface"),
        ("--md-default-fg-color--lighter", "--fog-surface"),
        ("--md-typeset-a-color", "--fog-surface"),
        ("--md-accent-fg-color", "--fog-surface"),
        ("--fog-muted", "--fog-surface"),
        ("--md-code-fg-color", "--md-code-bg-color"),
        ("--fog-header-fg", "--fog-header-bg"),
        ("--fog-on-accent", "--md-accent-fg-color"),
        ("--fog-on-accent", "--fog-accent-strong"),
    )
    increased_pairs = (
        ("--md-default-fg-color--light", "--md-default-bg-color"),
        ("--md-default-fg-color--lighter", "--md-default-bg-color"),
        ("--md-typeset-a-color", "--md-default-bg-color"),
        ("--md-accent-fg-color", "--md-default-bg-color"),
        ("--fog-muted", "--md-default-bg-color"),
        ("--md-default-fg-color--light", "--fog-surface"),
        ("--md-default-fg-color--lighter", "--fog-surface"),
        ("--md-typeset-a-color", "--fog-surface"),
        ("--md-accent-fg-color", "--fog-surface"),
        ("--fog-muted", "--fog-surface"),
        ("--fog-on-accent", "--md-accent-fg-color"),
    )

    first_media = css.find("@media")
    base_scope = css if first_media < 0 else css[:first_media]
    try:
        increased_scope = extract_media_body(css, "@media (prefers-contrast: more)")
    except ValueError as error:
        failures.append(str(error))
        return

    for scheme in ("default", "slate"):
        selector = f'[data-md-color-scheme="{scheme}"]'
        base_blocks = extract_blocks(base_scope, selector)
        increased_blocks = extract_blocks(increased_scope, selector)
        if len(base_blocks) != 1 or len(increased_blocks) != 1:
            failures.append(
                f"{scheme}: expected one base and one increased-contrast token block"
            )
            continue

        base = parse_color_variables(base_blocks[0])
        increased = base | parse_color_variables(increased_blocks[0])

        for foreground_name, background_name in semantic_pairs:
            foreground = base.get(foreground_name)
            background = base.get(background_name)
            if foreground is None or background is None:
                failures.append(
                    f"{scheme}: missing {foreground_name} or {background_name}"
                )
                continue
            ratio = contrast_ratio(foreground, background)
            if ratio < MINIMUM_CONTRAST:
                failures.append(
                    f"{scheme}: {foreground_name} on {background_name} is "
                    f"{ratio:.2f}:1, expected at least {MINIMUM_CONTRAST}:1"
                )

        for foreground_name, background_name in increased_pairs:
            ratio = contrast_ratio(
                increased[foreground_name], increased[background_name]
            )
            if ratio < INCREASED_CONTRAST:
                failures.append(
                    f"{scheme} increased contrast: {foreground_name} is "
                    f"{ratio:.2f}:1, expected at least {INCREASED_CONTRAST}:1"
                )


def check_pointer_targets(
    custom_css: str, root_pixels: float, failures: list[str]
) -> None:
    for pointer, minimum in (
        ("coarse", MINIMUM_TOUCH_TARGET),
        ("fine", MINIMUM_POINTER_TARGET),
    ):
        media_query = f"@media (pointer: {pointer})"
        try:
            rules = parse_rules(extract_media_body(custom_css, media_query))
        except ValueError as error:
            failures.append(str(error))
            continue

        for selector in (
            ".md-header__button",
            ".md-header__option",
            ".md-search__button",
            ".md-source",
            ".md-nav__link",
            ".md-top",
        ):
            declarations = rules.get(selector, {})
            for property_name in ("min-inline-size", "min-block-size"):
                value = declarations.get(property_name)
                if value is None:
                    failures.append(
                        f"{selector}: missing {pointer} {property_name}"
                    )
                    continue
                pixels = length_to_pixels(value, root_pixels)
                if pixels < minimum:
                    failures.append(
                        f"{selector}: {pointer} {property_name} computes to "
                        f"{pixels:.1f}px, expected at least {minimum:.0f}px"
                    )

        search_height = rules.get(".md-search__form", {}).get("min-block-size")
        if search_height is None:
            failures.append(
                f".md-search__form: missing {pointer} min-block-size"
            )
        elif length_to_pixels(search_height, root_pixels) < minimum:
            failures.append(
                f".md-search__form: {pointer} height is below {minimum:.0f}px"
            )


def check_pages(failures: list[str]) -> int:
    pages = sorted(SITE.rglob("index.html"))
    if not pages:
        failures.append("no generated index.html pages found")
        return 0

    for page in pages:
        inspector = PageInspector()
        content = page.read_text(encoding="utf-8")
        inspector.feed(content)
        relative_path = page.relative_to(SITE)

        for directory in relative_path.parts[:-1]:
            if ASCII_ROUTE_PATTERN.fullmatch(directory) is None:
                failures.append(
                    f"{relative_path}: generated page directory is not ASCII "
                    f"kebab-case: {directory}"
                )

        if not inspector.html_lang.startswith("zh"):
            failures.append(f"{relative_path}: html language is not Chinese")
        if "width=device-width" not in inspector.viewport:
            failures.append(f"{relative_path}: viewport is not device-width")
        if not inspector.has_main or not inspector.has_nav:
            failures.append(f"{relative_path}: missing main or nav landmark")
        if not inspector.has_skip_link:
            failures.append(f"{relative_path}: missing skip link")
        if inspector.headings.count(1) != 1:
            failures.append(f"{relative_path}: expected exactly one article h1")
        for previous, current in zip(inspector.headings, inspector.headings[1:]):
            if current > previous + 1:
                failures.append(
                    f"{relative_path}: heading level jumps from h{previous} to h{current}"
                )
        for source in inspector.missing_alt:
            failures.append(f"{relative_path}: image has empty alt text: {source}")
        for url in inspector.page_urls:
            check_ascii_url(url, str(relative_path), failures)
        if "fonts.googleapis.com" in content:
            failures.append(f"{relative_path}: remote Google Fonts are still loaded")

    return len(pages)


def check_generated_indexes(failures: list[str]) -> None:
    sitemap = SITE / "sitemap.xml"
    if not sitemap.is_file():
        failures.append("generated sitemap.xml is missing")
    else:
        for url in re.findall(r"<loc>([^<]+)</loc>", sitemap.read_text("utf-8")):
            check_ascii_url(url, "sitemap.xml", failures)

    search_index = SITE / "search" / "search_index.json"
    if not search_index.is_file():
        failures.append("generated search index is missing")
        return
    try:
        search_data = json.loads(search_index.read_text("utf-8"))
    except json.JSONDecodeError as error:
        failures.append(f"search index is invalid JSON: {error}")
        return
    for document in search_data.get("docs", []):
        location = document.get("location")
        if isinstance(location, str):
            check_ascii_url(location, "search index", failures)


def main() -> None:
    if not CUSTOM_CSS.is_file() or not SITE.is_dir():
        raise FileNotFoundError("Run mkdocs build before checking the HIG baseline")

    custom_css = CUSTOM_CSS.read_text(encoding="utf-8")
    theme_stylesheets = sorted(
        (SITE / "assets" / "stylesheets").glob("main.*.min.css")
    )
    if not theme_stylesheets:
        raise FileNotFoundError("Generated Material stylesheet was not found")
    theme_css = theme_stylesheets[0].read_text(encoding="utf-8")
    failures: list[str] = []

    check_generated_custom_css(custom_css, failures)

    for requirement in (
        '@charset "UTF-8";',
        "color-scheme: light dark",
        "::selection",
        ":focus-visible",
        "touch-action: manipulation",
        "@media (prefers-contrast: more)",
        "@media (forced-colors: active)",
        "@media (prefers-reduced-motion: reduce)",
        "env(safe-area-inset-left)",
        "env(safe-area-inset-right)",
        "--fog-header-bg",
        "--fog-sidebar-primary",
        "--fog-reading-width",
    ):
        if requirement not in custom_css:
            failures.append(f"extra.css: missing {requirement}")

    check_contrast(custom_css, failures)
    root_pixels = material_root_pixels(theme_css, failures)
    if root_pixels is not None:
        check_body_text_size(custom_css, root_pixels, failures)
        check_pointer_targets(custom_css, root_pixels, failures)
    check_no_glass(custom_css, failures)
    check_document_style(custom_css, failures)
    check_wide_layout(custom_css, failures)
    check_adaptive_sidebars(custom_css, failures)
    check_reading_surface(custom_css, failures)
    page_count = check_pages(failures)
    check_generated_indexes(failures)

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        raise SystemExit(1)

    print(
        f"HIG baseline passed for {page_count} pages: contrast, targets, "
        "semantics, system fonts, solid no-glass chrome, adaptive sidebars, "
        "wide layout, fresh generated CSS, accessibility preferences, and "
        "ASCII URLs."
    )


if __name__ == "__main__":
    main()