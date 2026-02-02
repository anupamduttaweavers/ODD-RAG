"""Celery task for syncing data folder changes."""

import asyncio
from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.hash_database import init_hash_db
from app.vectorstore.vectorstore import save_vectorstore, vector_store


@celery_app.task(bind=True, name="app.tasks.sync_tasks.sync_data_folder_changes_task")
def sync_data_folder_changes_task(self):
    """
    Celery task to sync data folder changes.
    
    Runs every 2 minutes to:
    1. Detect new files added to Data folder
    2. Detect deleted files from Data folder
    3. Update hash registry and vectorstore
    """
    from app.utils.hash_registry import sync_data_folder_changes
    
    print("=" * 60)
    print("[SYNC TASK] Starting sync_data_folder_changes...")
    print(f"[SYNC TASK] Scanning folder: {settings.BASE_DATA_FOLDER}")
    
    try:
        # Initialize hash database for this worker
        init_hash_db()
        
        # Run the async sync function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(sync_data_folder_changes(settings.BASE_DATA_FOLDER))
        loop.close()
        
        # Log results
        print("[SYNC TASK] Sync completed!")
        print(f"[SYNC TASK] New files added: {results['new_files_added']}")
        print(f"[SYNC TASK] Duplicates skipped: {results['new_files_skipped_duplicate']}")
        print(f"[SYNC TASK] Deleted files removed: {results['deleted_files_removed']}")
        print(f"[SYNC TASK] Chunks added: {results['chunks_added']}")
        print(f"[SYNC TASK] Chunks removed: {results['chunks_removed']}")
        
        if results['errors']:
            print(f"[SYNC TASK] Errors: {len(results['errors'])}")
            for error in results['errors']:
                print(f"[SYNC TASK]    - {error}")
        
        # Save vectorstore if changes were made
        if results['chunks_added'] > 0 or results['chunks_removed'] > 0:
            save_vectorstore(vector_store)
            print("[SYNC TASK] Vectorstore saved.")
        
        print("=" * 60)
        return results
        
    except Exception as e:
        print(f"[SYNC TASK] Error: {str(e)}")
        print("=" * 60)
        raise self.retry(exc=e, countdown=60, max_retries=3)
