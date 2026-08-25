"""
TGA Analysis Service

Handles TGA data analysis from Excel files, specifically extracting:
- Unit adsorption (column J)
- Desorption energy (column K)
- Sample information

This service focuses on the example_TGA_data.xlsx format and does not
include PDF parsing functionality.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class TGAAnalyzer:
    """TGA data analyzer for Excel files with specific column extraction."""

    def __init__(self):
        self.logger = logger

    def parse_excel(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse TGA Excel file and extract key metrics from columns J and K.

        Args:
            file_path: Path to the Excel file

        Returns:
            Dict containing extracted TGA metrics

        Raises:
            ValueError: If file cannot be read or required columns are missing
            FileNotFoundError: If file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"TGA file not found: {file_path}")

        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            self.logger.info(f"Successfully loaded TGA Excel file: {file_path}")

            # Extract sample information (assuming first row or specific pattern)
            sample_name = self._extract_sample_name(df)

            # Extract unit adsorption from column J
            unit_adsorption = self._extract_column_data(df, 'J', 'unit_adsorption')

            # Extract desorption energy from column K
            desorption_energy = self._extract_column_data(df, 'K', 'desorption_energy')

            result = {
                'sample_name': sample_name,
                'unit_adsorption': unit_adsorption,
                'desorption_energy': desorption_energy,
                'raw_data_available': len(df) > 0
            }

            self.logger.info(f"TGA analysis completed for sample: {sample_name}")
            return result

        except Exception as e:
            self.logger.error(f"Error parsing TGA Excel file {file_path}: {str(e)}")
            raise ValueError(f"Failed to parse TGA Excel file: {str(e)}")

    def _extract_sample_name(self, df: pd.DataFrame) -> str:
        """Extract sample name from the DataFrame."""
        # Try to find sample name in first few rows or specific column
        for col in df.columns:
            if 'sample' in str(col).lower() or 'name' in str(col).lower():
                first_value = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
                if first_value:
                    return str(first_value)

        # Fallback to generic name
        return "Unknown Sample"

    def _extract_column_data(self, df: pd.DataFrame, column_letter: str, metric_name: str) -> float:
        """
        Extract numeric data from specified column letter.

        Args:
            df: DataFrame to extract from
            column_letter: Excel column letter (e.g., 'J', 'K')
            metric_name: Name of the metric for error messages

        Returns:
            Numeric value from the column

        Raises:
            ValueError: If column doesn't exist or contains no valid numeric data
        """
        try:
            # Convert column letter to index
            col_index = ord(column_letter.upper()) - ord('A')

            if col_index >= len(df.columns):
                raise ValueError(f"Column {column_letter} not found in TGA data")

            column_data = df.iloc[:, col_index]

            # Find first valid numeric value
            numeric_values = pd.to_numeric(column_data, errors='coerce').dropna()

            if numeric_values.empty:
                raise ValueError(f"No valid numeric data found in column {column_letter} for {metric_name}")

            # Return the first valid numeric value
            value = float(numeric_values.iloc[0])
            self.logger.debug(f"Extracted {metric_name}: {value} from column {column_letter}")
            return value

        except Exception as e:
            self.logger.error(f"Error extracting {metric_name} from column {column_letter}: {str(e)}")
            raise ValueError(f"Failed to extract {metric_name} from column {column_letter}: {str(e)}")

    def generate_plot_data(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Generate plot data for TGA analysis.

        Note: TGA typically doesn't generate standard plots like XRD/IR,
        so this returns None to indicate no plot is available.

        Args:
            file_path: Path to the Excel file

        Returns:
            None (TGA doesn't generate standard plots)
        """
        # TGA data is typically tabular and doesn't generate standard plots
        # Return None to indicate no plot is available
        return None


def create_tga_analyzer() -> TGAAnalyzer:
    """Factory function to create TGA analyzer instance."""
    return TGAAnalyzer()
