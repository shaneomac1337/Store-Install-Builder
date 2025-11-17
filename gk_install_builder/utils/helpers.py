"""
Helper utility functions for ProjectGenerator

This module contains miscellaneous helper functions extracted
from generator.py to improve modularity.
"""

import os


def replace_urls_in_json(data, new_base_url):
    """
    Recursively replace URLs in JSON structure
    
    Args:
        data: Dictionary or list to process
        new_base_url: New base URL to replace with
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
                if 'test.cse.cloud4retail.co' in value:
                    data[key] = value.replace('test.cse.cloud4retail.co', new_base_url)
            else:
                replace_urls_in_json(value, new_base_url)
    elif isinstance(data, list):
        for item in data:
            replace_urls_in_json(item, new_base_url)


def create_helper_structure(helper_dir, helper_structure_dict, create_component_files_callback):
    """
    Create the necessary helper directory structure with placeholder files
    
    Args:
        helper_dir: Path to helper directory
        helper_structure_dict: Dictionary defining directory structure
        create_component_files_callback: Function to call for creating component files
    """
    # Create main helper directory
    os.makedirs(helper_dir, exist_ok=True)
    
    # Create sub-directories
    for dir_name in helper_structure_dict.keys():
        sub_dir = os.path.join(helper_dir, dir_name)
        os.makedirs(sub_dir, exist_ok=True)
        print(f"  Created directory: {sub_dir}")
    
    # Create component-specific directories and files
    create_component_files_callback(helper_dir)
