#!/usr/bin/env python3
"""
Continuous Voice Memo Monitor

This module provides continuous monitoring of voice memo directories,
automatically detecting and processing new audio files as they're created.
"""

import os
import sys
import time
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Set, Dict, List, Optional
from dataclasses import dataclass

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from audio_processor import AudioFileProcessor


@dataclass
class MonitorConfig:
    """Configuration for the continuous monitor."""
    polling_interval: int = 60  # seconds
    min_file_age: int = 30  # seconds - wait before processing to ensure file is complete
    max_file_age_days: int = 7  # only process files newer than this
    db_path: str = "processed_files.db"
    log_level: str = "INFO"


class ProcessedFileTracker:
    """Tracks which files have already been processed using SQLite."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the SQLite database for tracking processed files."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_size INTEGER NOT NULL,
                modification_time TEXT NOT NULL,
                processed_time TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT
            )
        ''')
        
        # Create index for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_file_path 
            ON processed_files(file_path)
        ''')
        
        conn.commit()
        conn.close()
    
    def is_processed(self, file_path: str, file_size: int, modification_time: str) -> bool:
        """Check if a file has already been processed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM processed_files 
            WHERE file_path = ? AND file_size = ? AND modification_time = ?
        ''', (file_path, file_size, modification_time))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def mark_processed(self, file_path: str, file_size: int, modification_time: str, 
                      success: bool, error_message: Optional[str] = None):
        """Mark a file as processed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        processed_time = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO processed_files 
            (file_path, file_size, modification_time, processed_time, success, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (file_path, file_size, modification_time, processed_time, success, error_message))
        
        conn.commit()
        conn.close()
    
    def get_processed_count(self) -> int:
        """Get the total number of processed files."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM processed_files')
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    def get_recent_processed(self, hours: int = 24) -> List[Dict]:
        """Get files processed in the last N hours."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute('''
            SELECT file_path, processed_time, success, error_message
            FROM processed_files 
            WHERE processed_time > ?
            ORDER BY processed_time DESC
        ''', (cutoff_time,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'file_path': row[0],
                'processed_time': row[1],
                'success': bool(row[2]),
                'error_message': row[3]
            })
        
        conn.close()
        return results
    
    def cleanup_old_records(self, days: int = 30):
        """Remove old processed file records."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            DELETE FROM processed_files 
            WHERE processed_time < ?
        ''', (cutoff_time,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count


class ContinuousVoiceMemoMonitor:
    """Continuously monitors for new voice memos and processes them."""
    
    def __init__(self, config: MonitorConfig, processor_callback=None):
        self.config = config
        self.processor_callback = processor_callback
        self.audio_processor = AudioFileProcessor()
        self.tracker = ProcessedFileTracker(config.db_path)
        self.running = False
        
        # Set up logging
        self._setup_logging()
        
        # Track discovered files to detect new ones
        self.known_files: Set[str] = set()
        
        self.logger.info("Continuous Voice Memo Monitor initialized")
    
    def _setup_logging(self):
        """Set up logging for the monitor."""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('voice_memo_monitor.log')
            ]
        )
        self.logger = logging.getLogger('VoiceMemoMonitor')
    
    def _is_file_ready(self, file_path: str) -> bool:
        """Check if a file is ready for processing (not still being written)."""
        try:
            stat = os.stat(file_path)
            file_age = time.time() - stat.st_mtime
            
            # File must be at least min_file_age seconds old to be considered complete
            if file_age < self.config.min_file_age:
                self.logger.debug(f"File too new, waiting: {file_path} (age: {file_age:.1f}s)")
                return False
            
            # File must not be older than max_file_age_days
            max_age = self.config.max_file_age_days * 24 * 3600
            if file_age > max_age:
                self.logger.debug(f"File too old, skipping: {file_path} (age: {file_age/3600:.1f}h)")
                return False
            
            return True
            
        except (OSError, IOError) as e:
            self.logger.warning(f"Error checking file readiness {file_path}: {e}")
            return False
    
    def _get_file_signature(self, file_path: str) -> Optional[tuple]:
        """Get a unique signature for a file (path, size, modification time)."""
        try:
            stat = os.stat(file_path)
            return (
                file_path,
                stat.st_size,
                datetime.fromtimestamp(stat.st_mtime).isoformat()
            )
        except (OSError, IOError):
            return None
    
    def discover_new_files(self) -> List[Dict]:
        """Discover new audio files that haven't been processed yet."""
        all_files = self.audio_processor.discover_audio_files()
        new_files = []
        
        for file_info in all_files:
            file_path = file_info['path']
            
            # Check if file is ready for processing
            if not self._is_file_ready(file_path):
                continue
            
            # Get file signature
            signature = self._get_file_signature(file_path)
            if not signature:
                continue
            
            file_path, file_size, modification_time = signature
            
            # Check if already processed
            if self.tracker.is_processed(file_path, file_size, modification_time):
                continue
            
            # This is a new file
            new_files.append(file_info)
            self.logger.info(f"Discovered new file: {os.path.basename(file_path)}")
        
        return new_files
    
    def process_file(self, file_info: Dict) -> Dict:
        """Process a single file and track the result."""
        file_path = file_info['path']
        filename = os.path.basename(file_path)
        
        self.logger.info(f"Processing: {filename}")
        
        # Get file signature for tracking
        signature = self._get_file_signature(file_path)
        if not signature:
            error_msg = "Could not get file signature"
            self.logger.error(f"Error processing {filename}: {error_msg}")
            return {'success': False, 'error': error_msg}
        
        file_path, file_size, modification_time = signature
        
        try:
            # Use the processor callback if provided
            if self.processor_callback:
                result = self.processor_callback(file_path)
            else:
                # Default: just log that we would process it
                result = {
                    'success': True,
                    'message': f"Would process {filename} (no callback provided)"
                }
            
            # Track the result
            success = result.get('success', False)
            error_message = result.get('error') if not success else None
            
            self.tracker.mark_processed(
                file_path, file_size, modification_time, 
                success, error_message
            )
            
            if success:
                self.logger.info(f"Successfully processed: {filename}")
                # Log Notion URL if available
                if result.get('notion_page', {}).get('page_url'):
                    self.logger.info(f"Notion page: {result['notion_page']['page_url']}")
            else:
                self.logger.error(f"Failed to process {filename}: {error_message}")
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Exception processing {filename}: {error_msg}")
            
            # Track the failure
            self.tracker.mark_processed(
                file_path, file_size, modification_time, 
                False, error_msg
            )
            
            return {'success': False, 'error': error_msg}
    
    def run_single_scan(self) -> Dict:
        """Run a single scan for new files and process them."""
        scan_start = time.time()
        self.logger.info("Starting scan for new voice memos...")
        
        try:
            new_files = self.discover_new_files()
            
            if not new_files:
                self.logger.info("No new voice memos found")
                return {
                    'success': True,
                    'files_found': 0,
                    'files_processed': 0,
                    'scan_time': time.time() - scan_start
                }
            
            self.logger.info(f"Found {len(new_files)} new voice memo(s)")
            
            processed_count = 0
            failed_count = 0
            
            for file_info in new_files:
                result = self.process_file(file_info)
                if result.get('success'):
                    processed_count += 1
                else:
                    failed_count += 1
            
            scan_time = time.time() - scan_start
            self.logger.info(f"Scan completed: {processed_count} processed, {failed_count} failed, {scan_time:.1f}s")
            
            return {
                'success': True,
                'files_found': len(new_files),
                'files_processed': processed_count,
                'files_failed': failed_count,
                'scan_time': scan_time
            }
            
        except Exception as e:
            error_msg = f"Scan failed: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'scan_time': time.time() - scan_start
            }
    
    def start_continuous_monitoring(self):
        """Start continuous monitoring loop."""
        self.running = True
        self.logger.info("Starting continuous voice memo monitoring...")
        self.logger.info(f"Polling interval: {self.config.polling_interval} seconds")
        self.logger.info(f"Database: {self.config.db_path}")
        
        # Show initial stats
        total_processed = self.tracker.get_processed_count()
        recent_processed = len(self.tracker.get_recent_processed(24))
        self.logger.info(f"Total files processed: {total_processed}")
        self.logger.info(f"Files processed in last 24h: {recent_processed}")
        
        try:
            while self.running:
                self.run_single_scan()
                
                if self.running:  # Check again in case we were stopped during scan
                    self.logger.debug(f"Waiting {self.config.polling_interval} seconds until next scan...")
                    time.sleep(self.config.polling_interval)
                    
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Monitoring stopped due to error: {e}")
        finally:
            self.running = False
            self.logger.info("Continuous monitoring stopped")
    
    def stop_monitoring(self):
        """Stop the continuous monitoring loop."""
        self.logger.info("Stopping continuous monitoring...")
        self.running = False
    
    def get_status(self) -> Dict:
        """Get current monitoring status and statistics."""
        total_processed = self.tracker.get_processed_count()
        recent_processed = self.tracker.get_recent_processed(24)
        
        return {
            'running': self.running,
            'config': {
                'polling_interval': self.config.polling_interval,
                'min_file_age': self.config.min_file_age,
                'max_file_age_days': self.config.max_file_age_days,
                'db_path': self.config.db_path
            },
            'stats': {
                'total_processed': total_processed,
                'processed_last_24h': len(recent_processed),
                'recent_files': recent_processed[:5]  # Show last 5
            }
        }


