"""
Map creation module for visualizing WILDCAT outputs
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

try:
    import geopandas as gpd
    import rasterio
    from rasterio.plot import show
    SPATIAL_LIBS_AVAILABLE = True
except ImportError:
    SPATIAL_LIBS_AVAILABLE = False

logger = logging.getLogger(__name__)


class MapCreator:
    """
    Create visualization maps from WILDCAT outputs
    """
    
    def __init__(self, output_folder: str):
        """
        Initialize map creator
        
        Args:
            output_folder: Folder for map outputs
        """
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)
    
    def create_probability_map(self, fire_name: str, basins_path: str,
                               probability_column: str, output_path: str = None) -> Optional[str]:
        """
        Create a probability map for a single scenario
        
        Args:
            fire_name: Name of the fire
            basins_path: Path to basins shapefile
            probability_column: Probability column to visualize
            output_path: Output path for map
            
        Returns:
            Path to created map or None
        """
        try:
            # Read basins
            basins = gpd.read_file(basins_path)
            
            # Create figure
            fig, ax = plt.subplots(figsize=(10, 8))
            
            # Plot basins colored by probability
            basins.plot(
                column=probability_column,
                ax=ax,
                legend=True,
                cmap='RdYlGn_r',
                vmin=0,
                vmax=1,
                legend_kwds={
                    'label': 'Debris Flow Probability',
                    'orientation': 'horizontal',
                    'pad': 0.05
                }
            )
            
            # Title
            rainfall = probability_column.replace('P_', '').replace('mmh', ' mm/hr')
            ax.set_title(f'{fire_name} - {rainfall} Rainfall Scenario', 
                        fontsize=14, fontweight='bold')
            
            # Remove axes
            ax.set_axis_off()
            
            # Add north arrow
            self._add_north_arrow(ax)
            
            # Add scale bar
            self._add_scale_bar(ax, basins)
            
            # Save
            if output_path is None:
                output_path = self.output_folder / f"{fire_name}_{probability_column}_map.png"
            
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"✅ Created map: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"❌ Error creating map: {e}")
            return None
    
    def create_composite_map(self, fire_name: str, basins_path: str,
                             scenarios: List[str] = None) -> Optional[str]:
        """
        Create a composite map showing multiple scenarios
        
        Args:
            fire_name: Name of the fire
            basins_path: Path to basins shapefile
            scenarios: List of probability columns
            
        Returns:
            Path to composite map or None
        """
        if scenarios is None:
            scenarios = ['P_16mmh', 'P_20mmh', 'P_24mmh', 'P_40mmh']
        
        try:
            # Read basins
            basins = gpd.read_file(basins_path)
            
            # Filter to existing columns
            existing_scenarios = [s for s in scenarios if s in basins.columns]
            if not existing_scenarios:
                logger.warning("No probability columns found")
                return None
            
            # Create figure
            n_scenarios = len(existing_scenarios)
            fig, axes = plt.subplots(1, n_scenarios, figsize=(6*n_scenarios, 8))
            
            if n_scenarios == 1:
                axes = [axes]
            
            # Plot each scenario
            for idx, (ax, scenario) in enumerate(zip(axes, existing_scenarios)):
                basins.plot(
                    column=scenario,
                    ax=ax,
                    cmap='RdYlGn_r',
                    vmin=0,
                    vmax=1,
                    legend=idx == 0,  # Only show legend on first
                    legend_kwds={
                        'label': 'Probability',
                        'orientation': 'vertical'
                    }
                )
                
                # Subplot title
                rainfall = scenario.replace('P_', '').replace('mmh', ' mm/hr')
                ax.set_title(f'{rainfall}', fontsize=12)
                ax.set_axis_off()
            
            # Main title
            fig.suptitle(f'{fire_name} - Debris Flow Probability Scenarios',
                         fontsize=16, fontweight='bold', y=0.98)
            
            # Save
            output_path = self.output_folder / f"{fire_name}_composite_map.png"
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"✅ Created composite map: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"❌ Error creating composite map: {e}")
            return None
    
    def _add_scale_bar(self, ax, gdf: gpd.GeoDataFrame):
        """Add a simple scale bar to the map"""
        try:
            # Get bounds
            bounds = gdf.total_bounds
            width_m = bounds[2] - bounds[0]
            
            # Determine scale bar length
            if width_m > 10000:
                scale_length = 5000  # 5 km
                scale_label = "5 km"
            elif width_m > 5000:
                scale_length = 2000  # 2 km
                scale_label = "2 km"
            else:
                scale_length = 1000  # 1 km
                scale_label = "1 km"
            
            # Calculate position
            x_pos = bounds[0] + (bounds[2] - bounds[0]) * 0.05
            y_pos = bounds[1] + (bounds[3] - bounds[1]) * 0.05
            
            # Draw scale bar
            ax.plot([x_pos, x_pos + scale_length], [y_pos, y_pos], 'k-', linewidth=3)
            ax.text(x_pos + scale_length/2, y_pos + (bounds[3]-bounds[1])*0.01, 
                    scale_label, ha='center', fontsize=10)
            
        except Exception:
            pass  # Scale bar is optional
    
    def _add_north_arrow(self, ax):
        """Add a north arrow to the map"""
        try:
            x, y = 0.95, 0.95  # Position in axes coordinates
            ax.annotate('N', xy=(x, y), xytext=(x, y-0.05),
                       xycoords='axes fraction',
                       ha='center', va='center',
                       fontsize=16, fontweight='bold',
                       arrowprops=dict(arrowstyle='->', lw=2))
        except Exception:
            pass  # North arrow is optional