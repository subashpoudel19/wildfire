 """
Batch visualization module for creating summary products
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import pandas as pd

try:
    import matplotlib.pyplot as plt
    import geopandas as gpd
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False

logger = logging.getLogger(__name__)


class BatchVisualizer:
    """
    Create batch visualizations and summary products
    """
    
    def __init__(self, output_folder: str):
        """
        Initialize batch visualizer
        
        Args:
            output_folder: Folder for visualization outputs
        """
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)
    
    def create_overview_map(self, fire_projects: List[Tuple[str, Dict]],
                            title: str = "Post-Fire Debris Flow Hazard Overview") -> Optional[str]:
        """
        Create an overview map showing all processed fires
        
        Args:
            fire_projects: List of (fire_name, project_info) tuples
            title: Map title
            
        Returns:
            Path to overview map
        """
        try:
            fig, ax = plt.subplots(figsize=(12, 10))
            
            # Collect all fire perimeters
            all_fires = []
            
            for fire_name, project_info in fire_projects:
                export_dir = Path(project_info['project_dir']) / "exports"
                basins_path = export_dir / "basins.shp"
                
                if basins_path.exists():
                    basins = gpd.read_file(basins_path)
                    # Get fire boundary
                    fire_boundary = basins.dissolve()
                    fire_boundary['fire_name'] = fire_name
                    fire_boundary['year'] = fire_name.split('_')[0]
                    all_fires.append(fire_boundary)
            
            if all_fires:
                # Combine all fires
                all_fires_gdf = gpd.GeoDataFrame(
                    pd.concat(all_fires, ignore_index=True),
                    crs=all_fires[0].crs
                )
                
                # Plot by year
                all_fires_gdf['year'] = all_fires_gdf['year'].astype(int)
                all_fires_gdf.plot(
                    column='year',
                    ax=ax,
                    legend=True,
                    cmap='viridis',
                    edgecolor='black',
                    linewidth=0.5,
                    legend_kwds={'label': 'Fire Year'}
                )
                
                # Add labels for large fires
                for idx, row in all_fires_gdf.iterrows():
                    if row.geometry.area > 1e7:  # Large fires
                        centroid = row.geometry.centroid
                        ax.annotate(
                            row['fire_name'].split('_')[1][:10],
                            xy=(centroid.x, centroid.y),
                            xytext=(3, 3),
                            textcoords='offset points',
                            fontsize=8,
                            bbox=dict(boxstyle='round,pad=0.3', fc='yellow', alpha=0.5)
                        )
                
                ax.set_title(title, fontsize=16, fontweight='bold')
                ax.set_axis_off()
                
                # Save
                output_path = self.output_folder / "fire_overview_map.png"
                plt.tight_layout()
                plt.savefig(output_path, dpi=300, bbox_inches='tight')
                plt.close()
                
                logger.info(f"✅ Created overview map: {output_path}")
                return str(output_path)
            
        except Exception as e:
            logger.error(f"❌ Error creating overview map: {e}")
            return None
    
    def create_fire_summary(self, fire_name: str, project_dir: str,
                            raster_dir: str = None) -> Optional[str]:
        """
        Create a summary sheet for a single fire
        
        Args:
            fire_name: Name of the fire
            project_dir: WILDCAT project directory
            raster_dir: Directory containing probability rasters
            
        Returns:
            Path to summary sheet
        """
        try:
            # Create figure with subplots
            fig = plt.figure(figsize=(11, 8.5))
            
            # Title
            fig.suptitle(f'{fire_name} - Debris Flow Hazard Summary',
                         fontsize=16, fontweight='bold')
            
            # Read basins data
            export_dir = Path(project_dir) / "exports"
            basins = gpd.read_file(export_dir / "basins.shp")
            
            # Calculate statistics
            stats_text = self._calculate_fire_statistics(basins)
            
            # Add statistics text
            ax_stats = fig.add_subplot(2, 2, 1)
            ax_stats.text(0.1, 0.9, stats_text, transform=ax_stats.transAxes,
                          fontsize=10, verticalalignment='top')
            ax_stats.set_title('Fire Statistics', fontweight='bold')
            ax_stats.axis('off')
            
            # Add hazard maps
            prob_scenarios = ['P_24mmh', 'P_40mmh']
            for idx, scenario in enumerate(prob_scenarios):
                ax = fig.add_subplot(2, 2, idx + 3)
                
                if scenario in basins.columns:
                    basins.plot(
                        column=scenario,
                        ax=ax,
                        cmap='RdYlGn_r',
                        vmin=0,
                        vmax=1,
                        legend=True,
                        legend_kwds={'label': 'Probability', 'orientation': 'horizontal'}
                    )
                    rainfall = scenario.replace('P_', '').replace('mmh', ' mm/hr')
                    ax.set_title(f'{rainfall} Scenario', fontweight='bold')
                else:
                    ax.text(0.5, 0.5, 'No Data', transform=ax.transAxes,
                            ha='center', va='center', fontsize=14)
                
                ax.set_axis_off()
            
            # Add metadata
            metadata_text = (
                f"Generated: {time.strftime('%Y-%m-%d')}\n"
                f"Model: WILDCAT Post-Fire Debris Flow\n"
                f"CRS: {basins.crs}"
            )
            fig.text(0.02, 0.02, metadata_text, fontsize=8, style='italic')
            
            # Save
            output_path = self.output_folder / f"{fire_name}_summary.pdf"
            plt.tight_layout()
            plt.savefig(output_path, format='pdf', bbox_inches='tight')
            plt.close()
            
            logger.info(f"✅ Created fire summary: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"❌ Error creating fire summary: {e}")
            return None
    
    def _calculate_fire_statistics(self, basins: gpd.GeoDataFrame) -> str:
        """Calculate and format fire statistics"""
        try:
            stats = []
            
            # Basic statistics
            stats.append(f"Number of basins: {len(basins)}")
            
            # Area statistics
            if 'Area_km2' in basins.columns:
                total_area = basins['Area_km2'].sum()
                stats.append(f"Total area: {total_area:.2f} km²")
                stats.append(f"Average basin area: {basins['Area_km2'].mean():.2f} km²")
            
            # Probability statistics for different scenarios
            prob_cols = [col for col in basins.columns if col.startswith('P_')]
            for prob_col in prob_cols:
                if prob_col in basins.columns:
                    high_risk = (basins[prob_col] > 0.5).sum()
                    rainfall = prob_col.replace('P_', '').replace('mmh', ' mm/hr')
                    stats.append(f"\n{rainfall} scenario:")
                    stats.append(f"  High risk basins: {high_risk} ({high_risk/len(basins)*100:.1f}%)")
                    stats.append(f"  Mean probability: {basins[prob_col].mean():.3f}")
                    stats.append(f"  Max probability: {basins[prob_col].max():.3f}")
            
            return '\n'.join(stats)
            
        except Exception as e:
            return f"Error calculating statistics: {e}"
    
    def create_summary_report(self, fire_projects: List[Tuple[str, Dict]],
                              assessment_results: Dict) -> Optional[str]:
        """
        Create a summary report for all processed fires
        
        Args:
            fire_projects: List of (fire_name, project_info) tuples
            assessment_results: Assessment results dictionary
            
        Returns:
            Path to summary report
        """
        try:
            # Collect statistics
            summary_data = []
            
            for fire_name, project_info in fire_projects:
                if fire_name not in assessment_results:
                    continue
                
                result = assessment_results[fire_name]
                if not result.get('success'):
                    continue
                
                # Get fire stats
                export_dir = Path(project_info['project_dir']) / "exports"
                basins_path = export_dir / "basins.shp"
                
                if basins_path.exists():
                    basins = gpd.read_file(basins_path)
                    
                    fire_stats = {
                        'Fire Name': fire_name,
                        'Year': fire_name.split('_')[0],
                        'Basins': len(basins),
                        'Area (km²)': basins.get('Area_km2', basins.geometry.area / 1e6).sum(),
                        'Processing Time (s)': result.get('total_time', 0),
                        'Memory Used (GB)': result.get('memory_used_gb', 0)
                    }
                    
                    # Add probability statistics
                    for prob_col in ['P_24mmh', 'P_40mmh']:
                        if prob_col in basins.columns:
                            fire_stats[f'{prob_col} High Risk'] = (basins[prob_col] > 0.5).sum()
                            fire_stats[f'{prob_col} Mean'] = basins[prob_col].mean()
                    
                    summary_data.append(fire_stats)
            
            if summary_data:
                # Create DataFrame
                df = pd.DataFrame(summary_data)
                
                # Sort by year and name
                df = df.sort_values(['Year', 'Fire Name'])
                
                # Save to CSV
                csv_path = self.output_folder / "fire_summary_statistics.csv"
                df.to_csv(csv_path, index=False)
                
                # Create summary plot
                fig, axes = plt.subplots(2, 2, figsize=(12, 10))
                
                # Plot 1: Fires by year
                ax = axes[0, 0]
                year_counts = df['Year'].value_counts().sort_index()
                year_counts.plot(kind='bar', ax=ax)
                ax.set_title('Fires Processed by Year')
                ax.set_xlabel('Year')
                ax.set_ylabel('Number of Fires')
                
                # Plot 2: Area distribution
                ax = axes[0, 1]
                df['Area (km²)'].hist(bins=20, ax=ax)
                ax.set_title('Fire Area Distribution')
                ax.set_xlabel('Area (km²)')
                ax.set_ylabel('Frequency')
                
                # Plot 3: Processing time vs area
                ax = axes[1, 0]
                ax.scatter(df['Area (km²)'], df['Processing Time (s)'])
                ax.set_title('Processing Time vs Fire Area')
                ax.set_xlabel('Area (km²)')
                ax.set_ylabel('Processing Time (s)')
                
                # Plot 4: High risk basins
                ax = axes[1, 1]
                if 'P_24mmh High Risk' in df.columns:
                    df['P_24mmh High Risk'].hist(bins=20, ax=ax)
                    ax.set_title('High Risk Basins Distribution (24mm/hr)')
                    ax.set_xlabel('Number of High Risk Basins')
                    ax.set_ylabel('Frequency')
                
                plt.tight_layout()
                plot_path = self.output_folder / "summary_statistics.png"
                plt.savefig(plot_path, dpi=300, bbox_inches='tight')
                plt.close()
                
                logger.info(f"✅ Created summary report: {csv_path}")
                logger.info(f"✅ Created summary plot: {plot_path}")
                
                return str(csv_path)
            
        except Exception as e:
            logger.error(f"❌ Error creating summary report: {e}")
            return None