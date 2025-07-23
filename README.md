# WILDCAT Post-Fire Debris Flow Analysis Automation Tool

## Overview

This tool automates the entire WILDCAT model workflow for post-fire debris flow analysis. It processes MTBS fire data from initial bundle extraction through final probability raster generation for hundreds of California wildfires.

## Features

- **Automated Data Processing**: Handles MTBS bundle extraction, GEE authentication, DEM downloading, and data clipping
- **Batch Processing**: Processes multiple fires across years with robust error handling
- **Memory Management**: Optimizes processing based on fire size to prevent memory errors
- **Raster Output**: Generates probability raster maps for debris flow hazard assessment
- **Comprehensive Logging**: Tracks processing status and errors for quality control

## Repository Structure

```
wildcat-automation/
├── notebooks/
│   ├── 00_complete_workflow.ipynb      # Master notebook for complete workflow
│   ├── 01_data_preparation.ipynb       # MTBS data extraction and organization
│   ├── 02_gee_processing.ipynb         # GEE authentication and DEM download
│   ├── 03_wildcat_execution.ipynb      # WILDCAT model execution
│   ├── 04_visualization.ipynb          # Probability raster generation
│   └── examples/                        # Example notebooks for specific tasks
├── src/
│   ├── __init__.py
│   ├── wildcat_automation.py           # Main automation orchestrator class
│   ├── data_acquisition/
│   │   ├── __init__.py
│   │   ├── mtbs_extractor.py          # MTBS bundle extraction
│   │   ├── gee_downloader.py          # GEE DEM downloading
│   │   └── asset_uploader.py          # Fire perimeter upload to GEE
│   ├── preprocessing/
│   │   ├── __init__.py
│   │   ├── data_validator.py          # Input data validation
│   │   ├── data_clipper.py            # Clip soil/EVT/severity data
│   │   └── folder_organizer.py        # Organize fire folders
│   ├── wildcat_core/
│   │   ├── __init__.py
│   │   ├── project_initializer.py     # WILDCAT project setup
│   │   ├── assessment_runner.py       # Run WILDCAT assessments
│   │   └── memory_optimizer.py        # Memory management utilities
│   └── visualization/
│       ├── __init__.py
│       ├── raster_generator.py        # Generate probability rasters
│       ├── map_creator.py             # Create visualization maps
│       └── batch_visualizer.py        # Batch visualization tools
├── config/
│   ├── config.yaml                     # Main configuration file
│   └── wildcat_config_template.py      # WILDCAT configuration template
├── data/
│   ├── shared/                         # Shared datasets
│   │   ├── soil/                      # SSURGO soil data
│   │   ├── evt/                       # LANDFIRE EVT data
│   │   └── severity/                  # MTBS severity by year
│   └── fires/                         # Fire-specific data
│       └── {year}/                    # Organized by year
│           └── {fire_name}/           # Individual fire folders
├── docs/
│   ├── installation.md                # Installation instructions
│   ├── user_guide.md                 # User guide
│   ├── api_reference.md              # API documentation
│   └── troubleshooting.md            # Common issues and solutions
├── requirements.txt                   # Python dependencies
├── setup.py                          # Package setup
└── README.md                         # This file
```

## Installation

### Prerequisites

1. **Python 3.8+** with Anaconda/Miniconda
2. **Google Earth Engine** account and authentication
3. **WILDCAT** model installed
4. **GDAL** for geospatial operations

### Setup Steps

```bash
# Clone the repository
git clone https://github.com/yourusername/wildcat-automation.git
cd wildcat-automation

# Create conda environment
conda create -n wildcat_env python=3.8
conda activate wildcat_env

# Install dependencies
pip install -r requirements.txt

# Install WILDCAT (if not already installed)
pip install wildcat

# Authenticate Google Earth Engine
earthengine authenticate
```

## Data Requirements

### Required Datasets

