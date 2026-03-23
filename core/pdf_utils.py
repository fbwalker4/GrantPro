"""
PDF utility functions for GrantPro branding and formatting.
"""
import re


def clean_markdown(text):
    """Convert markdown OR HTML content to reportlab-compatible XML tags.

    Handles two input formats:
    1. Markdown (legacy content): **bold**, *italic*, # headings
    2. HTML (from Quill rich text editor): <strong>, <em>, <u>, <h1>-<h3>, <ul>, <ol>, <li>, <blockquote>, <br>

    ReportLab Paragraph elements support a limited subset of HTML:
    <b>, <i>, <u>, <br/>, <font>, <a>, <sub>, <sup>, <strike>

    Returns cleaned text suitable for reportlab Paragraph elements.
    """
    if not text:
        return text

    # Detect if content is HTML (from Quill editor)
    is_html = bool(re.search(r'<(p|strong|em|h[1-3]|ul|ol|li|br|blockquote|u|s|a)\b', text))

    if is_html:
        return _clean_html_for_reportlab(text)
    else:
        return _clean_markdown_for_reportlab(text)


def _clean_html_for_reportlab(text):
    """Convert Quill HTML output to reportlab-compatible XML.

    Preserves: bold, italic, underline, strikethrough, line breaks, links.
    Converts: <strong> -> <b>, <em> -> <i>, <s> -> <strike>
    Strips: <p>, <h1>-<h3> (headings handled separately), <div>, <span>, <ul>, <ol>, <li>, <blockquote>
    """
    import html as html_module

    # Convert HTML tags to reportlab equivalents
    text = re.sub(r'<strong>(.*?)</strong>', r'<b>\1</b>', text, flags=re.DOTALL)
    text = re.sub(r'<em>(.*?)</em>', r'<i>\1</i>', text, flags=re.DOTALL)
    text = re.sub(r'<u>(.*?)</u>', r'<u>\1</u>', text, flags=re.DOTALL)
    text = re.sub(r'<s>(.*?)</s>', r'<strike>\1</strike>', text, flags=re.DOTALL)
    text = re.sub(r'<a\s+href="([^"]*)"[^>]*>(.*?)</a>', r'<a href="\1">\2</a>', text, flags=re.DOTALL)

    # Convert <br> and <br/> to reportlab <br/>
    text = re.sub(r'<br\s*/?>', '<br/>', text)

    # Convert </p> to paragraph breaks (double newline)
    text = re.sub(r'</p>\s*', '\n\n', text)
    text = re.sub(r'<p[^>]*>', '', text)

    # Convert headings to bold text (actual heading rendering happens in split_sections)
    text = re.sub(r'<h[1-3][^>]*>(.*?)</h[1-3]>', r'\n\n<b>\1</b>\n\n', text, flags=re.DOTALL)

    # Convert list items to bullet text
    text = re.sub(r'<li[^>]*>(.*?)</li>', '\n\u2022 \\1', text, flags=re.DOTALL)
    text = re.sub(r'</?[ou]l[^>]*>', '\n', text)

    # Convert blockquotes to italic
    text = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', r'<i>\1</i>', text, flags=re.DOTALL)

    # Strip any remaining HTML tags that reportlab doesn't understand
    # Keep: <b>, <i>, <u>, <strike>, <br/>, <a>, <font>, <sub>, <sup>
    allowed_tags = r'<(?:/?(?:b|i|u|strike|br/|a|font|sub|sup)[^>]*)>'
    # Find all tags, keep allowed ones, strip others
    def _strip_tag(m):
        tag = m.group(0)
        if re.match(allowed_tags, tag):
            return tag
        return ''
    text = re.sub(r'<[^>]+>', _strip_tag, text)

    # Unescape HTML entities that Quill may have added
    text = text.replace('&nbsp;', ' ')
    # But keep &amp; &lt; &gt; as-is since reportlab needs them

    # Clean up multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def _clean_markdown_for_reportlab(text):
    """Original markdown cleaning for legacy plain-text content."""
    # First, escape XML entities for reportlab (& must be first)
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')

    # Convert **bold** to <b>bold</b>  (must come before single *)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

    # Convert *italic* to <i>italic</i>
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)

    # Strip heading markers (### ## #) at line beginnings
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Remove horizontal rule markers (--- or ___ or ***)
    text = re.sub(r'^[\-_\*]{3,}\s*$', '', text, flags=re.MULTILINE)

    # Remove table markers: lines that are mostly pipes and dashes
    text = re.sub(r'^\|.*\|\s*$', '', text, flags=re.MULTILINE)
    # Remove table separator lines  |---|---|
    text = re.sub(r'^\|[\s\-\|:]+\|\s*$', '', text, flags=re.MULTILINE)

    # Remove bullet markers at start of lines (- or * used as list items)
    # but preserve the text
    text = re.sub(r'^[\-\*]\s+', '', text, flags=re.MULTILINE)

    # Clean up multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def split_markdown_sections(content):
    """Split content into heading/body pairs based on markdown OR HTML headings.

    Handles both:
    - Markdown: # Heading, ## Heading, ### Heading
    - HTML: <h1>Heading</h1>, <h2>Heading</h2>, <h3>Heading</h3>

    Returns a list of tuples: (heading_level, heading_text, body_text)
    where heading_level is 1-6 (or 0 for content before any heading).
    """
    if not content:
        return [(0, '', '')]

    # Detect HTML headings
    is_html = bool(re.search(r'<h[1-6][^>]*>', content))

    parts = []
    current_heading = None
    current_level = 0
    current_body = []

    for line in content.split('\n'):
        heading_match = None

        if is_html:
            # Match HTML headings: <h1>text</h1>, <h2>text</h2>, etc.
            heading_match = re.match(r'.*<h([1-6])[^>]*>(.*?)</h[1-6]>', line)
            if heading_match:
                level = int(heading_match.group(1))
                text = re.sub(r'<[^>]+>', '', heading_match.group(2)).strip()
                if current_body or current_heading:
                    parts.append((current_level, current_heading or '', '\n'.join(current_body)))
                current_level = level
                current_heading = text
                current_body = []
                continue

        # Match markdown headings
        md_match = re.match(r'^(#{1,6})\s+(.*)', line)
        if md_match:
            if current_body or current_heading:
                parts.append((current_level, current_heading or '', '\n'.join(current_body)))
            current_level = len(md_match.group(1))
            current_heading = md_match.group(2).strip()
            current_body = []
        else:
            current_body.append(line)

    # Save last section
    if current_body or current_heading:
        parts.append((current_level, current_heading or '', '\n'.join(current_body)))

    return parts


