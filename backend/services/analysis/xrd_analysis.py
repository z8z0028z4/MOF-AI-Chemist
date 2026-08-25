"""
XRD Analysis Service

Handles XRD data analysis from CSV/TXT files, extracting peak information
and generating Plotly visualization data.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class XRDAnalyzer:
    """XRD data analyzer for CSV/TXT files with peak detection and plotting."""

    def __init__(self):
        self.logger = logger

    def parse_data_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse XRD data file and extract key features.

        Args:
            file_path: Path to the CSV/TXT file

        Returns:
            Dict containing extracted XRD features

        Raises:
            ValueError: If file cannot be read or data is invalid
            FileNotFoundError: If file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"XRD file not found: {file_path}")

        try:
            # Read data file
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path)
            else:
                # Assume space or tab separated for TXT
                df = pd.read_csv(file_path, sep=r'\s+')

            self.logger.info(f"Successfully loaded XRD file: {file_path}")

            # Extract features
            features = self._extract_xrd_features(df)

            result = {
                **features,
                'source_file': str(file_path.name),
                'analysis_type': 'XRD',
                'raw_data_available': len(df) > 0
            }

            self.logger.info(f"XRD analysis completed for file: {file_path.name}")
            return result

        except Exception as e:
            self.logger.error(f"Error parsing XRD file {file_path}: {str(e)}")
            raise ValueError(f"Failed to parse XRD file: {str(e)}")

    def _extract_xrd_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract key features from XRD data."""
        # Handle different column formats
        if len(df.columns) < 2:
            raise ValueError("XRD data must have at least 2 columns (2theta, intensity)")

        # Try to identify theta and intensity columns
        theta_col = None
        intensity_col = None

        # Look for common column patterns
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['theta', '2theta', 'pos', 'angle', '2θ']):
                theta_col = col
            elif any(keyword in col_lower for keyword in ['intensity', 'iobs', 'counts', 'cps', 'y']):
                intensity_col = col

        # Fallback to first two numeric columns
        if theta_col is None or intensity_col is None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) >= 2:
                theta_col = numeric_cols[0]
                intensity_col = numeric_cols[1]
            else:
                raise ValueError("Could not identify theta and intensity columns")

        self.logger.info(f"Using theta column: {theta_col}, intensity column: {intensity_col}")

        # Convert to numeric, handling any non-numeric values
        theta = pd.to_numeric(df[theta_col], errors='coerce').dropna()
        intensity = pd.to_numeric(df[intensity_col], errors='coerce').dropna()

        if len(theta) == 0 or len(intensity) == 0:
            raise ValueError("No valid numeric data found in XRD file")

        # Ensure both arrays have the same length
        min_len = min(len(theta), len(intensity))
        theta = theta.iloc[:min_len]
        intensity = intensity.iloc[:min_len]

        # Find peaks (simple peak detection)
        peaks = self._find_peaks(theta.values, intensity.values)

        # Calculate basic statistics
        max_intensity = float(intensity.max())
        max_intensity_theta = float(theta[intensity.idxmax()])

        # Count significant peaks (above 10% of max intensity)
        significant_peaks = [p for p in peaks if p[1] > max_intensity * 0.1]

        features = {
            'peak_count': len(peaks),
            'significant_peaks': len(significant_peaks),
            'max_intensity': max_intensity,
            'max_intensity_theta': max_intensity_theta,
            'peaks': peaks[:10],  # Limit to top 10 peaks
            'data_points': len(theta),
            'theta_range': [float(theta.min()), float(theta.max())],
            'source_file': getattr(df, 'name', 'unknown'),
            'analysis_type': 'XRD',
            'raw_data_available': True
        }

        return features

    def _find_peaks(self, theta: np.ndarray, intensity: np.ndarray) -> List[Tuple[float, float]]:
        """Improved peak detection algorithm."""
        peaks = []

        if len(intensity) < 3:
            return peaks

        # Calculate statistics for better threshold
        mean_intensity = np.mean(intensity)
        std_intensity = np.std(intensity)
        max_intensity = np.max(intensity)

        # Use multiple threshold strategies
        threshold_low = mean_intensity + 0.5 * std_intensity  # Statistical threshold
        threshold_high = max_intensity * 0.05  # 5% of max intensity
        threshold_very_low = max_intensity * 0.01  # 1% of max intensity (fallback)
        threshold = max(threshold_low, threshold_high, threshold_very_low)

        self.logger.info(f"Peak detection - Mean: {mean_intensity:.2f}, Std: {std_intensity:.2f}, Max: {max_intensity:.2f}, Threshold: {threshold:.2f}")

        # Find local maxima with improved conditions
        for i in range(2, len(intensity) - 2):  # Wider window for better detection
            # Check if current point is a local maximum
            is_local_max = (intensity[i] > intensity[i-1] and
                           intensity[i] > intensity[i+1] and
                           intensity[i] > intensity[i-2] and
                           intensity[i] > intensity[i+2])

            # Check if above threshold
            above_threshold = intensity[i] > threshold

            if is_local_max and above_threshold:
                peaks.append((float(theta[i]), float(intensity[i])))

        # If no peaks found with strict criteria, try more relaxed approach
        if len(peaks) == 0:
            self.logger.warning("No peaks found with strict criteria, trying relaxed approach")
            relaxed_threshold = max_intensity * 0.005  # 0.5% of max intensity

            for i in range(1, len(intensity) - 1):
                # Simple local maximum check
                is_local_max = (intensity[i] > intensity[i-1] and intensity[i] > intensity[i+1])
                above_threshold = intensity[i] > relaxed_threshold

                if is_local_max and above_threshold:
                    peaks.append((float(theta[i]), float(intensity[i])))

        # Sort by intensity (descending)
        peaks.sort(key=lambda x: x[1], reverse=True)

        self.logger.info(f"Found {len(peaks)} peaks")
        if peaks:
            self.logger.info(f"Top 3 peaks: {peaks[:3]}")

        return peaks

    def generate_plot_data(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Generate Plotly plot data for XRD analysis.

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

            # Use the same column identification logic as _extract_xrd_features
            theta_col = None
            intensity_col = None

            # Look for common column patterns
            for col in df.columns:
                col_lower = col.lower()
                if any(keyword in col_lower for keyword in ['theta', '2theta', 'pos', 'angle', '2θ']):
                    theta_col = col
                elif any(keyword in col_lower for keyword in ['intensity', 'iobs', 'counts', 'cps', 'y']):
                    intensity_col = col

            # Fallback to first two numeric columns
            if theta_col is None or intensity_col is None:
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) >= 2:
                    theta_col = numeric_cols[0]
                    intensity_col = numeric_cols[1]
                else:
                    return None

            # Convert to numeric
            theta = pd.to_numeric(df[theta_col], errors='coerce').dropna()
            intensity = pd.to_numeric(df[intensity_col], errors='coerce').dropna()

            if len(theta) == 0 or len(intensity) == 0:
                return None

            # Ensure both arrays have the same length
            min_len = min(len(theta), len(intensity))
            theta = theta.iloc[:min_len]
            intensity = intensity.iloc[:min_len]

            # Create Plotly figure data
            plot_data = {
                'data': [{
                    'x': theta.tolist(),
                    'y': intensity.tolist(),
                    'type': 'scatter',
                    'mode': 'lines',
                    'name': 'XRD Pattern',
                    'line': {'color': '#1f77b4', 'width': 1}
                }],
                'layout': {
                    'title': f'XRD Pattern - {file_path.name}',
                    'xaxis': {'title': '2θ (degrees)'},
                    'yaxis': {'title': 'Intensity (cps)'},
                    'showlegend': True,
                    'width': 800,
                    'height': 500
                }
            }

            return plot_data

        except Exception as e:
            self.logger.error(f"Error generating XRD plot data: {str(e)}")
            return None


def create_xrd_analyzer() -> XRDAnalyzer:
    """Factory function to create XRD analyzer instance."""
    return XRDAnalyzer()
