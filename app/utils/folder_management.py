# This holdes the set of functions that manage the folders in the application
import os
from pathlib import Path
from typing import List

from app.core.config import settings


# Folder management functions
def get_base_data_folder() -> Path:
    """Get the base data folder path from settings."""
    return settings.BASE_DATA_FOLDER


def get_all_folders() -> List[str]:
    """Retrieve all folder names in the Data folder."""
    try:
        data_folder = get_base_data_folder()
        folders = [name for name in os.listdir(data_folder) if os.path.isdir(os.path.join(data_folder, name))]
        return folders
    except FileNotFoundError:
        return []   

def create_folder(folder_name: str) -> bool:
    """Create a new folder in the Data folder."""
    try:
        data_folder = get_base_data_folder()
        existing_folders = get_all_folders()
        if folder_name in existing_folders:
            return False, "Folder already exists"
        new_folder_path = data_folder / folder_name
        new_folder_path.mkdir(parents=True, exist_ok=False)
        return True, "Folder created successfully"
    except FileExistsError:
        return False, "Folder already exists"
    
def delete_folder(folder_name: str) -> bool:
    """Delete a folder from the Data folder."""
    try:
        data_folder = get_base_data_folder()
        folder_path = data_folder / folder_name
        if folder_path.exists() and folder_path.is_dir():
            os.rmdir(folder_path)
            return True, "Folder deleted successfully"
        return False, "Folder does not exist"
    except Exception:
        return False, "Error occurred during deletion"
    
def rename_folder(old_name: str, new_name: str) -> bool:
    """Rename a folder in the Data folder."""
    try:
        data_folder = get_base_data_folder()
        old_folder_path = data_folder / old_name
        new_folder_path = data_folder / new_name
        if old_folder_path.exists() and old_folder_path.is_dir():
            old_folder_path.rename(new_folder_path)
            return True,"Folder renamed successfully"
        return False,"Old folder does not exist"
    except Exception:
        return False,"Error occurred during renaming"
    

def delete_file(file_name: str,folder_name: str):
    try:
        data_folder = get_base_data_folder()
        file_path = data_folder / folder_name / file_name
        if file_path.exists() and file_path.is_file():
            os.remove(file_path)
            return True, "File deleted successfully"
        return False, "File does not exist"
    except Exception:
        return False, "Error occurred during deletion"