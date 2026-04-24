#!/usr/bin/env python3
"""
html_cleanup.py - Remove Calibre-only HTML metadata before markdown conversion.

This stays separate from convert.py so Calibre/Pandoc-specific cleanup can
evolve independently and be reused or tested on its own.
"""

import argparse
import re


def sanitize_html_content(html_content):
    """Strip Calibre styling metadata that turns into bracketed spans."""
    html_content = re.sub(r'\sclass="[^"]*\bcalibre[^\s"]*[^"]*"', '', html_content)
    html_content = re.sub(r"\sclass='[^']*\bcalibre[^\s']*[^']*'", '', html_content)
    html_content = re.sub(r'\sid="calibre_link-\d+"', '', html_content)
    html_content = re.sub(r"\sid='calibre_link-\d+'", '', html_content)
    return html_content


def sanitize_html_file(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    sanitized = sanitize_html_content(html_content)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(sanitized)


def main():
    parser = argparse.ArgumentParser(description="Strip Calibre HTML metadata before pandoc conversion")
    parser.add_argument("input_html", help="Path to source HTML")
    parser.add_argument("output_html", help="Path to sanitized HTML")
    args = parser.parse_args()

    sanitize_html_file(args.input_html, args.output_html)


if __name__ == "__main__":
    main()
