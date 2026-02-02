"""Folder management endpoints with hash registry and vectorstore synchronization."""

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from app.utils.folder_management import (
    get_all_folders,
    create_folder,
    delete_folder,
    rename_folder
)
from app.utils.hash_registry import (
    delete_hashes_by_folder,
    update_folder_name_in_registry
)
from app.vectorstore.operations import (
    delete_documents_by_folder,
    update_folder_name_in_metadata
)

router = APIRouter()


@router.get("/")
async def read_folders():
    """This endpoint returns a list of all folders in the Data directory."""
    data = get_all_folders()
    return {
        "message": "List of folders",
        "count": len(data),
        "data": data
    }


@router.post("/create")
async def create_folder_endpoint(folder_name: str = Body(..., embed=True)):
    """This endpoint creates a new folder in the Data directory."""
    success, message = create_folder(folder_name)
    if not success:
        return JSONResponse(status_code=400, content={"message": message})
    return {"message": f"Folder '{folder_name}' created successfully."}


@router.delete("/delete")
async def delete_folder_endpoint(folder_name: str = Body(..., embed=True)):
    """
    Delete a folder and sync with hash registry and vectorstore.
    
    Flow:
    1. Delete all document chunks from vectorstore with this folder_name
    2. Delete all entries from hash registry for this folder
    3. Delete the physical folder from disk
    """
    # 1. Delete from vectorstore first (while we still have the metadata)
    docs_deleted = delete_documents_by_folder(folder_name)
    
    # 2. Delete from hash registry
    hashes_deleted = delete_hashes_by_folder(folder_name)
    
    # 3. Delete physical folder
    success, message = delete_folder(folder_name)
    if not success:
        return JSONResponse(
            status_code=400,
            content={
                "message": message,
                "note": f"Cleaned up {docs_deleted} chunks from vectorstore and {hashes_deleted} entries from registry"
            }
        )
    
    return {
        "message": f"Folder '{folder_name}' deleted successfully.",
        "vectorstore_chunks_deleted": docs_deleted,
        "registry_entries_deleted": hashes_deleted
    }


@router.put("/rename")
async def rename_folder_endpoint(
    old_name: str = Body(..., embed=True),
    new_name: str = Body(..., embed=True)
):
    """
    Rename a folder and sync with hash registry and vectorstore.
    
    Flow:
    1. Rename physical folder on disk
    2. Update folder_name in hash registry entries
    3. Update folder_name in vectorstore document metadata
    """
    # 1. Rename physical folder first
    success, message = rename_folder(old_name, new_name)
    if not success:
        return JSONResponse(status_code=400, content={"message": message})
    
    # 2. Update hash registry
    registry_updated = update_folder_name_in_registry(old_name, new_name)
    
    # 3. Update vectorstore metadata
    vectorstore_updated = update_folder_name_in_metadata(old_name, new_name)
    
    return {
        "message": f"Folder '{old_name}' renamed to '{new_name}' successfully.",
        "registry_entries_updated": registry_updated,
        "vectorstore_chunks_updated": vectorstore_updated
    }