def detect_redundant_sentences(sections_dict, min_words=20):
    """Scan sections for sentences that appear in multiple sections.

    Args:
        sections_dict: dict of {section_name: content_text}
        min_words: minimum word count for a sentence to be checked (default 20)

    Returns:
        list of issue dicts: {title, message, severity} for the consistency validator.
    """
    issues = []

    # Build a map of sentence -> list of section names
    sentence_locations = {}

    for section_name, content in sections_dict.items():
        if not content:
            continue
        # Split into sentences (rough split on period/question/exclamation followed by space or end)
        sentences = re.split(r'(?<=[.!?])\s+', content)
        for sentence in sentences:
            # Normalize whitespace
            normalized = ' '.join(sentence.split())
            word_count = len(normalized.split())
            if word_count < min_words:
                continue
            # Use lowercase for comparison
            key = normalized.lower().strip()
            if key not in sentence_locations:
                sentence_locations[key] = set()
            sentence_locations[key].add(section_name)

    # Find sentences appearing in 2+ sections
    for sentence_key, section_set in sentence_locations.items():
        if len(section_set) >= 2:
            section_names = sorted(section_set)
            # Truncate the sentence for the message
            preview = sentence_key[:120] + ('...' if len(sentence_key) > 120 else '')
            issues.append({
                'title': 'Redundant Content Detected',
                'message': (
                    f'The following sentence appears in {len(section_names)} sections '
                    f'({", ".join(s.replace("_", " ").title() for s in section_names)}): '
                    f'"{preview}"'
                ),
                'severity': 'warning'
            })

    return issues


def add_grantpro_footer(canvas, doc):
    """Draw GrantPro branded footer on every page.

    Left side: "Assembled by GrantPro.org" in 7pt gray
    Right side: "Page X" in 7pt gray
    Position: 0.5 inches from bottom of page
    """
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor

    canvas.saveState()
    canvas.setFont('Helvetica', 7)
    canvas.setFillColor(HexColor('#999999'))

    page_width = doc.pagesize[0]
    y_pos = 0.5 * inch

    # Left side: branding
    canvas.drawString(doc.leftMargin, y_pos, "Assembled by GrantPro.org")

    # Right side: page number
    page_num_text = f"Page {canvas.getPageNumber()}"
    canvas.drawRightString(page_width - doc.rightMargin, y_pos, page_num_text)

    canvas.restoreState()


def _page_number_only(canvas, doc):
    """Draw only a page number footer (no branding)."""
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor

    canvas.saveState()
    canvas.setFont('Helvetica', 7)
    canvas.setFillColor(HexColor('#999999'))

    page_width = doc.pagesize[0]
    y_pos = 0.5 * inch

    page_num_text = f"Page {canvas.getPageNumber()}"
    canvas.drawRightString(page_width - doc.rightMargin, y_pos, page_num_text)

    canvas.restoreState()


def get_footer_callback(show_branding=True):
    """Return the footer callback function for use with reportlab's
    onFirstPage / onLaterPages / afterPage parameters in BaseDocTemplate.build().

    Args:
        show_branding: If True (default), includes "Assembled by GrantPro.org".
                       If False, only page numbers are shown.

    Usage:
        footer = get_footer_callback(show_branding=True)
        doc.build(story, onFirstPage=footer, onLaterPages=footer)
    """
    if show_branding:
        return add_grantpro_footer
    return _page_number_only
