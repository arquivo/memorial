"""Test suite for extract_data_for_sites.py command-line tool.

Tests cover:
- Command-line argument parsing and validation
- Single site extraction mode (--site and --version) with title and metadata
- Bulk site extraction mode (from config) with title and metadata
- Error handling and edge cases
- TSV export functionality with site, title, and metadata columns
"""

import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_metadata():
    """Fixture providing sample extracted metadata."""
    return [
        '<meta name="description" content="Test description"/>',
        '<meta name="keywords" content="test, keywords"/>',
        '<link rel="author" href="https://example.com/author"/>',
    ]


@pytest.fixture
def mock_title():
    """Fixture providing sample page title."""
    return "Example Site Title"


@pytest.fixture
def mock_data():
    """Fixture providing sample extracted data (title and metadata)."""
    return (
        "Example Site Title",
        [
            '<meta name="description" content="Test description"/>',
            '<meta name="keywords" content="test, keywords"/>',
        ],
    )


@pytest.fixture
def mock_config():
    """Fixture providing sample site configuration."""
    return {
        "example.com": {"version": "20200101120000"},
        "test.com": {"version": "20200102120000"},
        "noversion.com": {"other_param": "value"},
    }


class TestSingleSiteExtraction:
    """Test single site extraction mode (--site and --version)."""

    def test_single_site_extraction_success(self, mock_data, capsys):
        """Test successful extraction for a single site."""
        with patch("extract_data_for_sites.extract_site_metadata", return_value=mock_data):
            with patch("extract_data_for_sites.export_to_tsv"):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "extract_data_for_sites.py",
                        "--site",
                        "example.com",
                        "--version",
                        "20200101120000",
                    ],
                ):
                    from extract_data_for_sites import main

                    result = main()

        assert result == 0
        captured = capsys.readouterr()
        assert "Site Title: Example Site Title" in captured.out
        assert "Found 2 metadata tag(s)" in captured.out

    def test_single_site_no_metadata(self, mock_title, capsys):
        """Test single site extraction when no metadata found."""
        with patch("extract_data_for_sites.extract_site_metadata", return_value=(mock_title, [])):
            with patch("extract_data_for_sites.export_to_tsv"):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "extract_data_for_sites.py",
                        "--site",
                        "example.com",
                        "--version",
                        "20200101120000",
                    ],
                ):
                    from extract_data_for_sites import main

                    result = main()

        assert result == 0
        captured = capsys.readouterr()
        assert "No metadata found" in captured.out

    def test_single_site_custom_timeout(self, mock_data):
        """Test single site extraction with custom timeout."""
        mock_extract = MagicMock(return_value=mock_data)
        with patch("extract_data_for_sites.extract_site_metadata", mock_extract):
            with patch("extract_data_for_sites.export_to_tsv"):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "extract_data_for_sites.py",
                        "--site",
                        "example.com",
                        "--version",
                        "20200101120000",
                        "--timeout",
                        "45",
                    ],
                ):
                    from extract_data_for_sites import main

                    main()

        call_args = mock_extract.call_args
        assert call_args[0][3] == 45

    def test_single_site_custom_wayback_server(self, mock_data):
        """Test single site extraction with custom wayback server."""
        mock_extract = MagicMock(return_value=mock_data)
        custom_server = "https://web.archive.org/web/"

        with patch("extract_data_for_sites.extract_site_metadata", mock_extract):
            with patch("extract_data_for_sites.export_to_tsv"):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "extract_data_for_sites.py",
                        "--site",
                        "example.com",
                        "--version",
                        "20200101120000",
                        "--wayback-server",
                        custom_server,
                    ],
                ):
                    from extract_data_for_sites import main

                    main()

        call_args = mock_extract.call_args
        assert call_args[0][2] == custom_server

    def test_single_site_missing_version_error(self, capsys):
        """Test error when --site provided without --version."""
        with patch.object(sys, "argv", ["extract_data_for_sites.py", "--site", "example.com"]):
            from extract_data_for_sites import main

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "--version is required when using --site" in captured.out

    def test_single_site_tsv_export(self, mock_data):
        """Test TSV export for single site."""
        mock_export = MagicMock()
        with patch("extract_data_for_sites.extract_site_metadata", return_value=mock_data):
            with patch("extract_data_for_sites.export_to_tsv", mock_export):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "extract_data_for_sites.py",
                        "--site",
                        "example.com",
                        "--version",
                        "20200101120000",
                        "--output",
                        "test.tsv",
                    ],
                ):
                    from extract_data_for_sites import main

                    main()

        mock_export.assert_called_once()
        call_args = mock_export.call_args
        results = call_args[0][0]
        assert "example.com" in results
        title, metadata = results["example.com"]
        assert title == mock_data[0]
        assert metadata == mock_data[1]
        assert call_args[0][1] == "test.tsv"


