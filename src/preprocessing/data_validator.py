"""
Data validation module
Validates input data quality and completeness
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

try:
    import rasterio
    import geopandas as gpd
    from shapely.geometry import box
    SPATIAL_LIBS_AVAILABLE = True
except ImportError:
    SPATIAL_LIBS_AVAILABLE = False
    print("Warning: Spatial libraries not available")

logger = logging.getLogger(__name__)


class DataValidator:
    """
    Validate fire input data for WILDCAT processing
    """
    
    def __init__(self):
        """Initialize data validator"""
        if not SPATIAL_LIBS_AVAILABLE:
            logger.warning("Spatial libraries not available - validation limited")
    
    def validate_dem(self, dem_path: str) -> Dict:
        """
        Validate DEM file
        
        Args:
            dem_path: Path to DEM file
            
        Returns:
            Validation results
        """
        results = {
            'valid': False,
            'issues': [],
            'metadata': {}
        }
        
        if not os.path.exists(dem_path):
            results['issues'].append("File does not exist")
            return results
        
        try:
            with rasterio.open(dem_path) as src:
                # Check basic properties
                results['metadata'] = {
                    'width': src.width,
                    'height': src.height,
                    'bands': src.count,
                    'crs': str(src.crs),
                    'resolution': src.res,
                    'nodata': src.nodata
                }
                
                # Validate
                if src.count != 1:
                    results['issues'].append(f"Expected 1 band, found {src.count}")
                
                if src.crs is None:
                    results['issues'].append("No CRS defined")
                
                if src.nodata is None:
                    results['issues'].append("No nodata value defined")
                
                # Check for data
                data = src.read(1)
                valid_pixels = ~(data == src.nodata) if src.nodata else data != 0
                if not valid_pixels.any():
                    results['issues'].append("No valid elevation data")
                
                results['valid'] = len(results['issues']) == 0
                
        except Exception as e:
            results['issues'].append(f"Error reading DEM: {e}")
        
        return results
    
    def validate_perimeter(self, perimeter_path: str) -> Dict:
        """
        Validate fire perimeter shapefile
        
        Args:
            perimeter_path: Path to perimeter shapefile
            
        Returns:
            Validation results
        """
        results = {
            'valid': False,
            'issues': [],
            'metadata': {}
        }
        
        if not os.path.exists(perimeter_path):
            results['issues'].append("File does not exist")
            return results
        
        try:
            gdf = gpd.read_file(perimeter_path)
            
            # Check basic properties
            results['metadata'] = {
                'features': len(gdf),
                'crs': str(gdf.crs),
                'geometry_type': gdf.geometry.type.unique().tolist(),
                'bounds': gdf.total_bounds.tolist()
            }
            
            # Validate
            if len(gdf) == 0:
                results['issues'].append("No features in shapefile")
            
            if gdf.crs is None:
                results['issues'].append("No CRS defined")
            
            # Check geometry validity
            invalid_geoms = ~gdf.geometry.is_valid
            if invalid_geoms.any():
                results['issues'].append(f"{invalid_geoms.sum()} invalid geometries")
            
            # Check for polygons
            if not all(geom_type in ['Polygon', 'MultiPolygon'] 
                      for geom_type in gdf.geometry.type):
                results['issues'].append("Non-polygon geometries found")
            
            results['valid'] = len(results['issues']) == 0
            
        except Exception as e:
            results['issues'].append(f"Error reading perimeter: {e}")
        
        return results
    
    def validate_dnbr(self, dnbr_path: str) -> Dict:
        """
        Validate dNBR raster
        
        Args:
            dnbr_path: Path to dNBR file
            
        Returns:
            Validation results
        """
        results = {
            'valid': False,
            'issues': [],
            'metadata': {}
        }
        
        if not os.path.exists(dnbr_path):
            results['issues'].append("File does not exist")
            return results
        
        try:
            with rasterio.open(dnbr_path) as src:
                # Check basic properties
                results['metadata'] = {
                    'width': src.width,
                    'height': src.height,
                    'bands': src.count,
                    'crs': str(src.crs),
                    'resolution': src.res,
                    'dtype': str(src.dtypes[0])
                }
                
                # Validate
                if src.count != 1:
                    results['issues'].append(f"Expected 1 band, found {src.count}")
                
                if src.crs is None:
                    results['issues'].append("No CRS defined")
                
                # Check data range
                data = src.read(1)
                data_min = data.min()
                data_max = data.max()
                
                # dNBR typically ranges from -2000 to 2000
                if data_min < -3000 or data_max > 3000:
                    results['issues'].append(f"Unusual dNBR range: {data_min} to {data_max}")
                
                results['valid'] = len(results['issues']) == 0
                
        except Exception as e:
            results['issues'].append(f"Error reading dNBR: {e}")
        
        return results
    
    def validate_fire_data(self, fire_data: Dict) -> Dict:
        """
        Validate all data for a fire
        
        Args:
            fire_data: Dictionary with paths to fire data
            
        Returns:
            Comprehensive validation results
        """
        results = {
            'fire_valid': True,
            'dem': {},
            'perimeter': {},
            'dnbr': {},
            'crs_match': True
        }
        
        # Validate each component
        if fire_data.get('dem'):
            results['dem'] = self.validate_dem(fire_data['dem'])
            if not results['dem']['valid']:
                results['fire_valid'] = False
        
        if fire_data.get('perimeter'):
            results['perimeter'] = self.validate_perimeter(fire_data['perimeter'])
            if not results['perimeter']['valid']:
                results['fire_valid'] = False
        
        if fire_data.get('dnbr'):
            results['dnbr'] = self.validate_dnbr(fire_data['dnbr'])
            if not results['dnbr']['valid']:
                results['fire_valid'] = False
        
        # Check CRS consistency
        crs_list = []
        for component in ['dem', 'perimeter', 'dnbr']:
            if results.get(component, {}).get('metadata', {}).get('crs'):
                crs_list.append(results[component]['metadata']['crs'])
        
        if len(set(crs_list)) > 1:
            results['crs_match'] = False
            results['fire_valid'] = False
            
        return results
    
    def check_spatial_overlap(self, perimeter_path: str, raster_path: str) -> bool:
        """
        Check if perimeter and raster overlap spatially
        
        Args:
            perimeter_path: Path to perimeter shapefile
            raster_path: Path to raster file
            
        Returns:
            True if they overlap
        """
        try:
            # Load perimeter
            perimeter = gpd.read_file(perimeter_path)
            
            # Get raster bounds
            with rasterio.open(raster_path) as src:
                raster_bounds = box(*src.bounds)
                raster_crs = src.crs
            
            # Convert perimeter to raster CRS if needed
            if perimeter.crs != raster_crs:
                perimeter = perimeter.to_crs(raster_crs)
            
            # Check intersection
            return perimeter.geometry.intersects(raster_bounds).any()
            
        except Exception as e:
            logger.error(f"Error checking overlap: {e}")
            return False