1. **MTBS Fire Bundles**: Download from [MTBS Direct Download](https://mtbs.gov/direct-download)
2. **Soil Data (SSURGO)**: Place in `data/shared/soil/`
3. **EVT Data (LANDFIRE)**: Place in `data/shared/evt/`
4. **MTBS Severity Maps**: Organize by year in `data/shared/severity/`

### Folder Structure for MTBS Data

```
data/fires/
├── 2017/
│   ├── fire_bundle_1.zip
│   ├── fire_bundle_2.zip
│   └── ...
├── 2018/
├── 2019/
└── ...
```

## Quick Start

### 1. Process a Single Fire

```python
from src.wildcat_automation import WildcatAutomation

# Initialize the automation tool
wildcat = WildcatAutomation(
    root_folder="./data/fires",
    output_folder="./outputs",
    shared_data_paths={
        'soil': './data/shared/soil/ussoils_18.shp',
        'evt': './data/shared/evt/LC24_EVT_250.tif',
        'severity_base': './data/shared/severity'
    }
)

# Process a single fire
wildcat.process_single_fire(
    year="2019",
    fire_name="BRICEBURG October062019",
    generate_raster=True
)
```

### 2. Batch Process Multiple Fires

```python
# Process all fires for specific years
wildcat.batch_process(
    years=["2019", "2020", "2021"],
    max_fires=None,  # Process all fires
    generate_rasters=True
)
```

### 3. Use the Master Notebook

Open `notebooks/00_complete_workflow.ipynb` for an interactive walkthrough of the entire process.

## Configuration

Edit `config/config.yaml` to customize:

```yaml
# Path configurations
paths:
  root_folder: "./data/fires"
  shared_data: "./data/shared"
  output_folder: "./outputs"
  
# Processing parameters
processing:
  years_to_process: ["2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024"]
  max_parallel_downloads: 5
  memory_threshold_gb: 2
  
# GEE settings
gee:
  project_id: "your-project-id"
  asset_path: "projects/your-project/assets/fires"
  
# WILDCAT settings
wildcat:
  kf_field: "KFFACT"
  optimization_thresholds:
    light: 10  # MB
    moderate: 50  # MB
    aggressive: 100  # MB
```

## Output Products

### 1. WILDCAT Outputs (per fire)
- `basins.shp`: Sub-basin polygons with debris flow metrics
- `segments.shp`: Stream segments with hazard ratings
- `outlets.shp`: Pour points for each basin

### 2. Probability Rasters
- `{fire_name}_P_16mmh.tif`: 16mm/hr rainfall scenario
- `{fire_name}_P_20mmh.tif`: 20mm/hr rainfall scenario
- `{fire_name}_P_24mmh.tif`: 24mm/hr rainfall scenario
- `{fire_name}_P_40mmh.tif`: 40mm/hr rainfall scenario

### 3. Summary Products
- `assessment_summary.json`: Processing status for all fires
- `fire_statistics.csv`: Key metrics for each fire
- `processing_log.txt`: Detailed processing log

## Workflow Steps

### Step 1: Data Preparation
1. Download MTBS bundles and place in year folders
2. Run bundle extraction: `notebooks/01_data_preparation.ipynb`
3. Validate extracted data

### Step 2: GEE Processing
1. Authenticate GEE
2. Upload fire perimeters as assets
3. Download DEMs for each fire

### Step 3: WILDCAT Execution
1. Initialize WILDCAT projects
2. Configure each fire with appropriate data paths
3. Run batch assessment with memory optimization

### Step 4: Visualization
1. Generate probability rasters from WILDCAT outputs
2. Create composite hazard maps
3. Export final products

## Advanced Usage

### Custom Processing Pipeline

```python
from src.wildcat_automation import WildcatAutomation
from src.preprocessing import DataValidator
from src.visualization import RasterGenerator

# Validate data first
validator = DataValidator()
validation_results = validator.validate_fire_data(fire_data)

# Run WILDCAT if validation passes
if validation_results['fire_valid']:
    wildcat = WildcatAutomation(config_path="config/config.yaml")
    results = wildcat.process_single_fire(year, fire_name)
    
    # Generate custom visualizations
    if results['success']:
        raster_gen = RasterGenerator("./outputs/rasters")
        raster_gen.generate_probability_rasters(
            fire_name, 
            project_dir,
            resolution=10  # Higher resolution
        )
```

### Memory Optimization

```python
from src.wildcat_core import MemoryOptimizer

# Check available memory
mem_info = MemoryOptimizer.get_memory_info()
print(f"Available memory: {mem_info['available_gb']:.1f} GB")

# Get optimization settings
opt_config = MemoryOptimizer.get_optimization_config(
    fire_size_mb=150,
    available_memory_gb=mem_info['available_gb']
)

# Apply optimization
MemoryOptimizer.optimize_memory(aggressive=True)
```

## Troubleshooting

### Common Issues

1. **Memory Errors**
   - Solution: Increase optimization threshold or process fewer fires in parallel
   - Use the memory optimizer: `MemoryOptimizer.optimize_memory(aggressive=True)`

2. **GEE Authentication Failed**
   - Solution: Re-authenticate with `earthengine authenticate`
   - Check project ID in configuration

3. **Missing KF Field**
   - Solution: Ensure soil data has KFFACT field or update config

4. **DEM Download Failures**
   - Solution: Check GEE quotas and asset permissions
   - Verify fire perimeters uploaded successfully

## API Reference

### Main Classes

#### WildcatAutomation
Main orchestrator class for the complete workflow.

```python
wildcat = WildcatAutomation(root_folder, output_folder, shared_data_paths)
wildcat.process_single_fire(year, fire_name, generate_raster=True)
wildcat.batch_process(years, max_fires=None, generate_rasters=True)
```

#### MTBSExtractor
Handles MTBS bundle extraction.

```python
extractor = MTBSExtractor(root_folder)
extractor.extract_all_bundles(years=["2019", "2020"])
```

#### RasterGenerator
Generates probability rasters from vector outputs.

```python
raster_gen = RasterGenerator(output_folder)
raster_gen.generate_probability_rasters(fire_name, project_dir, resolution=30)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Citation

If you use this tool in your research, please cite:

```
@software{wildcat_automation,
  title={WILDCAT Post-Fire Debris Flow Analysis Automation Tool},
  author={Your Name},
  year={2024},
  url={https://github.com/yourusername/wildcat-automation}
}
```

## License

This project is licensed under the MIT License - see LICENSE file for details.

## Acknowledgments

- USGS for the WILDCAT model
- MTBS for fire perimeter and severity data
- Google Earth Engine for DEM access
- All contributors to this project