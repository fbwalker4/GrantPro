"""
PDF utility functions for GrantPro branding and formatting.
"""
import re


def clean_markdown(text):
    """Convert markdown formatting to reportlab-compatible XML tags and strip artifacts.

    Converts:
      **bold** -> <b>bold</b>
      *italic* -> <i>italic</i>
      ### / ## / # headings -> stripped (handled separately as Heading styles)
      --- horizontal rules -> removed
      | table markers -> removed
      Remaining markdown artifacts -> stripped

    Returns cleaned text suitable for reportlab Paragraph elements.
    """
    if not text:
        return text

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
    """Split content into heading/body pairs based on markdown headings.

    Returns a list of tuples: (heading_level, heading_text, body_text)
    where heading_level is 1-6 (or 0 for content before any heading).
    """
    parts = []
    current_heading = None
    current_level = 0
    current_body = []

    for line in (content or '').split('\n'):
        heading_match = re.match(r'^(#{1,6})\s+(.*)', line)
        if heading_match:
            # Save previous section
            if current_body or current_heading:
                parts.append((current_level, current_heading or '', '\n'.join(current_body)))
            current_level = len(heading_match.group(1))
            current_heading = heading_match.group(2).strip()
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
