"""
Raster generation module for WILDCAT debris flow probability maps
Converts vector outputs to raster format for visualization
"""

import os
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Geospatial imports
try:
    import geopandas as gpd
    import rasterio
    from rasterio import features
    from rasterio.transform import from_bounds
    from rasterio.enums import Resampling
    from rasterio.warp import calculate_default_transform, reproject
    from shapely.geometry import mapping
    SPATIAL_LIBS_AVAILABLE = True
except ImportError:
    SPATIAL_LIBS_AVAILABLE = False
    print("Warning: Spatial libraries not available")

# Set up logging
logger = logging.getLogger(__name__)


class RasterGenerator:
    """
    Generate probability raster maps from WILDCAT vector outputs
    """
    
    def __init__(self, output_folder: str):
        """
        Initialize raster generator
        
        Args:
            output_folder: Folder to save raster outputs
        """
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        
        # Define probability thresholds and colors
        self.probability_colors = {
            'low': '#2ECC71',      # Green
            'moderate': '#F39C12',  # Orange
            'high': '#E74C3C',     # Red
            'very_high': '#8B0000'  # Dark red
        }
        
        # Probability thresholds
        self.thresholds = {
            'low': (0, 0.25),
            'moderate': (0.25, 0.50),
            'high': (0.50, 0.75),
            'very_high': (0.75, 1.0)
        }
    
    def generate_probability_rasters(self, fire_name: str, project_dir: str,
                                     probability_columns: List[str] = None,
                                     resolution: float = 30.0) -> Dict:
        """
        Generate probability rasters for a single fire
        
        Args:
            fire_name: Name of the fire
            project_dir: WILDCAT project directory
            probability_columns: List of probability columns to rasterize
            resolution: Output raster resolution in meters
            
        Returns:
            Dictionary with generation results
        """
        if probability_columns is None:
            probability_columns = ['P_16mmh', 'P_20mmh', 'P_24mmh', 'P_40mmh']
        
        logger.info(f"\n🎨 Generating probability rasters for {fire_name}")
        
        # Create output directory for this fire
        fire_output_dir = self.output_folder / fire_name
        fire_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Read WILDCAT outputs
        export_dir = Path(project_dir) / "exports"
        basins_path = export_dir / "basins.shp"
        
        if not basins_path.exists():
            logger.error(f"❌ Basins shapefile not found: {basins_path}")
            return {'success': False, 'error': 'Basins shapefile not found'}
        
        try:
            # Read basins data
            basins = gpd.read_file(basins_path)
            logger.info(f"   📊 Loaded {len(basins)} basins")
            
            # Get bounds and CRS
            bounds = basins.total_bounds
            crs = basins.crs
            
            # Calculate raster dimensions
            width = int((bounds[2] - bounds[0]) / resolution)
            height = int((bounds[3] - bounds[1]) / resolution)
            
            # Create transform
            transform = from_bounds(bounds[0], bounds[1], bounds[2], bounds[3], width, height)
            
            logger.info(f"   📐 Raster dimensions: {width} x {height} pixels")
            logger.info(f"   📏 Resolution: {resolution}m")
            
            # Generate raster for each probability column
            generated_rasters = []
            
            for prob_col in probability_columns:
                if prob_col not in basins.columns:
                    logger.warning(f"   ⚠️  Column {prob_col} not found in basins")
                    continue
                
                # Create output path
                output_path = fire_output_dir / f"{fire_name}_{prob_col}.tif"
                
                # Rasterize
                logger.info(f"   🎨 Rasterizing {prob_col}...")
                
                # Create shapes for rasterization
                shapes = []
                for idx, row in basins.iterrows():
                    if not np.isnan(row[prob_col]):
                        shapes.append((mapping(row.geometry), row[prob_col]))
                
                # Create empty raster
                raster = np.full((height, width), np.nan, dtype=np.float32)
                
                # Burn values into raster
                if shapes:
                    features.rasterize(
                        shapes=shapes,
                        out=raster,
                        transform=transform,
                        dtype=np.float32
                    )
                
                # Write raster
                with rasterio.open(
                    output_path, 'w',
                    driver='GTiff',
                    height=height,
                    width=width,
                    count=1,
                    dtype=np.float32,
                    crs=crs,
                    transform=transform,
                    nodata=np.nan,
                    compress='deflate'
                ) as dst:
                    dst.write(raster, 1)
                    
                    # Add metadata
                    dst.update_tags(
                        fire_name=fire_name,
                        probability_scenario=prob_col,
                        units='probability (0-1)',
                        source='WILDCAT debris flow model'
                    )
                
                logger.info(f"   ✅ Saved: {output_path.name}")
                generated_rasters.append(str(output_path))
            
            return {
                'success': True,
                'rasters': generated_rasters,
                'count': len(generated_rasters)
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating rasters: {e}")
            return {'success': False, 'error': str(e)}
    
    def create_hazard_classification_raster(self, probability_raster_path: str,
                                            output_path: str) -> bool:
        """
        Create a classified hazard raster from probability values
        
        Args:
            probability_raster_path: Path to probability raster
            output_path: Path for classified output
            
        Returns:
            Success status
        """
        try:
            with rasterio.open(probability_raster_path) as src:
                # Read data
                data = src.read(1)
                profile = src.profile.copy()
                
                # Create classified array
                classified = np.zeros_like(data, dtype=np.uint8)
                classified[np.isnan(data)] = 0  # No data
                
                # Apply thresholds
                for level, (low, high) in enumerate(self.thresholds.values(), 1):
                    mask = (data >= low) & (data < high)
                    classified[mask] = level
                
                # Update profile
                profile.update(
                    dtype=np.uint8,
                    nodata=0,
                    compress='deflate'
                )
                
                # Write classified raster
                with rasterio.open(output_path, 'w', **profile) as dst:
                    dst.write(classified, 1)
                    
                    # Add color interpretation
                    dst.write_colormap(
                        1, {
                            0: (255, 255, 255, 0),      # No data (transparent)
                            1: (46, 204, 113, 255),     # Low (green)
                            2: (243, 156, 18, 255),     # Moderate (orange)
                            3: (231, 76, 60, 255),      # High (red)
                            4: (139, 0, 0, 255)         # Very high (dark red)
                        }
                    )
            
            logger.info(f"✅ Created classified hazard raster: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating classified raster: {e}")
            return False
    
    def batch_generate_rasters(self, fire_projects: List[Tuple[str, Dict]],
                               probability_columns: List[str] = None,
                               resolution: float = 30.0) -> Dict:
        """
        Batch generate rasters for multiple fires
        
        Args:
            fire_projects: List of (fire_name, project_info) tuples
            probability_columns: Probability columns to rasterize
            resolution: Output resolution in meters
            
        Returns:
            Dictionary with batch results
        """
        logger.info(f"\n🎨 Batch generating rasters for {len(fire_projects)} fires")
        
        results = {
            'generated': 0,
            'failed': 0,
            'fires': {}
        }
        
        for fire_name, project_info in fire_projects:
            project_dir = project_info.get('project_dir')
            if not project_dir:
                logger.warning(f"⚠️  No project directory for {fire_name}")
                results['failed'] += 1
                continue
            
            # Generate rasters
            fire_result = self.generate_probability_rasters(
                fire_name, project_dir, probability_columns, resolution
            )
            
            results['fires'][fire_name] = fire_result
            
            if fire_result['success']:
                results['generated'] += fire_result['count']
            else:
                results['failed'] += 1
        
        return results