class TestBulkExtraction:
    """Test bulk site extraction mode (from config)."""

    def test_bulk_extraction_success(self, mock_config, capsys):
        """Test successful bulk extraction for multiple sites."""
        mock_extract = MagicMock()
        mock_extract.side_effect = [
            ("Example Title", ["<meta name='description'/>"]),
            ("Test Title", ["<meta name='keywords'/>"]),
        ]
        mock_export = MagicMock()

        with patch("extract_data_for_sites.extract_site_metadata", mock_extract):
            with patch("extract_data_for_sites.export_site_to_tsv", mock_export):
                with patch("builtins.open", create=True):
                    with patch("config.ARCHIVE_CONFIG", mock_config):
                        with patch.object(
                            sys,
                            "argv",
                            ["extract_data_for_sites.py"],
                        ):
                            from extract_data_for_sites import main

                            result = main()

        assert result == 0
        captured = capsys.readouterr()
        assert "Extracting data for 3 sites" in captured.out
        assert "✓ Extraction complete!" in captured.out

    def test_bulk_extraction_custom_timeout(self, mock_config):
        """Test bulk extraction with custom timeout."""
        mock_extract = MagicMock(return_value=("Example Title", ["<meta name='description'/>"]))

        with patch("extract_data_for_sites.extract_site_metadata", mock_extract):
            with patch("extract_data_for_sites.export_site_to_tsv"):
                with patch("builtins.open", create=True):
                    with patch("config.ARCHIVE_CONFIG", mock_config):
                        with patch.object(
                            sys,
                            "argv",
                            [
                                "extract_data_for_sites.py",
                                "--timeout",
                                "60",
                            ],
                        ):
                            from extract_data_for_sites import main

                            main()

        # Verify that extract_site_metadata was called with timeout=60
        calls = mock_extract.call_args_list
        for call in calls:
            if "version" in str(call):  # Skip non-site calls
                assert call[0][3] == 60

    def test_bulk_extraction_custom_wayback_server(self, mock_config):
        """Test bulk extraction with custom wayback server."""
        mock_extract = MagicMock(return_value=("Example Title", ["<meta name='description'/>"]))
        custom_server = "https://web.archive.org/web/"

        with patch("extract_data_for_sites.extract_site_metadata", mock_extract):
            with patch("extract_data_for_sites.export_site_to_tsv"):
                with patch("builtins.open", create=True):
                    with patch("config.ARCHIVE_CONFIG", mock_config):
                        with patch.object(
                            sys,
                            "argv",
                            [
                                "extract_data_for_sites.py",
                                "--wayback-server",
                                custom_server,
                            ],
                        ):
                            from extract_data_for_sites import main

                            main()

        # Verify that extract_site_metadata was called with custom wayback server
        calls = mock_extract.call_args_list
        for call in calls:
            if len(call[0]) > 2:
                assert call[0][2] == custom_server

    def test_bulk_extraction_custom_output(self, mock_config):
        """Test bulk extraction with custom output file."""
        mock_extract = MagicMock(return_value=("Example Title", ["<meta name='description'/>"]))
        mock_export = MagicMock()

        with patch("extract_data_for_sites.extract_site_metadata", mock_extract):
            with patch("extract_data_for_sites.export_site_to_tsv", mock_export):
                with patch("builtins.open", create=True):
                    with patch("config.ARCHIVE_CONFIG", mock_config):
                        with patch.object(
                            sys,
                            "argv",
                            [
                                "extract_data_for_sites.py",
                                "--output",
                                "custom.tsv",
                            ],
                        ):
                            from extract_data_for_sites import main

                            main()

        # Verify that export_site_to_tsv was called with custom output file
        calls = mock_export.call_args_list
        for call in calls:
            assert call[0][3] == "custom.tsv"


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_version_without_site_error(self, capsys):
        """Test error when --version provided without --site."""
        with patch.object(sys, "argv", ["extract_data_for_sites.py", "--version", "20200101120000"]):
            from extract_data_for_sites import main

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "--site is required when using --version" in captured.out


