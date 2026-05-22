"""Test suite for data_extractor.py module.

Tests cover:
- format_metadata_as_string function with various metadata formats
- extract_metadata_from_html function
- fix_not_closed_metatags function
- export_to_tsv function
"""

from unittest.mock import patch

from bs4 import BeautifulSoup

from data_extractor import (
    export_site_to_tsv,
    export_to_tsv,
    extract_metadata_from_html,
    extract_site_metadata,
    fix_not_closed_metatags,
    format_metadata_as_string,
)


class TestFormatMetadataAsString:
    """Test suite for format_metadata_as_string function."""

    def test_empty_metadata_list(self):
        """Test formatting an empty metadata list."""
        result = format_metadata_as_string([])
        assert result == "[  ]"

    def test_single_metadata_item(self):
        """Test formatting a single metadata item."""
        metadata = ['<meta name="description" content="Test description"/>']
        result = format_metadata_as_string(metadata)
        assert result == "[ '''<meta name=\"description\" content=\"Test description\"/>''' ]"

    def test_multiple_metadata_items(self):
        """Test formatting multiple metadata items."""
        metadata = [
            '<meta name="description" content="Test description"/>',
            '<meta name="keywords" content="test, keywords"/>',
        ]
        result = format_metadata_as_string(metadata)
        expected = (
            "[ '''<meta name=\"description\" content=\"Test description\"/>''', "
            "'''<meta name=\"keywords\" content=\"test, keywords\"/>''' ]"
        )
        assert result == expected

    def test_metadata_with_special_characters(self):
        """Test formatting metadata with special characters."""
        metadata = ['<meta name="description" content="My \'special\' example"/>']
        result = format_metadata_as_string(metadata)
        assert "'''" in result  # Triple quotes should wrap the tag
        assert '<meta name="description" content="My \'special\' example"/>' in result

    def test_metadata_with_quotes(self):
        """Test formatting metadata containing quotes."""
        metadata = [
            '<meta name="description" content="Quote: \\"Hello\\""/>',
            '<meta name="author" content="\'John Doe\'"/>',
        ]
        result = format_metadata_as_string(metadata)
        assert "[ " in result
        assert " ]" in result
        assert result.count("'''") == 4  # 2 tags, each with opening and closing triple quotes

    def test_metadata_preserves_order(self):
        """Test that metadata order is preserved."""
        metadata = [
            '<meta name="first"/>',
            '<meta name="second"/>',
            '<meta name="third"/>',
        ]
        result = format_metadata_as_string(metadata)
        # Check that tags appear in order
        first_pos = result.find("first")
        second_pos = result.find("second")
        third_pos = result.find("third")
        assert first_pos < second_pos < third_pos

    def test_metadata_with_newlines(self):
        """Test formatting metadata containing newlines."""
        metadata = ['<meta name="description" content="Line1\nLine2"/>']
        result = format_metadata_as_string(metadata)
        # The function should preserve content as-is, escaping happens during TSV export
        assert "'''" in result
        assert "Line1\nLine2" in result

    def test_metadata_with_tabs(self):
        """Test formatting metadata containing tabs."""
        metadata = ['<meta name="description" content="Col1\tCol2"/>']
        result = format_metadata_as_string(metadata)
        assert "'''" in result
        assert "Col1\tCol2" in result

    def test_link_tags_in_metadata(self):
        """Test formatting link tags as metadata."""
        metadata = [
            '<link rel="author" href="https://example.com/author"/>',
            '<link rel="shortcut icon" href="https://example.com/favicon.ico"/>',
        ]
        result = format_metadata_as_string(metadata)
        assert result.count("'''") == 4
        assert "author" in result
        assert "favicon" in result

    def test_formatted_output_is_valid_list_syntax(self):
        """Test that output can be evaluated as Python list syntax."""
        metadata = [
            '<meta name="description" content="Test"/>',
            '<meta name="keywords" content="test, keywords"/>',
        ]
        result = format_metadata_as_string(metadata)
        # Remove outer brackets and spaces to get list-like content
        assert result.startswith("[ ")
        assert result.endswith(" ]")
        # Count separating commas (should be 1 between 2 items, but the content has a comma too)
        assert result.count("'''") == 4  # 2 tags, each wrapped in triple quotes


