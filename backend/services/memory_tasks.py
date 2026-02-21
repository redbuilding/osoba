"""Background task service for auto-indexing conversations."""
import asyncio
from typing import Optional
from services.conversation_indexing import find_conversations_to_index, index_conversation
from core.config import get_logger

logger = get_logger("memory_tasks")


class MemoryTaskService:
    """Background service for auto-indexing conversations to memory."""
    
    def __init__(self, check_interval: int = 300):
        """Initialize memory task service.
        
        Args:
            check_interval: Seconds between checks (default: 300 = 5 minutes)
        """
        self.check_interval = check_interval
        self.running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the background indexing service."""
        if self.running:
            logger.warning("Memory task service already running")
            return
        
        self.running = True
        self._task = asyncio.create_task(self._indexing_loop())
        logger.info(f"Memory task service started (check interval: {self.check_interval}s)")
    
    async def stop(self):
        """Stop the background indexing service."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Memory task service stopped")
    
    async def _indexing_loop(self):
        """Main loop for finding and indexing conversations."""
        while self.running:
            try:
                await self._check_and_index()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in indexing loop: {e}", exc_info=True)
                await asyncio.sleep(self.check_interval)
    
    async def _check_and_index(self):
        """Check for conversations to index and process them."""
        try:
            # Find conversations needing indexing
            conv_ids = await find_conversations_to_index(limit=10)
            
            if not conv_ids:
                logger.debug("No conversations to index")
                return
            
            # Index each conversation
            indexed_count = 0
            for conv_id in conv_ids:
                try:
                    success = await index_conversation(conv_id)
                    if success:
                        indexed_count += 1
                except Exception as e:
                    logger.error(f"Error indexing conversation {conv_id}: {e}")
            
            if indexed_count > 0:
                logger.info(f"Indexed {indexed_count}/{len(conv_ids)} conversations")
                
        except Exception as e:
            logger.error(f"Error in check_and_index: {e}", exc_info=True)
