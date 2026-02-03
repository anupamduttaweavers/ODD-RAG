# This file contains all the operations related to vector store management.
from app.vectorstore.vectorstore import vector_store
from langchain_core.documents import Document
from app.core.logging import logger


async def add_documents(documents: list[Document]):
    """Add documents to the vector store."""
    try:
        await vector_store.aadd_documents(documents)
    except Exception as e:
        print(f"Error adding documents: {e}")


async def retrieve_similar(query, k=5):
    """Retrieve similar documents from the vector store."""
    try:
        # results = vector_store.similarity_search(query, k=k, fetch_k=5)
        results = vector_store.similarity_search_with_score(
            query, 
            k=k
        )
        # print(",".join([str(score) for doc, score in results]))
        results = [
    doc for doc, score in results 
]
        return  results
    except Exception as e:
        print(f"Error retrieving documents: {e}")
        return []


def delete_documents_by_folder(folder_name: str) -> int:
    """
    Delete all documents from a specific folder.
    
    Iterates through all documents and removes those matching the folder_name.
    
    Args:
        folder_name: Name of the folder whose documents should be deleted
        
    Returns:
        Number of documents deleted
    """
    ids_to_delete = []
    
    # Find all document IDs with matching folder_name
    for index_id, doc_id in list(vector_store.index_to_docstore_id.items()):
        try:
            doc = vector_store.docstore.search(doc_id)
            if doc and hasattr(doc, 'metadata'):
                if doc.metadata.get('folder_name') == folder_name:
                    ids_to_delete.append(doc_id)
        except Exception:
            continue
    
    # Delete the documents
    if ids_to_delete:
        try:
            vector_store.delete(ids_to_delete)
            return len(ids_to_delete)
        except Exception as e:
            print(f"Error deleting documents: {e}")
    
    return 0

def delete_documents_by_file_name(file_name: str) -> int:
    """
    Delete all documents/chunks from a specific file by its name.
    
    Args:
        file_name: Name of the file whose chunks should be deleted
    Returns:
        Number of documents deleted
    """
    ids_to_delete = []
    
    # Find all document IDs with matching file_name
    for index_id, doc_id in list(vector_store.index_to_docstore_id.items()):
        try:
            doc = vector_store.docstore.search(doc_id)
            if doc and hasattr(doc, 'metadata'):
                if doc.metadata.get('file_name') == file_name:
                    ids_to_delete.append(doc_id)
        except Exception:
            continue
    # logger.info(f"IDs to delete for file_name '{file_name}': {ids_to_delete}")
    # Delete the documents
    if ids_to_delete:
        try:
            vector_store.delete(ids_to_delete)
            return len(ids_to_delete)
        except Exception as e:
            print(f"Error deleting documents: {e}")
    
    return 0


def update_folder_name_in_metadata(old_folder_name: str, new_folder_name: str) -> int:
    """
    Update folder_name in metadata for all documents from a folder.
    
    Since FAISS docstore holds Document objects with mutable metadata dicts,
    we can update them directly.
    
    Args:
        old_folder_name: Current folder name in metadata
        new_folder_name: New folder name to set
        
    Returns:
        Number of documents updated
    """
    updated_count = 0
    
    # Iterate through all documents and update metadata
    for index_id, doc_id in list(vector_store.index_to_docstore_id.items()):
        try:
            doc = vector_store.docstore.search(doc_id)
            if doc and hasattr(doc, 'metadata'):
                if doc.metadata.get('folder_name') == old_folder_name:
                    # Update metadata directly (Document metadata is a dict, mutable)
                    doc.metadata['folder_name'] = new_folder_name
                    # Also update file_path if it contains the folder name
                    if 'file_path' in doc.metadata and old_folder_name in doc.metadata['file_path']:
                        doc.metadata['file_path'] = doc.metadata['file_path'].replace(
                            f"/{old_folder_name}/", f"/{new_folder_name}/"
                        )
                    updated_count += 1
        except Exception:
            continue
    
    return updated_count


def delete_documents_by_file_path(file_path: str) -> int:
    """
    Delete all documents/chunks from a specific file.
    
    Args:
        file_path: Path of the file whose chunks should be deleted
        
    Returns:
        Number of documents deleted
    """
    ids_to_delete = []
    
    # Find all document IDs with matching file_path
    for index_id, doc_id in list(vector_store.index_to_docstore_id.items()):
        try:
            doc = vector_store.docstore.search(doc_id)
            if doc and hasattr(doc, 'metadata'):
                if doc.metadata.get('file_path') == file_path:
                    ids_to_delete.append(doc_id)
        except Exception:
            continue
    # logger.info(f"IDs to delete for file_path '{file_path}': {ids_to_delete}")
    # Delete the documents
    if ids_to_delete:
        try:
            vector_store.delete(ids_to_delete)
            return len(ids_to_delete)
        except Exception as e:
            print(f"Error deleting documents: {e}")
    
    return 0

def get_total_docs_count() -> int:
    """Get the total number of documents in the vector store."""
    try:
        return vector_store.index.ntotal
    except Exception as e:
        print(f"Error getting total document count: {e}")
        return 0