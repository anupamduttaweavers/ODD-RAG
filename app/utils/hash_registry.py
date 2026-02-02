"""Hash registry operations for file deduplication."""

import hashlib
from pathlib import Path
from typing import Optional

from sqlmodel import select

from app.core.hash_database import get_session
from app.models.hash_registry import FileHashRegistry, HashLookupResult


def calculate_hash_from_bytes(file_bytes: bytes) -> str:
    """
    Calculate SHA256 hash from file bytes.
    
    Use this to check for duplicates BEFORE saving the file.
    
    Args:
        file_bytes: Raw bytes of the file
        
    Returns:
        SHA256 hash string
    """
    return hashlib.sha256(file_bytes).hexdigest()


def calculate_hash_from_file(file_path: str) -> str:
    """
    Calculate SHA256 hash from a file on disk.
    
    Reads file in chunks to handle large files.
    
    Args:
        file_path: Path to the file
        
    Returns:
        SHA256 hash string
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read in 64KB chunks for memory efficiency
        for chunk in iter(lambda: f.read(65536), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def lookup_hash(content_hash: str) -> HashLookupResult:
    """
    Check if a file with the given hash already exists.
    
    Searches across ALL folders (global deduplication).
    
    Args:
        content_hash: SHA256 hash of file content
        
    Returns:
        HashLookupResult with exists=True if found, False otherwise
    """
    session = get_session()
    try:
        statement = select(FileHashRegistry).where(
            FileHashRegistry.content_hash == content_hash
        )
        result = session.exec(statement).first()
        
        if result:
            return HashLookupResult(
                exists=True,
                file_name=result.file_name,
                file_path=result.file_path,
                folder_name=result.folder_name,
                message=f"Duplicate file found: '{result.file_name}' in folder '{result.folder_name}'"
            )
        
        return HashLookupResult(
            exists=False,
            message="No duplicate found"
        )
    finally:
        session.close()


def register_hash(
    content_hash: str,
    file_name: str,
    file_path: str,
    folder_name: str,
    file_type: str,
    file_size: int,
    is_processed: bool = False,
    chunk_count: Optional[int] = None
) -> FileHashRegistry:
    """
    Register a new file hash in the registry.
    
    Call this after successfully saving and processing a file.
    
    Args:
        content_hash: SHA256 hash of file content
        file_name: Original file name
        file_path: Full path to stored file
        folder_name: Folder where file is stored
        file_type: File extension (pdf, txt)
        file_size: File size in bytes
        is_processed: Whether file has been processed
        chunk_count: Number of chunks if processed
        
    Returns:
        Created FileHashRegistry record
    """
    session = get_session()
    try:
        registry_entry = FileHashRegistry(
            content_hash=content_hash,
            file_name=file_name,
            file_path=file_path,
            folder_name=folder_name,
            file_type=file_type,
            file_size=file_size,
            is_processed=is_processed,
            chunk_count=chunk_count
        )
        session.add(registry_entry)
        session.commit()
        session.refresh(registry_entry)
        return registry_entry
    finally:
        session.close()


def update_processing_status(
    content_hash: str,
    is_processed: bool = True,
    chunk_count: Optional[int] = None
) -> bool:
    """
    Update the processing status of a registered file.
    
    Args:
        content_hash: SHA256 hash of file content
        is_processed: New processing status
        chunk_count: Number of chunks after processing
        
    Returns:
        True if updated, False if hash not found
    """
    session = get_session()
    try:
        statement = select(FileHashRegistry).where(
            FileHashRegistry.content_hash == content_hash
        )
        result = session.exec(statement).first()
        
        if result:
            result.is_processed = is_processed
            if chunk_count is not None:
                result.chunk_count = chunk_count
            session.add(result)
            session.commit()
            return True
        
        return False
    finally:
        session.close()


def remove_hash(content_hash: str) -> bool:
    """
    Remove a hash from the registry.
    
    Call this when a file is deleted.
    
    Args:
        content_hash: SHA256 hash to remove
        
    Returns:
        True if removed, False if not found
    """
    session = get_session()
    try:
        statement = select(FileHashRegistry).where(
            FileHashRegistry.content_hash == content_hash
        )
        result = session.exec(statement).first()
        
        if result:
            session.delete(result)
            session.commit()
            return True
        
        return False
    finally:
        session.close()


def remove_hash_by_path(file_path: str) -> bool:
    """
    Remove a hash by file path.
    
    Useful when you know the path but not the hash.
    
    Args:
        file_path: Path of the file to remove
        
    Returns:
        True if removed, False if not found
    """
    session = get_session()
    try:
        statement = select(FileHashRegistry).where(
            FileHashRegistry.file_path == file_path
        )
        result = session.exec(statement).first()
        
        if result:
            session.delete(result)
            session.commit()
            return True
        
        return False
    finally:
        session.close()


def get_all_hashes() -> list[FileHashRegistry]:
    """
    Get all registered file hashes.
    
    Returns:
        List of all FileHashRegistry records
    """
    session = get_session()
    try:
        statement = select(FileHashRegistry)
        results = session.exec(statement).all()
        return list(results)
    finally:
        session.close()


def get_hashes_by_folder(folder_name: str) -> list[FileHashRegistry]:
    """
    Get all registered files in a specific folder.
    
    Args:
        folder_name: Folder to filter by
        
    Returns:
        List of FileHashRegistry records in that folder
    """
    session = get_session()
    try:
        statement = select(FileHashRegistry).where(
            FileHashRegistry.folder_name == folder_name
        )
        results = session.exec(statement).all()
        return list(results)
    finally:
        session.close()


def delete_hashes_by_folder(folder_name: str) -> int:
    """
    Delete all hash registry entries for a folder.
    
    Call this when a folder is deleted.
    
    Args:
        folder_name: Name of the folder
        
    Returns:
        Number of entries deleted
    """
    session = get_session()
    try:
        statement = select(FileHashRegistry).where(
            FileHashRegistry.folder_name == folder_name
        )
        results = session.exec(statement).all()
        
        count = len(results)
        for record in results:
            session.delete(record)
        
        session.commit()
        return count
    finally:
        session.close()

def delete_hashes_by_file_name(file_name: str) -> int:
    """
    Delete all hash registry entries for a folder.
    
    Call this when a folder is deleted.
    
    Args:
        folder_name: Name of the folder
        
    Returns:
        Number of entries deleted
    """
    session = get_session()
    try:
        statement = select(FileHashRegistry).where(
            FileHashRegistry.file_name == file_name
        )
        results = session.exec(statement).all()
        
        count = len(results)
        for record in results:
            session.delete(record)
        
        session.commit()
        return count
    finally:
        session.close()

def update_folder_name_in_registry(old_folder_name: str, new_folder_name: str) -> int:
    """
    Update folder_name for all entries in hash registry.
    
    Call this when a folder is renamed.
    
    Args:
        old_folder_name: Current folder name
        new_folder_name: New folder name
        
    Returns:
        Number of entries updated
    """
    session = get_session()
    try:
        statement = select(FileHashRegistry).where(
            FileHashRegistry.folder_name == old_folder_name
        )
        results = session.exec(statement).all()
        
        count = 0
        for record in results:
            record.folder_name = new_folder_name
            # Also update file_path if it contains the folder name
            if old_folder_name in record.file_path:
                record.file_path = record.file_path.replace(
                    f"/{old_folder_name}/", f"/{new_folder_name}/"
                )
            session.add(record)
            count += 1
        
        session.commit()
        return count
    finally:
        session.close()


def sync_registry_with_folder(folder_path: Path, folder_name: str) -> int:
    """
    Scan a folder and register any unregistered files.
    
    Useful for startup sync or manual rebuild.
    
    Args:
        folder_path: Path to the folder to scan
        folder_name: Name of the folder
        
    Returns:
        Number of newly registered files
    """
    registered_count = 0
    
    if not folder_path.exists():
        return 0
    
    for file_path in folder_path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in ('.pdf', '.txt'):
            content_hash = calculate_hash_from_file(str(file_path))
            
            # Check if already registered
            lookup = lookup_hash(content_hash)
            if not lookup.exists:
                register_hash(
                    content_hash=content_hash,
                    file_name=file_path.name,
                    file_path=str(file_path),
                    folder_name=folder_name,
                    file_type=file_path.suffix.lower().lstrip('.'),
                    file_size=file_path.stat().st_size,
                    is_processed=False
                )
                registered_count += 1
    
    return registered_count


def sync_all_folders(base_folder: Path) -> dict[str, int]:
    """
    Sync all folders under the base data folder.
    
    Scans each subfolder and registers any unregistered files.
    
    Args:
        base_folder: Base data folder path
        
    Returns:
        Dict mapping folder names to number of files registered
    """
    results = {}
    
    if not base_folder.exists():
        return results
    
    for folder_path in base_folder.iterdir():
        if folder_path.is_dir():
            count = sync_registry_with_folder(folder_path, folder_path.name)
            results[folder_path.name] = count
    
    return results


def get_unprocessed_files() -> list[FileHashRegistry]:
    """
    Get all files that have not been processed yet.
    
    Returns:
        List of FileHashRegistry records where is_processed=False
    """
    session = get_session()
    try:
        statement = select(FileHashRegistry).where(
            FileHashRegistry.is_processed == False  # noqa: E712
        )
        results = session.exec(statement).all()
        return list(results)
    finally:
        session.close()


async def load_all_files_to_vectorstore(base_folder: Path) -> dict[str, dict]:
    """
    Load ALL files from all folders into the vectorstore.
    
    Since vectorstore is in-memory, ALL files must be loaded on each startup.
    This function:
    1. Scans all folders in base_folder
    2. Processes EVERY file (PDF/txt) and adds to vectorstore
    3. Registers any unregistered files in hash registry
    4. Marks previously unprocessed files as processed
    
    Args:
        base_folder: Base data folder path (e.g., Data/)
        
    Returns:
        Dict with results per folder: {folder_name: {loaded: n, chunks: m, newly_processed: k, errors: []}}
    """
    from app.utils.document_converstion import process_file
    from app.vectorstore.operations import add_documents
    
    results = {}
    
    if not base_folder.exists():
        return results
    
    # Iterate through each folder
    for folder_path in base_folder.iterdir():
        if not folder_path.is_dir():
            continue
            
        folder_name = folder_path.name
        folder_result = {
            "loaded": 0,
            "chunks": 0,
            "newly_processed": 0,  # Files that were unprocessed, now marked processed
            "errors": []
        }
        
        # Iterate through each file in the folder
        for file_path in folder_path.iterdir():
            if not file_path.is_file():
                continue
                
            if file_path.suffix.lower() not in ('.pdf', '.txt'):
                continue
            
            try:
                # Calculate hash
                content_hash = calculate_hash_from_file(str(file_path))
                
                # Check if already registered in hash registry
                lookup = lookup_hash(content_hash)
                was_unprocessed = False
                
                if not lookup.exists:
                    # File not registered, register it first
                    register_hash(
                        content_hash=content_hash,
                        file_name=file_path.name,
                        file_path=str(file_path),
                        folder_name=folder_name,
                        file_type=file_path.suffix.lower().lstrip('.'),
                        file_size=file_path.stat().st_size,
                        is_processed=False
                    )
                    was_unprocessed = True
                else:
                    # Check if it was previously unprocessed
                    session = get_session()
                    try:
                        statement = select(FileHashRegistry).where(
                            FileHashRegistry.content_hash == content_hash
                        )
                        file_record = session.exec(statement).first()
                        if file_record and not file_record.is_processed:
                            was_unprocessed = True
                    finally:
                        session.close()
                
                # Process the file (ALWAYS - vectorstore is in-memory)
                doc_info, chunks = process_file(
                    file_path=str(file_path),
                    folder_name=folder_name
                )
                
                # Add chunks to vectorstore
                if chunks:
                    await add_documents(chunks)
                
                # Update processing status if it was unprocessed
                if was_unprocessed:
                    update_processing_status(
                        content_hash=content_hash,
                        is_processed=True,
                        chunk_count=len(chunks)
                    )
                    folder_result["newly_processed"] += 1
                
                folder_result["loaded"] += 1
                folder_result["chunks"] += len(chunks)
                
            except Exception as e:
                folder_result["errors"].append({
                    "file": file_path.name,
                    "error": str(e)
                })
        
        results[folder_name] = folder_result
    
    return results


# Need to use this function to sync manual changes in Data folder(repeat this function after some time interval to keep the hash registry and vectorstore in sync with the Data folder)
# Add this to a schedular
async def sync_data_folder_changes(base_folder: Path) -> dict:
    """
    Scan Data folder for manual file changes and sync with hash registry and vectorstore.
    
    This function handles:
    1. NEW FILES: Files in Data folder not in hash registry
       - If hash exists & is_processed=True (duplicate content): Skip (already in vectorstore)
       - If hash is new: Register, process file, add chunks to vectorstore
    2. DELETED FILES: Files in hash registry but missing from Data folder
       - Remove from hash registry
       - Remove chunks from vectorstore
    
    Use this to protect against manual file additions/deletions without using API endpoints.
    
    Args:
        base_folder: Base data folder path (e.g., settings.BASE_DATA_FOLDER)
        
    Returns:
        Dict with sync results:
        {
            "new_files_added": int,
            "new_files_skipped_duplicate": int,
            "deleted_files_removed": int,
            "chunks_added": int,
            "chunks_removed": int,
            "errors": []
        }
    """
    from app.utils.document_converstion import process_file
    from app.vectorstore.operations import add_documents, delete_documents_by_file_path
    
    results = {
        "new_files_added": 0,
        "new_files_skipped_duplicate": 0,
        "deleted_files_removed": 0,
        "chunks_added": 0,
        "chunks_removed": 0,
        "errors": []
    }
    
    if not base_folder.exists():
        return results
    
    # Step 1: Get all registered files from hash registry
    all_registered = get_all_hashes()
    registered_paths = {record.file_path: record for record in all_registered}
    registered_hashes = {record.content_hash: record for record in all_registered}
    
    # Step 2: Scan all files currently in Data folder
    current_files = set()
    
    for folder_path in base_folder.iterdir():
        if not folder_path.is_dir():
            continue
        
        folder_name = folder_path.name
        
        for file_path in folder_path.iterdir():
            if not file_path.is_file():
                continue
            
            if file_path.suffix.lower() not in ('.pdf', '.txt'):
                continue
            
            file_path_str = str(file_path)
            current_files.add(file_path_str)
            
            # Check if file is already registered by path
            if file_path_str in registered_paths:
                # File already registered, skip
                continue
            
            # New file detected - calculate hash
            try:
                content_hash = calculate_hash_from_file(file_path_str)
                
                # Check if this content hash already exists (duplicate content)
                if content_hash in registered_hashes:
                    existing_record = registered_hashes[content_hash]
                    # Duplicate content - check if already processed
                    if existing_record.is_processed:
                        # Skip - content already in vectorstore, no need to reprocess
                        results["new_files_skipped_duplicate"] += 1
                        continue
                
                # New file with new content - register and process
                register_hash(
                    content_hash=content_hash,
                    file_name=file_path.name,
                    file_path=file_path_str,
                    folder_name=folder_name,
                    file_type=file_path.suffix.lower().lstrip('.'),
                    file_size=file_path.stat().st_size,
                    is_processed=False
                )
                
                # Process the file and add to vectorstore
                doc_info, chunks = process_file(
                    file_path=file_path_str,
                    folder_name=folder_name
                )
                
                if chunks:
                    await add_documents(chunks)
                    results["chunks_added"] += len(chunks)
                
                # Mark as processed
                update_processing_status(
                    content_hash=content_hash,
                    is_processed=True,
                    chunk_count=len(chunks)
                )
                
                results["new_files_added"] += 1
                
            except Exception as e:
                results["errors"].append({
                    "file": file_path.name,
                    "action": "add",
                    "error": str(e)
                })
    
    # Step 3: Find deleted files (in registry but not in Data folder)
    for registered_path, record in registered_paths.items():
        if registered_path not in current_files:
            try:
                # File was deleted - remove from vectorstore
                chunks_deleted = delete_documents_by_file_path(registered_path)
                results["chunks_removed"] += chunks_deleted
                
                # Remove from hash registry
                remove_hash(record.content_hash)
                
                results["deleted_files_removed"] += 1
                
            except Exception as e:
                results["errors"].append({
                    "file": record.file_name,
                    "action": "delete",
                    "error": str(e)
                })
    
    return results