class TestArgumentValidation:
    """Test argument validation and defaults."""

    def test_default_output_file(self, mock_config):
        """Test that default output file is 'data.tsv'."""
        mock_extract = MagicMock(return_value=("Title", []))
        mock_export = MagicMock()

        with patch("extract_data_for_sites.extract_site_metadata", mock_extract):
            with patch("extract_data_for_sites.export_site_to_tsv", mock_export):
                with patch("builtins.open", create=True):
                    with patch("config.ARCHIVE_CONFIG", mock_config):
                        with patch.object(sys, "argv", ["extract_data_for_sites.py"]):
                            from extract_data_for_sites import main

                            main()

        # Verify that export_site_to_tsv was called with default output file
        calls = mock_export.call_args_list
        for call in calls:
            assert call[0][3] == "data.tsv"

    def test_default_timeout(self, mock_config):
        """Test that default timeout is 30 seconds."""
        mock_extract = MagicMock(return_value=("Title", []))

        with patch("extract_data_for_sites.extract_site_metadata", mock_extract):
            with patch("extract_data_for_sites.export_site_to_tsv"):
                with patch("builtins.open", create=True):
                    with patch("config.ARCHIVE_CONFIG", mock_config):
                        with patch.object(sys, "argv", ["extract_data_for_sites.py"]):
                            from extract_data_for_sites import main

                            main()

        # Verify that extract_site_metadata was called with default timeout
        calls = mock_extract.call_args_list
        for call in calls:
            if len(call[0]) > 3:
                assert call[0][3] == 30

    def test_default_wayback_server(self, mock_config):
        """Test that default wayback server is set correctly."""
        mock_extract = MagicMock(return_value=("Title", []))

        with patch("extract_data_for_sites.extract_site_metadata", mock_extract):
            with patch("extract_data_for_sites.export_site_to_tsv"):
                with patch("builtins.open", create=True):
                    with patch("config.ARCHIVE_CONFIG", mock_config):
                        with patch.object(sys, "argv", ["extract_data_for_sites.py"]):
                            from extract_data_for_sites import main

                            main()

        # Verify that extract_site_metadata was called with default wayback server
        calls = mock_extract.call_args_list
        for call in calls:
            if len(call[0]) > 2:
                assert call[0][2] == "https://arquivo.pt/noFrame/replay/"


class TestOutputFormatting:
    """Test output formatting."""

    def test_single_site_output_display(self, mock_data, capsys):
        """Test output formatting for single site."""
        with patch("extract_data_for_sites.extract_site_metadata", return_value=mock_data):
            with patch("extract_data_for_sites.export_to_tsv"):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "extract_data_for_sites.py",
                        "--site",
                        "example.com",
                        "--version",
                        "20200101120000",
                    ],
                ):
                    from extract_data_for_sites import main

                    main()

        captured = capsys.readouterr()
        assert "Extracting data for: example.com" in captured.out
        assert "Version: 20200101120000" in captured.out
        assert "Site Title: Example Site Title" in captured.out
        assert "1." in captured.out

    def test_bulk_extraction_progress_display(self, mock_config, capsys):
        """Test progress display for bulk extraction."""
        mock_extract = MagicMock(return_value=("Example Title", ["<meta name='description'/>"]))

        with patch("extract_data_for_sites.extract_site_metadata", mock_extract):
            with patch("extract_data_for_sites.export_site_to_tsv"):
                with patch("builtins.open", create=True):
                    with patch("config.ARCHIVE_CONFIG", mock_config):
                        with patch.object(sys, "argv", ["extract_data_for_sites.py"]):
                            from extract_data_for_sites import main

                            main()

        captured = capsys.readouterr()
        assert "Extracting data for" in captured.out
        assert "Timeout per site: 30 seconds" in captured.out
        assert "✓ Extraction complete!" in captured.out


class TestIntegration:
    """Integration tests."""

    def test_single_site_full_workflow(self, mock_data):
        """Test complete workflow for single site."""
        mock_extract = MagicMock(return_value=mock_data)
        mock_export = MagicMock()

        with patch("extract_data_for_sites.extract_site_metadata", mock_extract):
            with patch("extract_data_for_sites.export_to_tsv", mock_export):
                with patch.object(
                    sys,
                    "argv",
                    [
                        "extract_data_for_sites.py",
                        "--site",
                        "example.com",
                        "--version",
                        "20200101120000",
                        "--timeout",
                        "45",
                        "--wayback-server",
                        "https://web.archive.org/web/",
                        "--output",
                        "results.tsv",
                    ],
                ):
                    from extract_data_for_sites import main

                    result = main()

        assert result == 0
        assert mock_extract.called
        assert mock_export.called

    def test_bulk_extraction_full_workflow(self, mock_config, mock_data):
        """Test complete workflow for bulk extraction."""
        mock_extract = MagicMock(return_value=mock_data)
        mock_export = MagicMock()

        with patch("extract_data_for_sites.extract_site_metadata", mock_extract):
            with patch("extract_data_for_sites.export_site_to_tsv", mock_export):
                with patch("builtins.open", create=True):
                    with patch("config.ARCHIVE_CONFIG", mock_config):
                        with patch.object(
                            sys,
                            "argv",
                            [
                                "extract_data_for_sites.py",
                                "--timeout",
                                "60",
                                "--output",
                                "all_sites.tsv",
                            ],
                        ):
                            from extract_data_for_sites import main

                            result = main()

        assert result == 0
        assert mock_extract.called
        assert mock_export.called
