"""
PDF utility functions for GrantPro branding and formatting.
"""


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


def get_footer_callback():
    """Return the footer callback function for use with reportlab's
    onFirstPage / onLaterPages / afterPage parameters in BaseDocTemplate.build().

    Usage:
        footer = get_footer_callback()
        doc.build(story, onFirstPage=footer, onLaterPages=footer)
    """
    return add_grantpro_footer