def main():
    """Demo function to test the continuous monitor."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Voice Memo Continuous Monitor")
    parser.add_argument('--interval', type=int, default=60, help='Polling interval in seconds')
    parser.add_argument('--min-age', type=int, default=30, help='Minimum file age before processing')
    parser.add_argument('--max-age-days', type=int, default=7, help='Maximum file age in days')
    parser.add_argument('--db-path', default='processed_files.db', help='Database path')
    parser.add_argument('--log-level', default='INFO', help='Log level')
    parser.add_argument('--scan-only', action='store_true', help='Run single scan only')
    
    args = parser.parse_args()
    
    config = MonitorConfig(
        polling_interval=args.interval,
        min_file_age=args.min_age,
        max_file_age_days=args.max_age_days,
        db_path=args.db_path,
        log_level=args.log_level
    )
    
    def dummy_processor(file_path: str) -> Dict:
        """Dummy processor for testing."""
        return {
            'success': True,
            'message': f"Dummy processed: {os.path.basename(file_path)}"
        }
    
    monitor = ContinuousVoiceMemoMonitor(config, dummy_processor)
    
    if args.scan_only:
        result = monitor.run_single_scan()
        print(f"Scan result: {result}")
    else:
        monitor.start_continuous_monitoring()


if __name__ == "__main__":
    main()