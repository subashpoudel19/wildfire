"""
Google Earth Engine downloader module
Handles DEM downloading from GEE for fire perimeters
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# GEE imports
try:
    import ee
    GEE_AVAILABLE = True
except ImportError:
    GEE_AVAILABLE = False
    print("Warning: Google Earth Engine not available")

# Set up logging
logger = logging.getLogger(__name__)


class GEEDownloader:
    """
    Handle Google Earth Engine operations for DEM downloading
    """
    
    def __init__(self, project_id: str, asset_path: str):
        """
        Initialize GEE downloader
        
        Args:
            project_id: GEE project ID
            asset_path: Base path for GEE assets
        """
        if not GEE_AVAILABLE:
            raise ImportError("Google Earth Engine not available. Install with: pip install earthengine-api")
        
        self.project_id = project_id
        self.asset_path = asset_path
        
        # Initialize EE
        try:
            ee.Initialize(project=project_id)
            logger.info("✅ Google Earth Engine initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize GEE: {e}")
            raise
    
    def download_dem_for_fire(self, fire_name: str, asset_id: str,
                              output_folder: str, buffer_distance: float = 5000) -> Dict:
        """
        Download DEM for a fire perimeter
        
        Args:
            fire_name: Name of the fire
            asset_id: GEE asset ID of fire perimeter
            output_folder: Output folder path
            buffer_distance: Buffer distance in meters
            
        Returns:
            Download result dictionary
        """
        try:
            # Load fire perimeter
            fire_boundary = ee.FeatureCollection(asset_id)
            
            # Buffer the boundary
            buffered = fire_boundary.geometry().buffer(buffer_distance)
            
            # Get DEM
            dem = ee.Image("USGS/3DEP/10m").clip(buffered)
            
            # Get download URL
            url = dem.getDownloadURL({
                'scale': 10,
                'crs': 'EPSG:4326',
                'region': buffered,
                'format': 'GEO_TIFF',
                'filePerBand': False
            })
            
            # Download file
            import urllib.request
            output_path = Path(output_folder) / f"{fire_name}_dem.tif"
            urllib.request.urlretrieve(url, output_path)
            
            logger.info(f"✅ Downloaded DEM: {fire_name}")
            
            return {
                'success': True,
                'output_path': str(output_path),
                'file_size_mb': output_path.stat().st_size / (1024 * 1024)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to download DEM for {fire_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def batch_download_dems(self, fire_inventory: Dict, output_folder: str,
                            max_parallel: int = 5) -> Dict:
        """
        Batch download DEMs for all fires
        
        Args:
            fire_inventory: Dictionary of fire data
            output_folder: Base output folder
            max_parallel: Maximum parallel downloads
            
        Returns:
            Download results summary
        """
        results = {
            'successful': 0,
            'failed': 0,
            'downloads': []
        }
        
        # Wait for any pending uploads
        logger.info("⏳ Waiting for asset uploads to complete...")
        time.sleep(30)
        
        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            # Submit download tasks
            future_to_fire = {}
            
            for fire_name, fire_data in fire_inventory.items():
                year = fire_name.split('_')[0]
                asset_name = fire_name.lower().replace(" ", "_").replace("-", "_")
                asset_id = f"{self.asset_path}/{year}/{asset_name}"
                
                # Output folder for this fire
                fire_output = Path(output_folder) / year / fire_name / "inputs"
                fire_output.mkdir(parents=True, exist_ok=True)
                
                future = executor.submit(
                    self.download_dem_for_fire,
                    fire_name,
                    asset_id,
                    str(fire_output)
                )
                future_to_fire[future] = fire_name
            
            # Process completed downloads
            for future in as_completed(future_to_fire):
                fire_name = future_to_fire[future]
                try:
                    result = future.result()
                    results['downloads'].append({
                        'fire_name': fire_name,
                        **result
                    })
                    
                    if result['success']:
                        results['successful'] += 1
                    else:
                        results['failed'] += 1
                        
                except Exception as e:
                    logger.error(f"Download failed for {fire_name}: {e}")
                    results['failed'] += 1
        
        return results