class TestFixNotClosedMetatags:
    """Test suite for fix_not_closed_metatags function."""

    def test_fix_unclosed_meta_tag(self):
        """Test fixing an unclosed meta tag."""
        html = '<meta name="description" content="test">'
        soup = BeautifulSoup(html, "html.parser")
        tag = soup.find("meta")
        result = fix_not_closed_metatags(tag)
        assert result.endswith("/>")

    def test_fix_already_closed_meta_tag(self):
        """Test fixing a meta tag that's already self-closed."""
        html = '<meta name="description" content="test"/>'
        soup = BeautifulSoup(html, "html.parser")
        tag = soup.find("meta")
        result = fix_not_closed_metatags(tag)
        assert result.endswith(">")

    def test_fix_link_tag(self):
        """Test fixing an unclosed link tag."""
        html = '<link rel="author" href="https://example.com">'
        soup = BeautifulSoup(html, "html.parser")
        tag = soup.find("link")
        result = fix_not_closed_metatags(tag)
        assert result.endswith("/>")


class TestExtractMetadataFromHtml:
    """Test suite for extract_metadata_from_html function."""

    def test_extract_title_and_metadata(self):
        """Test extracting title and metadata from HTML."""
        html = """
        <html>
        <head>
            <title>Test Page</title>
            <meta name="description" content="Test description"/>
            <meta name="keywords" content="test, keywords"/>
        </head>
        </html>
        """
        title, metadata = extract_metadata_from_html(html.encode())
        assert title == "Test Page"
        assert len(metadata) == 2
        assert any("description" in tag for tag in metadata)
        assert any("keywords" in tag for tag in metadata)

    def test_extract_link_tags(self):
        """Test extracting link tags from HTML."""
        html = """
        <html>
        <head>
            <link rel="author" href="https://example.com/author"/>
            <link rel="shortcut icon" href="https://example.com/favicon.ico"/>
        </head>
        </html>
        """
        title, metadata = extract_metadata_from_html(html.encode())
        assert title == ""
        assert len(metadata) == 2
        assert any("author" in tag for tag in metadata)
        assert any("favicon" in tag for tag in metadata)

    def test_extract_from_html_without_head(self):
        """Test extracting metadata from HTML without head section."""
        html = """
        <html>
        <body>
            <p>No head section</p>
        </body>
        </html>
        """
        title, metadata = extract_metadata_from_html(html.encode())
        assert title == ""
        assert metadata == []

    def test_extract_with_malformed_html(self):
        """Test that function handles malformed HTML gracefully."""
        html = """
        <html>
        <head>
            <title>Test</title>
            <meta name="description" content="unclosed
        </head>
        </html>
        """
        # Should not raise an exception
        title, metadata = extract_metadata_from_html(html.encode())
        assert title == "Test"

    def test_extract_ignores_invalid_meta_names(self):
        """Test that only valid meta names are extracted."""
        html = """
        <html>
        <head>
            <meta name="description" content="Valid"/>
            <meta name="invalid-name" content="Should not appear"/>
            <meta property="og:title" content="Also should not appear"/>
        </head>
        </html>
        """
        title, metadata = extract_metadata_from_html(html.encode())
        assert len(metadata) == 1
        assert "description" in metadata[0]

    def test_extract_ignores_invalid_link_rels(self):
        """Test that only valid link rel values are extracted."""
        html = """
        <html>
        <head>
            <link rel="author" href="https://example.com/author"/>
            <link rel="stylesheet" href="style.css"/>
        </head>
        </html>
        """
        title, metadata = extract_metadata_from_html(html.encode())
        # Should only extract author, not stylesheet
        assert len(metadata) == 1
        assert "author" in metadata[0]


