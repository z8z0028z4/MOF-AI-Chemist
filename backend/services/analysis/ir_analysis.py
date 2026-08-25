"""
IR Analysis Service

Handles IR data analysis from CSV/TXT files, extracting spectral features
and generating Plotly visualization data.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class IRAnalyzer:
    """IR data analyzer for CSV/TXT files with spectral feature extraction and plotting."""

    def __init__(self):
        self.logger = logger
        # Common functional group regions in IR spectroscopy
        self.functional_regions = {
            'OH_stretch': (3200, 3600),
            'CH_stretch': (2800, 3000),
            'C=O_stretch': (1650, 1750),
            'C=C_stretch': (1600, 1700),
            'CH_bend': (1350, 1500),
            'C-O_stretch': (1000, 1300)
        }

    def parse_data_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse IR data file and extract key features.

        Args:
            file_path: Path to the CSV/TXT file

        Returns:
            Dict containing extracted IR features

        Raises:
            ValueError: If file cannot be read or data is invalid
            FileNotFoundError: If file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"IR file not found: {file_path}")

        try:
            # Read data file
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path)
            else:
                # Assume space or tab separated for TXT
                df = pd.read_csv(file_path, sep=r'\s+')

            self.logger.info(f"Successfully loaded IR file: {file_path}")

            # Extract features
            features = self._extract_ir_features(df)

            result = {
                **features,
                'source_file': str(file_path.name),
                'analysis_type': 'IR',
                'raw_data_available': len(df) > 0
            }

            self.logger.info(f"IR analysis completed for file: {file_path.name}")
            return result

        except Exception as e:
            self.logger.error(f"Error parsing IR file {file_path}: {str(e)}")
            raise ValueError(f"Failed to parse IR file: {str(e)}")

    def _extract_ir_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract key features from IR data."""
        # Assume first two columns are wavenumber and intensity/transmittance
        if len(df.columns) < 2:
            raise ValueError("IR data must have at least 2 columns (wavenumber, intensity)")

        wavenumber_col = df.columns[0]
        intensity_col = df.columns[1]

        # Convert to numeric, handling any non-numeric values
        wavenumber = pd.to_numeric(df[wavenumber_col], errors='coerce').dropna()
        intensity = pd.to_numeric(df[intensity_col], errors='coerce').dropna()

        if len(wavenumber) == 0 or len(intensity) == 0:
            raise ValueError("No valid numeric data found in IR file")

        # Find peaks in functional group regions
        functional_group_peaks = self._analyze_functional_groups(wavenumber.values, intensity.values)

        # Find overall peaks
        peaks = self._find_peaks(wavenumber.values, intensity.values)

        # Calculate basic statistics
        max_intensity = float(intensity.max())
        min_intensity = float(intensity.min())

        features = {
            'peak_count': len(peaks),
            'functional_groups': functional_group_peaks,
            'max_intensity': max_intensity,
            'min_intensity': min_intensity,
            'peaks': peaks[:10],  # Limit to top 10 peaks
            'data_points': len(wavenumber),
            'wavenumber_range': [float(wavenumber.min()), float(wavenumber.max())]
        }

        return features

    def _analyze_functional_groups(self, wavenumber: np.ndarray, intensity: np.ndarray) -> Dict[str, Any]:
        """Analyze functional group regions for characteristic peaks."""
        functional_groups = {}

        for group_name, (min_wave, max_wave) in self.functional_regions.items():
            # Find data points in this region
            mask = (wavenumber >= min_wave) & (wavenumber <= max_wave)
            if not np.any(mask):
                continue

            region_wavenumber = wavenumber[mask]
            region_intensity = intensity[mask]

            if len(region_wavenumber) == 0:
                continue

            # Find peaks in this region
            region_peaks = []
            for i in range(1, len(region_intensity) - 1):
                if (region_intensity[i] > region_intensity[i-1] and
                    region_intensity[i] > region_intensity[i+1]):
                    region_peaks.append((float(region_wavenumber[i]), float(region_intensity[i])))

            if region_peaks:
                # Sort by intensity and take strongest peak
                region_peaks.sort(key=lambda x: x[1], reverse=True)
                strongest_peak = region_peaks[0]
                functional_groups[group_name] = {
                    'peak_wavenumber': strongest_peak[0],
                    'peak_intensity': strongest_peak[1],
                    'peak_count': len(region_peaks)
                }

        return functional_groups

    def _find_peaks(self, wavenumber: np.ndarray, intensity: np.ndarray) -> List[Tuple[float, float]]:
        """Simple peak detection algorithm for IR spectra."""
        peaks = []

        # Find local maxima
        for i in range(1, len(intensity) - 1):
            if (intensity[i] > intensity[i-1] and
                intensity[i] > intensity[i+1] and
                intensity[i] > np.mean(intensity) * 0.1):  # Above noise threshold
                peaks.append((float(wavenumber[i]), float(intensity[i])))

        # Sort by intensity (descending)
        peaks.sort(key=lambda x: x[1], reverse=True)

        return peaks

    def generate_plot_data(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Generate Plotly plot data for IR analysis.

        Args:
            file_path: Path to the data file

        Returns:
            Dict containing Plotly figure data or None if no data
        """
        try:
            # Read data file
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path)
            else:
                df = pd.read_csv(file_path, sep=r'\s+')

            if len(df.columns) < 2:
                return None

            wavenumber_col = df.columns[0]
            intensity_col = df.columns[1]

            # Convert to numeric
            wavenumber = pd.to_numeric(df[wavenumber_col], errors='coerce').dropna()
            intensity = pd.to_numeric(df[intensity_col], errors='coerce').dropna()

            if len(wavenumber) == 0 or len(intensity) == 0:
                return None

            # Create Plotly figure data
            plot_data = {
                'data': [{
                    'x': wavenumber.tolist(),
                    'y': intensity.tolist(),
                    'type': 'scatter',
                    'mode': 'lines',
                    'name': 'IR Spectrum',
                    'line': {'color': '#ff7f0e', 'width': 1}
                }],
                'layout': {
                    'title': f'IR Spectrum - {file_path.name}',
                    'xaxis': {'title': 'Wavenumber (cm⁻¹)', 'autorange': 'reversed'},
                    'yaxis': {'title': 'Intensity (a.u.)'},
                    'showlegend': True,
                    'width': 800,
                    'height': 500
                }
            }

            return plot_data

        except Exception as e:
            self.logger.error(f"Error generating IR plot data: {str(e)}")
            return None


def create_ir_analyzer() -> IRAnalyzer:
    """Factory function to create IR analyzer instance."""
    return IRAnalyzer()
