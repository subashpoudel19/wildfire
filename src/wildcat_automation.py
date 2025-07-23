"""
WILDCAT Post-Fire Debris Flow Analysis Automation Tool
Core module for automating the complete WILDCAT workflow
"""

import os
import json
import time
import shutil
import psutil
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WildcatAutomation:
    """
    Main class for automating WILDCAT post-fire debris flow analysis
    """
    
    def __init__(self, root_folder: str, output_folder: str, shared_data_paths: Dict[str, str]):
        """
        Initialize WILDCAT automation
        
        Args:
            root_folder: Root folder containing fire data organized by year
            output_folder: Output folder for results
            shared_data_paths: Dictionary with paths to shared datasets (soil, evt, severity)
        """
        self.root_folder = Path(root_folder)
        self.output_folder = Path(output_folder)
        self.shared_data_paths = shared_data_paths
        
        # Create output directories
        self.output_folder.mkdir(parents=True, exist_ok=True)
        
        # Import WILDCAT
        try:
            import wildcat
            self.wildcat = wildcat
            logger.info("✅ WILDCAT imported successfully")
        except ImportError:
            logger.error("❌ WILDCAT not found. Please install with: pip install wildcat")
            raise
    
    def get_fire_size_mb(self, fire_folder: Path) -> float:
        """Calculate total size of fire data in MB"""
        total_size = 0
        for file_path in fire_folder.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size / (1024 * 1024)
    
    def get_optimization_level(self, size_mb: float) -> str:
        """Determine optimization level based on fire size"""
        if size_mb < 10:
            return "standard"
        elif size_mb < 50:
            return "light"
        elif size_mb < 100:
            return "moderate"
        else:
            return "aggressive"
    
    def initialize_single_project(self, fire_name: str, fire_data: Dict, 
                                  project_folder: str) -> Tuple[str, bool]:
        """
        Initialize a single WILDCAT project
        
        Args:
            fire_name: Name of the fire
            fire_data: Dictionary with fire data paths
            project_folder: Base folder for WILDCAT projects
            
        Returns:
            Tuple of (project_dir, success)
        """
        try:
            logger.info(f"🔥 Initializing: {fire_name}")
            
            # Create project directory
            project_dir = os.path.join(project_folder, fire_name)
            
            # Initialize WILDCAT project
            self.wildcat.initialize(project_dir)
            
            # Get fire year
            year = fire_name.split('_')[0]
            
            # Configure project
            config_path = os.path.join(project_dir, "config.py")
            
            # Read default config
            with open(config_path, 'r') as f:
                config_lines = f.readlines()
            
            # Find the line containing "# Inputs"
            inputs_index = next(i for i, line in enumerate(config_lines) if "# Inputs" in line)
            
            # Custom configuration
            custom_config = f"""
# Fire-specific inputs
dem = r"{fire_data['dem']}"
perimeter = r"{fire_data['perimeter']}"
dnbr = r"{fire_data['dnbr']}"

# Shared FULL datasets (will be clipped during preprocessing)
kf = r"{self.shared_data_paths['soil']}"
evt = r"{self.shared_data_paths['evt']}"
"""
            
            # Add severity if available
            severity_path = os.path.join(self.shared_data_paths['severity_base'], f"mtbs_CA_{year}.tif")
            if os.path.exists(severity_path):
                custom_config += f'severity = r"{severity_path}"  # MTBS severity for {year}\n'
                logger.info(f"   📊 Using MTBS severity data for {year}")
            else:
                custom_config += "# severity = None  # No MTBS data - will estimate from dNBR\n"
                logger.warning(f"   ⚠️  No severity data for {year} - will estimate from dNBR")
            
            # Add KF field configuration
            custom_config += '\n# Soil data configuration\nkf_field = "KFFACT"\n'
            
            # Insert custom config
            config_lines.insert(inputs_index + 1, custom_config)
            
            # Write updated config
            with open(config_path, 'w') as f:
                f.writelines(config_lines)
            
            # Check fire size for optimization
            fire_size_mb = self.get_fire_size_mb(Path(fire_data['folder']))
            optimization_level = self.get_optimization_level(fire_size_mb)
            
            logger.info(f"   📁 Project directory: {project_dir}")
            logger.info(f"   📊 Fire size: {fire_size_mb:.1f} MB")
            logger.info(f"   ⚡ Optimization: {optimization_level}")
            logger.info(f"   ✅ Project initialized successfully")
            
            return project_dir, True
            
        except Exception as e:
            logger.error(f"   ❌ Error initializing {fire_name}: {e}")
            return None, False
    
    def initialize_all_projects(self, fire_inventory: Dict, project_folder: str) -> Dict:
        """
        Initialize WILDCAT projects for all fires
        
        Args:
            fire_inventory: Dictionary of fire data
            project_folder: Base folder for WILDCAT projects
            
        Returns:
            Dictionary with initialization results
        """
        os.makedirs(project_folder, exist_ok=True)
        
        initialized_projects = {}
        successful = 0
        failed = 0
        
        logger.info(f"\n🚀 Initializing {len(fire_inventory)} WILDCAT projects...")
        
        for i, (fire_name, fire_data) in enumerate(fire_inventory.items(), 1):
            logger.info(f"\n[{i}/{len(fire_inventory)}] {'='*50}")
            
            project_dir, success = self.initialize_single_project(
                fire_name, fire_data, project_folder
            )
            
            if success:
                initialized_projects[fire_name] = {
                    'project_dir': project_dir,
                    'fire_data': fire_data,
                    'fire_size_mb': self.get_fire_size_mb(Path(fire_data['folder']))
                }
                successful += 1
            else:
                failed += 1
        
        logger.info(f"\n{'='*70}")
        logger.info(f"📊 INITIALIZATION SUMMARY")
        logger.info(f"{'='*70}")
        logger.info(f"✅ Successful: {successful}/{len(fire_inventory)}")
        logger.info(f"❌ Failed: {failed}")
        
        return {
            'projects': initialized_projects,
            'successful': successful,
            'failed': failed
        }
    
    def run_single_assessment(self, fire_name: str, project_info: Dict) -> Dict:
        """
        Run WILDCAT assessment for a single fire
        
        Args:
            fire_name: Name of the fire
            project_info: Project information dictionary
            
        Returns:
            Assessment results dictionary
        """
        project_dir = project_info['project_dir']
        file_size_mb = project_info['fire_size_mb']
        
        logger.info(f"\n🎯 Assessing: {fire_name}")
        logger.info(f"   📁 Project: {os.path.basename(project_dir)}")
        logger.info(f"   📊 Fire size: {file_size_mb:.1f} MB")
        
        # Check memory before starting
        mem_before = psutil.virtual_memory()
        if mem_before.available / (1024**3) < 2:
            logger.warning("   ⚠️  Low memory - clearing cache")
            import gc
            gc.collect()
        
        try:
            # Preprocess
            logger.info("   🔄 Preprocessing (clipping datasets to fire perimeter)...")
            start_time = time.time()
            self.wildcat.preprocess(project_dir)
            preprocess_time = time.time() - start_time
            logger.info(f"   ✅ Preprocessed in {preprocess_time:.1f}s")
            
            # Check preprocessed files
            preprocessed_dir = os.path.join(project_dir, "preprocessed")
            if os.path.exists(preprocessed_dir):
                files = os.listdir(preprocessed_dir)
                logger.info(f"   📁 Created: {', '.join(files)}")
            
            # Assess
            logger.info("   🎯 Running debris flow assessment...")
            start_time = time.time()
            self.wildcat.assess(project_dir)
            assess_time = time.time() - start_time
            logger.info(f"   ✅ Assessed in {assess_time:.1f}s")
            
            # Export
            logger.info("   📤 Exporting results...")
            self.wildcat.export(project_dir, format="Shapefile")
            self.wildcat.export(project_dir, format="GeoJSON")
            
            # Check outputs
            export_dir = os.path.join(project_dir, "exports")
            output_files = []
            if os.path.exists(export_dir):
                for file in os.listdir(export_dir):
                    if file.endswith('.shp'):
                        file_path = os.path.join(export_dir, file)
                        size_kb = os.path.getsize(file_path) / 1024
                        output_files.append(file)
                        logger.info(f"   📁 {file}: {size_kb:.1f} KB")
            
            total_time = preprocess_time + assess_time
            
            # Memory after
            mem_after = psutil.virtual_memory()
            mem_used = (mem_before.available - mem_after.available) / (1024**3)
            
            return {
                'success': True,
                'preprocess_time': preprocess_time,
                'assess_time': assess_time,
                'total_time': total_time,
                'output_files': output_files,
                'memory_used_gb': mem_used,
                'file_size_mb': file_size_mb
            }
            
        except MemoryError as e:
            logger.error(f"   ❌ Memory Error: {e}")
            return {
                'success': False,
                'error': 'MemoryError',
                'message': str(e),
                'file_size_mb': file_size_mb
            }
            
        except Exception as e:
            logger.error(f"   ❌ Error: {e}")
            return {
                'success': False,
                'error': type(e).__name__,
                'message': str(e),
                'file_size_mb': file_size_mb
            }
    
    def run_batch_assessment(self, initialized_projects: Dict, 
                             skip_existing: bool = True,
                             memory_threshold_gb: float = 2.0) -> Dict:
        """
        Run WILDCAT assessments for all initialized projects
        
        Args:
            initialized_projects: Dictionary of initialized projects
            skip_existing: Skip fires that already have results
            memory_threshold_gb: Memory threshold for optimization
            
        Returns:
            Dictionary with assessment results
        """
        logger.info(f"\n💻 Available memory: {psutil.virtual_memory().available / (1024**3):.1f} GB")
        logger.info(f"🔥 Processing {len(initialized_projects)} fires...")
        
        # Sort by file size (smallest first)
        sorted_projects = sorted(
            initialized_projects.items(),
            key=lambda x: x[1].get('fire_size_mb', 0)
        )
        
        results = {}
        success_count = 0
        memory_errors = 0
        other_errors = 0
        overall_start = time.time()
        
        for i, (fire_name, project_info) in enumerate(sorted_projects, 1):
            logger.info(f"\n[{i}/{len(sorted_projects)}] {'='*60}")
            
            # Check if already processed
            if skip_existing:
                export_dir = os.path.join(project_info['project_dir'], "exports")
                if os.path.exists(export_dir) and any(f.endswith('.shp') for f in os.listdir(export_dir)):
                    logger.info(f"⏭️  Skipping {fire_name} - already processed")
                    continue
            
            # Run assessment
            result = self.run_single_assessment(fire_name, project_info)
            results[fire_name] = result
            
            if result['success']:
                success_count += 1
            elif result.get('error') == 'MemoryError':
                memory_errors += 1
            else:
                other_errors += 1
            
            # Progress update
            elapsed = time.time() - overall_start
            if i > 0:
                avg_time = elapsed / i
                remaining = (len(sorted_projects) - i) * avg_time
                logger.info(f"   ⏱️  Progress: {i}/{len(sorted_projects)} | "
                            f"Elapsed: {elapsed/60:.1f}min | "
                            f"ETA: {remaining/60:.1f}min")
        
        overall_time = time.time() - overall_start
        
        # Summary
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 ASSESSMENT SUMMARY")
        logger.info(f"{'='*80}")
        logger.info(f"Total fires processed: {len(results)}")
        logger.info(f"✅ Successful: {success_count}")
        logger.info(f"🧠 Memory errors: {memory_errors}")
        logger.info(f"❌ Other errors: {other_errors}")
        logger.info(f"⏱️  Total time: {overall_time/60:.1f} minutes")
        
        return results
    
    def process_single_fire(self, year: str, fire_name: str, generate_raster: bool = True) -> Dict:
        """
        Process a single fire through the complete workflow
        
        Args:
            year: Year of the fire
            fire_name: Name of the fire
            generate_raster: Whether to generate probability rasters
            
        Returns:
            Processing results dictionary
        """
        logger.info(f"\n🔥 Processing single fire: {fire_name} ({year})")
        
        # Construct fire data paths
        fire_folder = self.root_folder / year / fire_name
        if not fire_folder.exists():
            logger.error(f"❌ Fire folder not found: {fire_folder}")
            return {'success': False, 'error': 'Fire folder not found'}
        
        # Find required files
        fire_data = self._find_fire_files(fire_folder)
        if not all(fire_data.values()):
            logger.error(f"❌ Missing required files for {fire_name}")
            return {'success': False, 'error': 'Missing required files'}
        
        # Initialize project
        project_folder = self.output_folder / "wildcat_projects"
        project_dir, init_success = self.initialize_single_project(
            fire_name, fire_data, str(project_folder)
        )
        
        if not init_success:
            return {'success': False, 'error': 'Project initialization failed'}
        
        # Run assessment
        project_info = {
            'project_dir': project_dir,
            'fire_size_mb': self.get_fire_size_mb(fire_folder)
        }
        
        assessment_result = self.run_single_assessment(fire_name, project_info)
        
        if assessment_result['success'] and generate_raster:
            # Generate probability rasters
            from .visualization import RasterGenerator
            raster_gen = RasterGenerator(str(self.output_folder / "rasters"))
            raster_result = raster_gen.generate_probability_rasters(
                fire_name, project_dir
            )
            assessment_result['raster_generated'] = raster_result['success']
        
        return assessment_result
    
    def batch_process(self, years: List[str], max_fires: Optional[int] = None, 
                      generate_rasters: bool = True) -> Dict:
        """
        Batch process multiple fires across years
        
        Args:
            years: List of years to process
            max_fires: Maximum number of fires to process (None for all)
            generate_rasters: Whether to generate probability rasters
            
        Returns:
            Processing results dictionary
        """
        logger.info(f"\n🚀 Batch processing fires for years: {years}")
        
        # Collect all fires
        all_fires = []
        for year in years:
            year_folder = self.root_folder / year
            if year_folder.exists():
                for fire_folder in year_folder.iterdir():
                    if fire_folder.is_dir() and not fire_folder.name.startswith('.'):
                        all_fires.append((year, fire_folder.name))
        
        # Limit fires if specified
        if max_fires:
            all_fires = all_fires[:max_fires]
        
        logger.info(f"Found {len(all_fires)} fires to process")
        
        # Process each fire
        results = {}
        for year, fire_name in all_fires:
            fire_key = f"{year}_{fire_name}"
            results[fire_key] = self.process_single_fire(year, fire_name, generate_rasters)
        
        # Summary
        successful = sum(1 for r in results.values() if r.get('success'))
        logger.info(f"\n✅ Batch processing complete!")
        logger.info(f"   Successful: {successful}/{len(results)}")
        
        return results
    
    def _find_fire_files(self, fire_folder: Path) -> Dict[str, str]:
        """Find required files in a fire folder"""
        files = {
            'dem': None,
            'perimeter': None,
            'dnbr': None,
            'folder': str(fire_folder)
        }
        
        # Search for files
        for file_path in fire_folder.rglob("*"):
            if file_path.is_file():
                name_lower = file_path.name.lower()
                
                # DEM
                if 'dem' in name_lower and file_path.suffix == '.tif':
                    files['dem'] = str(file_path)
                # Perimeter
                elif 'burn_bndy' in name_lower and file_path.suffix == '.shp':
                    files['perimeter'] = str(file_path)
                # dNBR
                elif 'dnbr' in name_lower and file_path.suffix == '.tif':
                    files['dnbr'] = str(file_path)
        
        return files