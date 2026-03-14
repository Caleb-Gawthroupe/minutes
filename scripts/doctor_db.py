import os
import sqlite3
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("DBDoctor")

def check_sqlite_version():
    sqlite_ver = sqlite3.sqlite_version
    logger.info(f"System SQLite version: {sqlite_ver}")
    v = sqlite3.sqlite_version_info
    if v < (3, 35, 0):
        logger.warning("❌ System SQLite is too old (< 3.35.0) for ChromaDB.")
        return False
    logger.info("✅ SQLite version is sufficient.")
    return True

def apply_pysqlite_patch():
    """Attempts to swap in pysqlite3-binary for the standard sqlite3."""
    try:
        import pysqlite3
        sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
        logger.info("✅ Successfully patched sqlite3 with pysqlite3-binary.")
        return True
    except ImportError:
        logger.error("❌ 'pysqlite3-binary' not found.")
        logger.info("Please run: pip install pysqlite3-binary")
        return False

def verify_chroma():
    try:
        import chromadb
        logger.info(f"✅ ChromaDB version {chromadb.__version__} is installed.")
        
        # Test initialization
        from chromadb.config import Settings
        client = chromadb.PersistentClient(path="data/test_db", settings=Settings(anonymized_telemetry=False))
        collection = client.get_or_create_collection("test")
        collection.add(documents=["test"], ids=["1"])
        count = collection.count()
        
        if count > 0:
            logger.info("✅ Database write/read test passed.")
            # Cleanup
            import shutil
            shutil.rmtree("data/test_db", ignore_errors=True)
            return True
        else:
            logger.error("❌ Database test failed (collection empty).")
            return False
    except Exception as e:
        logger.error(f"❌ ChromaDB initialization failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("=== CivicClaw Database Doctor ===")
    
    sufficient_sqlite = check_sqlite_version()
    
    if not sufficient_sqlite:
        logger.info("Attempting to apply pysqlite3 patch...")
        if not apply_pysqlite_patch():
            logger.error("Could not fix SQLite issues automatically.")
            sys.exit(1)
            
    if verify_chroma():
        logger.info("=== SUCCESS: Database environment is ready! ===")
    else:
        logger.error("=== FAILURE: Database issues persist. ===")
        sys.exit(1)
