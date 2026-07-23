from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / ".build" / "site"
CUSTOM_CSS = ROOT / "stylesheets" / "extra.css"
SITE_URL = "https://belugarex.github.io/foggy-notes/"
SITE_HOST = urlparse(SITE_URL).netloc
MINIMUM_CONTRAST = 4.5
INCREASED_CONTRAST = 7.0
MINIMUM_BODY_TEXT = 17.0
MINIMUM_TOUCH_TARGET = 44.0
MINIMUM_POINTER_TARGET = 28.0
ASCII_ROUTE_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


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


def check_transparency_fallback(css: str, failures: list[str]) -> None:
    media_query = "@media (prefers-reduced-transparency: reduce)"
    try:
        rules = parse_rules(extract_media_body(css, media_query))
    except ValueError as error:
        failures.append(str(error))
        return

    for selector in (".md-header", ".md-sidebar--primary"):
        declarations = rules.get(selector, {})
        if "background-color" not in declarations:
            failures.append(f"{selector}: missing reduced-transparency background")
        if declarations.get("backdrop-filter") != "none":
            failures.append(f"{selector}: backdrop-filter must be none when reduced")
        if declarations.get("-webkit-backdrop-filter") != "none":
            failures.append(
                f"{selector}: -webkit-backdrop-filter must be none when reduced"
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
        ("--md-code-fg-color", "--md-code-bg-color"),
        ("--fog-header-fg", "--fog-header-bg"),
    )
    increased_pairs = (
        ("--md-default-fg-color--light", "--md-default-bg-color"),
        ("--md-default-fg-color--lighter", "--md-default-bg-color"),
        ("--md-typeset-a-color", "--md-default-bg-color"),
        ("--md-accent-fg-color", "--md-default-bg-color"),
        ("--fog-muted", "--md-default-bg-color"),
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

    for requirement in (
        "color-scheme: light dark",
        "::selection",
        ":focus-visible",
        "touch-action: manipulation",
        "backdrop-filter",
        "@media (prefers-contrast: more)",
        "@media (forced-colors: active)",
        "@media (prefers-reduced-transparency: reduce)",
        "@media (prefers-reduced-motion: reduce)",
        "env(safe-area-inset-left)",
        "env(safe-area-inset-right)",
    ):
        if requirement not in custom_css:
            failures.append(f"extra.css: missing {requirement}")

    check_contrast(custom_css, failures)
    root_pixels = material_root_pixels(theme_css, failures)
    if root_pixels is not None:
        check_body_text_size(custom_css, root_pixels, failures)
        check_pointer_targets(custom_css, root_pixels, failures)
    check_transparency_fallback(custom_css, failures)
    page_count = check_pages(failures)
    check_generated_indexes(failures)

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        raise SystemExit(1)

    print(
        f"HIG baseline passed for {page_count} pages: contrast, targets, "
        "semantics, system fonts, accessibility preferences, and ASCII URLs."
    )


if __name__ == "__main__":
    main()