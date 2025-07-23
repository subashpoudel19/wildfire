"""
MTBS data extraction module
Handles extraction and organization of MTBS fire bundle data
"""

import os
import re
import zipfile
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import xml.etree.ElementTree as ET

# Set up logging
logger = logging.getLogger(__name__)


class MTBSExtractor:
    """
    Extract and organize MTBS fire bundle data
    """
    
    def __init__(self, root_folder: str):
        """
        Initialize MTBS extractor
        
        Args:
            root_folder: Root folder containing MTBS zip files organized by year
        """
        self.root_folder = Path(root_folder)
        self.root_folder.mkdir(parents=True, exist_ok=True)
    
    def extract_fire_info(self, xml_file: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract fire name and date from MTBS metadata XML
        
        Args:
            xml_file: Path to metadata XML file
            
        Returns:
            Tuple of (fire_name, fire_date)
        """
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            supplinf = root.find(".//supplinf")
            
            if supplinf is not None:
                fire_info = supplinf.text.strip()
                fire_name = None
                fire_date = None
                
                for line in fire_info.split("\n"):
                    if "Fire Name" in line:
                        fire_name = line.split(":")[1].strip()
                    elif "Date of Fire" in line:
                        fire_date = line.split(":")[1].strip()
                
                return fire_name, fire_date
        except Exception as e:
            logger.error(f"Error parsing XML file {xml_file}: {e}")
        
        return None, None
    
    def format_fire_date(self, fire_date: str) -> Optional[str]:
        """Format fire date to standardized format"""
        try:
            # Remove spaces and commas
            fire_date = fire_date.replace(" ", "").replace(",", "")
            # Split and reverse date parts
            date_parts = fire_date.split("-")
            return "".join(date_parts[::-1])
        except:
            return None
    
    def sanitize_filename(self, name: str) -> str:
        """Replace invalid characters in filename"""
        return re.sub(r'[<>:"/\\|?*]', '_', name)
    
    def extract_single_bundle(self, zip_path: Path) -> Dict:
        """
        Extract a single MTBS bundle
        
        Args:
            zip_path: Path to zip file
            
        Returns:
            Extraction result dictionary
        """
        try:
            year_folder = zip_path.parent
            folder_name = zip_path.stem
            folder_path = year_folder / folder_name
            
            # Create extraction folder
            folder_path.mkdir(exist_ok=True)
            
            # Extract zip
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(folder_path)
            
            logger.info(f"✅ Extracted: {zip_path.name}")
            
            # Find and parse XML metadata
            xml_file = None
            for file in folder_path.glob("*_metadata.xml"):
                xml_file = file
                break
            
            if xml_file:
                fire_name, fire_date = self.extract_fire_info(str(xml_file))
                
                if fire_name and fire_date:
                    # Format new folder name
                    formatted_date = self.format_fire_date(fire_date)
                    if formatted_date:
                        safe_fire_name = self.sanitize_filename(fire_name)
                        new_folder_name = f"{safe_fire_name}_{formatted_date}"
                        new_folder_path = year_folder / new_folder_name
                        
                        # Rename folder
                        if not new_folder_path.exists():
                            folder_path.rename(new_folder_path)
                            logger.info(f"   📁 Renamed to: {new_folder_name}")
                            
                            return {
                                'success': True,
                                'original': str(zip_path),
                                'extracted_to': str(new_folder_path),
                                'fire_name': fire_name,
                                'fire_date': fire_date
                            }
            
            return {
                'success': True,
                'original': str(zip_path),
                'extracted_to': str(folder_path),
                'fire_name': None,
                'fire_date': None
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to extract {zip_path}: {e}")
            return {
                'success': False,
                'original': str(zip_path),
                'error': str(e)
            }
    
    def extract_all_bundles(self, years: List[str] = None) -> Dict:
        """
        Extract all MTBS bundles for specified years
        
        Args:
            years: List of years to process (None for all)
            
        Returns:
            Extraction results summary
        """
        results = {
            'successful': 0,
            'failed': 0,
            'details': []
        }
        
        # Get year folders
        if years:
            year_folders = [self.root_folder / year for year in years 
                           if (self.root_folder / year).exists()]
        else:
            year_folders = [f for f in self.root_folder.iterdir() if f.is_dir()]
        
        # Collect all zip files
        all_zips = []
        for year_folder in year_folders:
            zip_files = list(year_folder.glob("*.zip"))
            all_zips.extend(zip_files)
        
        logger.info(f"📦 Found {len(all_zips)} zip files to extract")
        
        # Extract each bundle
        for zip_path in all_zips:
            result = self.extract_single_bundle(zip_path)
            results['details'].append(result)
            
            if result['success']:
                results['successful'] += 1
            else:
                results['failed'] += 1
        
        logger.info(f"\n✅ Extraction complete: {results['successful']} successful, {results['failed']} failed")
        
        return results
    
    def count_zip_files(self, years: List[str] = None) -> int:
        """Count number of zip files to process"""
        count = 0
        
        if years:
            year_folders = [self.root_folder / year for year in years 
                           if (self.root_folder / year).exists()]
        else:
            year_folders = [f for f in self.root_folder.iterdir() if f.is_dir()]
        
        for year_folder in year_folders:
            count += len(list(year_folder.glob("*.zip")))
        
        return count