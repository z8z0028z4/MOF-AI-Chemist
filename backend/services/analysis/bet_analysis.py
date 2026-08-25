"""
BET Analysis Service

Handles BET data analysis from PDF files, specifically extracting key metrics
from the first page only. This service does NOT perform any regression analysis
or calculations - only extracts pre-calculated values from PDF reports.

Key metrics extracted:
- Surface area
- Pore size
- Pore volume
- Other standard BET parameters
"""

import PyPDF2
import re
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class BETAnalyzer:
    """BET data analyzer for PDF files with first page extraction only."""

    def __init__(self):
        self.logger = logger
        # Patterns to match common BET metrics in PDF text
        self.metric_patterns = {
            'surface_area': [
                r'surface\s+area[:\s]*(\d+\.?\d*)\s*m²/g',
                r'BET\s+surface\s+area[:\s]*(\d+\.?\d*)\s*m²/g',
                r'S\.A\.[:\s]*(\d+\.?\d*)\s*m²/g',
            ],
            'pore_size': [
                r'pore\s+size[:\s]*(\d+\.?\d*)\s*nm',
                r'pore\s+diameter[:\s]*(\d+\.?\d*)\s*nm',
                r'Dp[:\s]*(\d+\.?\d*)\s*nm',
            ],
            'pore_volume': [
                r'pore\s+volume[:\s]*(\d+\.?\d*)\s*cm³/g',
                r'total\s+pore\s+volume[:\s]*(\d+\.?\d*)\s*cm³/g',
                r'Vp[:\s]*(\d+\.?\d*)\s*cm³/g',
            ],
            'adsorption_volume': [
                r'adsorption\s+volume[:\s]*(\d+\.?\d*)\s*cm³/g',
                r'Va[:\s]*(\d+\.?\d*)\s*cm³/g',
            ]
        }

    def parse_first_page(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse BET PDF file and extract key metrics from first page only.

        Args:
            file_path: Path to the PDF file

        Returns:
            Dict containing extracted BET metrics

        Raises:
            ValueError: If file cannot be read or no metrics found
            FileNotFoundError: If file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"BET PDF file not found: {file_path}")

        try:
            # Extract text from first page only
            first_page_text = self._extract_first_page_text(file_path)

            # Extract metrics using pattern matching
            metrics = self._extract_metrics_from_text(first_page_text)

            # Add metadata
            result = {
                **metrics,
                'source_file': str(file_path.name),
                'analysis_type': 'BET_first_page',
                'raw_data_available': len(first_page_text) > 0
            }

            self.logger.info(f"BET analysis completed for file: {file_path.name}")
            return result

        except Exception as e:
            self.logger.error(f"Error parsing BET PDF file {file_path}: {str(e)}")
            raise ValueError(f"Failed to parse BET PDF file: {str(e)}")

    def _extract_first_page_text(self, file_path: Path) -> str:
        """Extract text content from the first page of PDF."""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                if len(pdf_reader.pages) == 0:
                    raise ValueError("PDF file has no pages")

                # Extract text from first page only
                first_page = pdf_reader.pages[0]
                text = first_page.extract_text()

                self.logger.debug(f"Extracted {len(text)} characters from first page")
                return text

        except Exception as e:
            self.logger.error(f"Error reading PDF file {file_path}: {str(e)}")
            raise ValueError(f"Failed to read PDF file: {str(e)}")

    def _extract_metrics_from_text(self, text: str) -> Dict[str, Any]:
        """Extract BET metrics from text using pattern matching."""
        metrics = {}

        for metric_name, patterns in self.metric_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        value = float(match.group(1))
                        metrics[metric_name] = value
                        self.logger.debug(f"Found {metric_name}: {value}")
                        break  # Use first match found
                    except (ValueError, IndexError):
                        continue

        # Ensure we have at least some basic metrics
        if not metrics:
            self.logger.warning("No BET metrics found in PDF text")
            # Return empty structure rather than failing
            return {
                'surface_area': None,
                'pore_size': None,
                'pore_volume': None
            }

        return metrics

    def generate_plot_data(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Generate plot data for BET analysis.

        Note: BET PDF parsing doesn't extract isotherm data for plotting,
        so this returns None to indicate no plot is available.

        Args:
            file_path: Path to the PDF file

        Returns:
            None (BET PDF parsing doesn't generate plots)
        """
        # BET PDF parsing only extracts tabular metrics, not isotherm data
        # Return None to indicate no plot is available
        return None


def create_bet_analyzer() -> BETAnalyzer:
    """Factory function to create BET analyzer instance."""
    return BETAnalyzer()