class TestExportSiteToTsv:
    """Test suite for export_site_to_tsv function (incremental export)."""

    def test_export_site_to_tsv_creates_file(self, tmp_path):
        """Test that export_site_to_tsv creates a TSV file."""
        output_file = tmp_path / "test_output.tsv"
        export_site_to_tsv("example.com", "Example Site", ['<meta name="description" content="Example"/>'], str(output_file))
        assert output_file.exists()

    def test_export_site_to_tsv_no_header(self, tmp_path):
        """Test that export_site_to_tsv doesn't write header."""
        output_file = tmp_path / "test_output.tsv"
        export_site_to_tsv("example.com", "Example Site", ['<meta name="description" content="Example"/>'], str(output_file))

        with open(output_file, encoding="utf-8") as f:
            lines = f.readlines()

        # Should have only data row, no header
        assert len(lines) == 1
        assert "Site\tTitle\tMetadata" not in lines[0]
        assert "example.com" in lines[0]

    def test_export_site_to_tsv_append_mode(self, tmp_path):
        """Test that export_site_to_tsv appends to existing file."""
        output_file = tmp_path / "test_output.tsv"

        # First export
        export_site_to_tsv("example1.com", "Site 1", [], str(output_file))

        # Second export (should append)
        export_site_to_tsv("example2.com", "Site 2", [], str(output_file))

        with open(output_file, encoding="utf-8") as f:
            lines = f.readlines()

        # Should have 2 data rows
        assert len(lines) == 2
        assert "example1.com" in lines[0]
        assert "example2.com" in lines[1]

    def test_export_site_to_tsv_escapes_special_chars(self, tmp_path):
        """Test that export_site_to_tsv escapes special characters."""
        output_file = tmp_path / "test_output.tsv"
        export_site_to_tsv(
            "example.com",
            "Title with\ttab and\nnewline",
            ['<meta name="description" content="Also\thas\tspecial\nchars"/>'],
            str(output_file),
        )

        with open(output_file, encoding="utf-8") as f:
            content = f.read()

        # Tabs and newlines should be escaped
        assert "\\t" in content
        assert "\\n" in content


