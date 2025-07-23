"""
GEE Asset Uploader module
Handles uploading fire perimeters to Google Earth Engine
"""

import logging
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import ee
    GEE_AVAILABLE = True
except ImportError:
    GEE_AVAILABLE = False

logger = logging.getLogger(__name__)


class AssetUploader:
    """Handle uploading assets to Google Earth Engine"""
    
    def __init__(self, project_id: str, asset_path: str):
        """Initialize asset uploader"""
        if not GEE_AVAILABLE:
            raise ImportError("Google Earth Engine not available")
        
        self.project_id = project_id
        self.asset_path = asset_path
        
        # Initialize EE
        try:
            ee.Initialize(project=project_id)
            logger.info("✅ GEE initialized for asset upload")
        except Exception as e:
            logger.error(f"❌ Failed to initialize GEE: {e}")
            raise
    
    def upload_fire_perimeter(self, fire_name: str, shapefile_path: str,
                              year: str) -> Dict:
        """
        Upload fire perimeter to GEE as an asset
        
        Args:
            fire_name: Name of the fire
            shapefile_path: Path to perimeter shapefile
            year: Fire year
            
        Returns:
            Upload result dictionary
        """
        try:
            # Construct asset ID
            asset_name = fire_name.lower().replace(" ", "_").replace("-", "_")
            asset_id = f"{self.asset_path}/{year}/{asset_name}"
            
            # Check if asset already exists
            try:
                ee.data.getAsset(asset_id)
                logger.info(f"   ℹ️  Asset already exists: {asset_id}")
                return {
                    'success': True,
                    'asset_id': asset_id,
                    'status': 'already_exists'
                }
            except ee.EEException:
                pass  # Asset doesn't exist, proceed with upload
            
            # Create upload task
            task = ee.batch.Export.table.toAsset(
                collection=ee.FeatureCollection(shapefile_path),
                description=f"Upload_{asset_name}",
                assetId=asset_id
            )
            
            # Start task
            task.start()
            
            logger.info(f"✅ Started upload: {asset_name}")
            logger.info(f"   Task ID: {task.id}")
            
            return {
                'success': True,
                'asset_id': asset_id,
                'task_id': task.id,
                'status': 'started'
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to upload {fire_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def batch_upload_perimeters(self, fire_inventory: Dict,
                                max_parallel: int = 5) -> Dict:
        """
        Batch upload fire perimeters to GEE
        
        Args:
            fire_inventory: Dictionary of fire data
            max_parallel: Maximum parallel uploads
            
        Returns:
            Upload results summary
        """
        results = {
            'successful': 0,
            'failed': 0,
            'tasks': []
        }
        
        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            # Submit upload tasks
            future_to_fire = {}
            
            for fire_name, fire_data in fire_inventory.items():
                if fire_data.get('has_perimeter'):
                    year = fire_name.split('_')[0]
                    future = executor.submit(
                        self.upload_fire_perimeter,
                        fire_name,
                        fire_data['perimeter_path'],
                        year
                    )
                    future_to_fire[future] = fire_name
            
            # Process completed uploads
            for future in as_completed(future_to_fire):
                fire_name = future_to_fire[future]
                try:
                    result = future.result()
                    results['tasks'].append({
                        'fire_name': fire_name,
                        **result
                    })
                    
                    if result['success']:
                        results['successful'] += 1
                    else:
                        results['failed'] += 1
                        
                except Exception as e:
                    logger.error(f"Upload failed for {fire_name}: {e}")
                    results['failed'] += 1
        
        return results