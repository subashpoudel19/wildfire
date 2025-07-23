"""
Folder organization module
Organizes and validates fire data folders
"""

import os
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class FolderOrganizer:
    """
    Organize and validate fire data folders
    """
    
    def __init__(self, root_folder: str):
        """
        Initialize folder organizer
        
        Args:
            root_folder: Root folder containing fire data
        """
        self.root_folder = Path(root_folder)
    
    def get_fire_inventory(self, years: List[str] = None) -> Dict:
        """
        Get inventory of all fire data
        
        Args:
            years: List of years to inventory (None for all)
            
        Returns:
            Dictionary of fire data
        """
        inventory = {}
        
        # Get year folders
        if years:
            year_folders = [self.root_folder / year for year in years 
                           if (self.root_folder / year).exists()]
        else:
            year_folders = [f for f in self.root_folder.iterdir() if f.is_dir()]
        
        # Inventory each fire
        for year_folder in year_folders:
            for fire_folder in year_folder.iterdir():
                if fire_folder.is_dir() and not fire_folder.name.startswith('.'):
                    fire_name = f"{year_folder.name}_{fire_folder.name}"
                    
                    # Check for required files
                    fire_data = self._check_fire_files(fire_folder)
                    fire_data['folder'] = str(fire_folder)
                    fire_data['year'] = year_folder.name
                    fire_data['size_mb'] = self._get_folder_size(fire_folder)
                    
                    inventory[fire_name] = fire_data
        
        logger.info(f"📊 Inventoried {len(inventory)} fires")
        
        return inventory
    
    def _check_fire_files(self, fire_folder: Path) -> Dict:
        """Check for required files in a fire folder"""
        files = {
            'has_perimeter': False,
            'has_dnbr': False,
            'has_dem': False,
            'has_metadata': False,
            'perimeter_path': None,
            'dnbr_path': None,
            'dem_path': None,
            'metadata_path': None
        }
        
        # Search for files
        for file_path in fire_folder.rglob("*"):
            if file_path.is_file():
                name_lower = file_path.name.lower()
                
                # Perimeter
                if 'burn_bndy' in name_lower and file_path.suffix == '.shp':
                    files['has_perimeter'] = True
                    files['perimeter_path'] = str(file_path)
                    files['perimeter'] = str(file_path)
                
                # dNBR
                elif 'dnbr' in name_lower and file_path.suffix == '.tif':
                    files['has_dnbr'] = True
                    files['dnbr_path'] = str(file_path)
                    files['dnbr'] = str(file_path)
                
                # DEM
                elif 'dem' in name_lower and file_path.suffix == '.tif':
                    files['has_dem'] = True
                    files['dem_path'] = str(file_path)
                    files['dem'] = str(file_path)
                
                # Metadata
                elif 'metadata' in name_lower and file_path.suffix == '.xml':
                    files['has_metadata'] = True
                    files['metadata_path'] = str(file_path)
        
        return files
    
    def _get_folder_size(self, folder: Path) -> float:
        """Get total size of folder in MB"""
        total_size = 0
        for file_path in folder.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size / (1024 * 1024)
    
    def validate_fire_data(self, fire_inventory: Dict) -> Dict:
        """
        Validate fire data completeness
        
        Args:
            fire_inventory: Fire inventory dictionary
            
        Returns:
            Validation results
        """
        validation_results = {
            'complete': [],
            'missing_perimeter': [],
            'missing_dnbr': [],
            'missing_dem': [],
            'total': len(fire_inventory)
        }
        
        for fire_name, fire_data in fire_inventory.items():
            is_complete = True
            
            if not fire_data['has_perimeter']:
                validation_results['missing_perimeter'].append(fire_name)
                is_complete = False
            
            if not fire_data['has_dnbr']:
                validation_results['missing_dnbr'].append(fire_name)
                is_complete = False
            
            if not fire_data['has_dem']:
                validation_results['missing_dem'].append(fire_name)
                is_complete = False
            
            if is_complete:
                validation_results['complete'].append(fire_name)
        
        # Summary
        logger.info(f"\n📋 Validation Summary:")
        logger.info(f"   Total fires: {validation_results['total']}")
        logger.info(f"   Complete: {len(validation_results['complete'])}")
        logger.info(f"   Missing perimeter: {len(validation_results['missing_perimeter'])}")
        logger.info(f"   Missing dNBR: {len(validation_results['missing_dnbr'])}")
        logger.info(f"   Missing DEM: {len(validation_results['missing_dem'])}")
        
        return validation_results