class TestExportToTsv:
    """Test suite for export_to_tsv function."""

    def test_export_to_tsv_creates_file(self, tmp_path):
        """Test that export_to_tsv creates a TSV file."""
        output_file = tmp_path / "test_output.tsv"
        results = {
            "example.com": ("Example Site", ['<meta name="description" content="Example"/>']),
        }
        export_to_tsv(results, str(output_file))
        assert output_file.exists()

    def test_export_to_tsv_header(self, tmp_path):
        """Test that TSV file has correct header."""
        output_file = tmp_path / "test_output.tsv"
        results = {
            "example.com": ("Example Site", ['<meta name="description" content="Example"/>']),
        }
        export_to_tsv(results, str(output_file))

        with open(output_file, encoding="utf-8") as f:
            lines = f.readlines()
        assert lines[0].strip() == "Site\tTitle\tMetadata"

    def test_export_to_tsv_data_rows(self, tmp_path):
        """Test that TSV file contains correct data rows."""
        output_file = tmp_path / "test_output.tsv"
        results = {
            "example.com": ("Example Site", ['<meta name="description" content="Example"/>']),
            "test.com": ("Test Site", []),
        }
        export_to_tsv(results, str(output_file))

        with open(output_file, encoding="utf-8") as f:
            lines = f.readlines()

        # Should have header + 2 data rows
        assert len(lines) == 3
        assert "example.com" in lines[1]
        assert "test.com" in lines[2]

    def test_export_to_tsv_escapes_special_characters(self, tmp_path):
        """Test that special characters are properly escaped."""
        output_file = tmp_path / "test_output.tsv"
        results = {
            "example.com": (
                "Title with\ttab and\nnewline",
                ['<meta name="description" content="Also\thas\tspecial\nchars"/>'],
            ),
        }
        export_to_tsv(results, str(output_file))

        with open(output_file, encoding="utf-8") as f:
            content = f.read()

        # Tabs and newlines should be escaped
        assert "\\t" in content
        assert "\\n" in content

    def test_export_to_tsv_sorted_sites(self, tmp_path):
        """Test that sites are exported in sorted order."""
        output_file = tmp_path / "test_output.tsv"
        results = {
            "zebra.com": ("Zebra", []),
            "apple.com": ("Apple", []),
            "middle.com": ("Middle", []),
        }
        export_to_tsv(results, str(output_file))

        with open(output_file, encoding="utf-8") as f:
            lines = f.readlines()

        assert "apple.com" in lines[1]
        assert "middle.com" in lines[2]
        assert "zebra.com" in lines[3]

    def test_export_to_tsv_with_empty_results(self, tmp_path):
        """Test exporting empty results dictionary."""
        output_file = tmp_path / "test_output.tsv"
        results = {}
        export_to_tsv(results, str(output_file))

        with open(output_file, encoding="utf-8") as f:
            lines = f.readlines()

        # Should have only header
        assert len(lines) == 1
        assert "Site\tTitle\tMetadata" in lines[0]

    def test_export_to_tsv_append_false_creates_header(self, tmp_path):
        """Test that append=False creates file with header."""
        output_file = tmp_path / "test_output.tsv"
        results = {
            "example.com": ("Example Site", ['<meta name="description" content="Example"/>']),
        }
        export_to_tsv(results, str(output_file), append=False)

        with open(output_file, encoding="utf-8") as f:
            lines = f.readlines()

        assert lines[0].strip() == "Site\tTitle\tMetadata"

    def test_export_to_tsv_append_true_no_header(self, tmp_path):
        """Test that append=True doesn't write header."""
        output_file = tmp_path / "test_output.tsv"

        # Create initial file with header
        results1 = {
            "site1.com": ("Site 1", []),
        }
        export_to_tsv(results1, str(output_file), append=False)

        # Append more data
        results2 = {
            "site2.com": ("Site 2", []),
        }
        export_to_tsv(results2, str(output_file), append=True)

        with open(output_file, encoding="utf-8") as f:
            lines = f.readlines()

        # Should have header + 2 data rows (no duplicate header)
        assert len(lines) == 3
        assert lines[0].strip() == "Site\tTitle\tMetadata"
        assert "site1.com" in lines[1]
        assert "site2.com" in lines[2]


class TestExtractSiteMetadata:
    """Test suite for extract_site_metadata function."""

    @patch("data_extractor.get_archived_page_content")
    def test_extract_site_metadata_success(self, mock_get_content):
        """Test successful site metadata extraction."""
        html_content = """
        <html>
        <head>
            <title>Test Site</title>
            <meta name="description" content="Test description"/>
        </head>
        </html>
        """
        mock_get_content.return_value = html_content.encode()

        title, metadata = extract_site_metadata("example.com", "20200101120000")

        assert title == "Test Site"
        assert len(metadata) == 1
        assert "description" in metadata[0]

    @patch("data_extractor.get_archived_page_content")
    def test_extract_site_metadata_with_custom_timeout(self, mock_get_content):
        """Test site metadata extraction with custom timeout."""
        mock_get_content.return_value = b"<html><head><title>Test</title></head></html>"

        extract_site_metadata("example.com", "20200101120000", timeout=30)

        # Check that timeout was passed correctly
        call_args = mock_get_content.call_args
        assert call_args[0][1] == 30  # timeout is the second positional argument

    @patch("data_extractor.get_archived_page_content")
    def test_extract_site_metadata_fetch_failure(self, mock_get_content):
        """Test handling of fetch failures."""
        mock_get_content.return_value = None

        title, metadata = extract_site_metadata("example.com", "20200101120000")

        assert title == ""
        assert metadata == []
