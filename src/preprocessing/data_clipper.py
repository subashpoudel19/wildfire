"""
Data clipping module
Clips shared datasets to fire perimeters
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

try:
    import rasterio
    from rasterio.mask import mask
    import geopandas as gpd
    import fiona
    SPATIAL_LIBS_AVAILABLE = True
except ImportError:
    SPATIAL_LIBS_AVAILABLE = False

logger = logging.getLogger(__name__)


class DataClipper:
    """
    Clip shared datasets to fire perimeters
    """
    
    def __init__(self):
        """Initialize data clipper"""
        if not SPATIAL_LIBS_AVAILABLE:
            raise ImportError("Spatial libraries required for clipping")
    
    def clip_raster(self, raster_path: str, perimeter_path: str, 
                    output_path: str, buffer_distance: float = 0) -> bool:
        """
        Clip raster to fire perimeter
        
        Args:
            raster_path: Path to input raster
            perimeter_path: Path to perimeter shapefile
            output_path: Path for clipped output
            buffer_distance: Buffer distance in meters
            
        Returns:
            Success status
        """
        try:
            # Load perimeter
            perimeter = gpd.read_file(perimeter_path)
            
            # Buffer if requested
            if buffer_distance > 0:
                perimeter = perimeter.buffer(buffer_distance)
            
            # Open raster
            with rasterio.open(raster_path) as src:
                # Reproject perimeter to raster CRS if needed
                if perimeter.crs != src.crs:
                    perimeter = perimeter.to_crs(src.crs)
                
                # Clip raster
                out_image, out_transform = mask(
                    src, 
                    perimeter.geometry, 
                    crop=True,
                    nodata=src.nodata
                )
                
                # Update metadata
                out_meta = src.meta.copy()
                out_meta.update({
                    "driver": "GTiff",
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform,
                    "compress": "deflate"
                })
                
                # Write clipped raster
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with rasterio.open(output_path, "w", **out_meta) as dest:
                    dest.write(out_image)
            
            logger.info(f"✅ Clipped raster: {os.path.basename(output_path)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error clipping raster: {e}")
            return False
    
    def clip_vector(self, vector_path: str, perimeter_path: str, 
                    output_path: str, buffer_distance: float = 0) -> bool:
        """
        Clip vector data to fire perimeter
        
        Args:
            vector_path: Path to input vector file
            perimeter_path: Path to perimeter shapefile
            output_path: Path for clipped output
            buffer_distance: Buffer distance in meters
            
        Returns:
            Success status
        """
        try:
            # Load data
            vector_data = gpd.read_file(vector_path)
            perimeter = gpd.read_file(perimeter_path)
            
            # Buffer if requested
            if buffer_distance > 0:
                perimeter = perimeter.buffer(buffer_distance)
            
            # Ensure same CRS
            if vector_data.crs != perimeter.crs:
                vector_data = vector_data.to_crs(perimeter.crs)
            
            # Clip
            clipped = gpd.clip(vector_data, perimeter)
            
            # Save
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            clipped.to_file(output_path)
            
            logger.info(f"✅ Clipped vector: {os.path.basename(output_path)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error clipping vector: {e}")
            return False
    
    def clip_fire_datasets(self, fire_name: str, fire_data: Dict,
                           shared_data_paths: Dict, output_folder: str) -> Dict:
        """
        Clip all shared datasets for a fire
        
        Args:
            fire_name: Name of the fire
            fire_data: Fire data dictionary
            shared_data_paths: Paths to shared datasets
            output_folder: Output folder for clipped data
            
        Returns:
            Dictionary with clipped data paths
        """
        results = {
            'success': True,
            'clipped_paths': {},
            'errors': []
        }
        
        perimeter_path = fire_data.get('perimeter')
        if not perimeter_path:
            results['success'] = False
            results['errors'].append("No perimeter path provided")
            return results
        
        # Create output directory
        fire_output = Path(output_folder) / fire_name / "clipped"
        fire_output.mkdir(parents=True, exist_ok=True)
        
        # Clip soil data (vector)
        if shared_data_paths.get('soil'):
            soil_output = fire_output / "soil_clipped.shp"
            if self.clip_vector(
                shared_data_paths['soil'],
                perimeter_path,
                str(soil_output),
                buffer_distance=1000
            ):
                results['clipped_paths']['soil'] = str(soil_output)
            else:
                results['errors'].append("Failed to clip soil data")
        
        # Clip EVT data (raster)
        if shared_data_paths.get('evt'):
            evt_output = fire_output / "evt_clipped.tif"
            if self.clip_raster(
                shared_data_paths['evt'],
                perimeter_path,
                str(evt_output),
                buffer_distance=1000
            ):
                results['clipped_paths']['evt'] = str(evt_output)
            else:
                results['errors'].append("Failed to clip EVT data")
        
        # Clip severity data (raster) if available
        if shared_data_paths.get('severity'):
            severity_output = fire_output / "severity_clipped.tif"
            if self.clip_raster(
                shared_data_paths['severity'],
                perimeter_path,
                str(severity_output)
            ):
                results['clipped_paths']['severity'] = str(severity_output)
            else:
                results['errors'].append("Failed to clip severity data")
        
        if results['errors']:
            results['success'] = False
        
        return results