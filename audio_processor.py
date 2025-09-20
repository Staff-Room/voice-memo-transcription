#!/usr/bin/env python3
"""
Voice Memo Audio Processing Module

This module handles discovery and metadata extraction for Voice Memo files
from iCloud Drive and other locations on macOS.
"""

import os
import glob
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


class AudioFileProcessor:
    """Handles discovery and metadata extraction for audio files."""
    
    def __init__(self):
        self.supported_formats = ['.m4a', '.wav', '.mp3', '.aiff', '.aac']
        self.voice_memo_paths = [
            os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs/Personal*/Voice memos/"),
            os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs/Content Captures/"),
            os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs/ZWC/*/Recordings/"),
        ]
    
    def discover_audio_files(self) -> List[Dict]:
        """
        Discover all audio files in Voice Memo locations.
        
        Returns:
            List of dictionaries containing file info
        """
        audio_files = []
        
        for path_pattern in self.voice_memo_paths:
            # Handle glob patterns with wildcards
            expanded_paths = glob.glob(path_pattern)
            
            for base_path in expanded_paths:
                if os.path.exists(base_path):
                    for ext in self.supported_formats:
                        pattern = os.path.join(base_path, f"*{ext}")
                        files = glob.glob(pattern)
                        
                        for file_path in files:
                            try:
                                file_info = self._get_basic_file_info(file_path)
                                if file_info:
                                    audio_files.append(file_info)
                            except Exception as e:
                                print(f"Error processing {file_path}: {e}")
        
        # Sort by modification date (newest first)
        audio_files.sort(key=lambda x: x.get('modified_date', ''), reverse=True)
        return audio_files
    
    def _get_basic_file_info(self, file_path: str) -> Optional[Dict]:
        """Get basic file information without detailed metadata."""
        try:
            stat = os.stat(file_path)
            return {
                'path': file_path,
                'filename': os.path.basename(file_path),
                'size': stat.st_size,
                'modified_date': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'created_date': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            }
        except Exception:
            return None
    
    def get_detailed_metadata(self, file_path: str) -> Dict:
        """
        Extract detailed metadata using macOS mdls command.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary containing detailed metadata
        """
        metadata = {
            'file_path': file_path,
            'filename': os.path.basename(file_path),
            'error': None
        }
        
        try:
            # Use mdls to get detailed metadata
            result = subprocess.run(
                ['mdls', file_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse mdls output
            mdls_data = self._parse_mdls_output(result.stdout)
            metadata.update(mdls_data)
            
        except subprocess.CalledProcessError as e:
            metadata['error'] = f"mdls command failed: {e}"
        except Exception as e:
            metadata['error'] = f"Metadata extraction failed: {e}"
        
        return metadata
    
    def _parse_mdls_output(self, mdls_output: str) -> Dict:
        """Parse the output from mdls command into a dictionary."""
        metadata = {}
        
        for line in mdls_output.strip().split('\n'):
            if '=' in line:
                try:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Clean up the value
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]  # Remove quotes
                    elif value == '(null)':
                        value = None
                    elif value.startswith('(') and value.endswith(')'):
                        # Handle arrays - for now just take the raw string
                        pass
                    
                    # Convert common metadata keys to readable names
                    readable_key = self._get_readable_key(key)
                    metadata[readable_key] = value
                    
                except ValueError:
                    continue
        
        return metadata
    
    def _get_readable_key(self, mdls_key: str) -> str:
        """Convert mdls keys to more readable format."""
        key_mappings = {
            'kMDItemDurationSeconds': 'duration_seconds',
            'kMDItemAudioBitRate': 'bit_rate',
            'kMDItemAudioChannelCount': 'channels',
            'kMDItemAudioSampleRate': 'sample_rate',
            'kMDItemContentCreationDate': 'creation_date',
            'kMDItemContentModificationDate': 'modification_date',
            'kMDItemFSSize': 'file_size',
            'kMDItemDisplayName': 'display_name',
            'kMDItemUserTags': 'tags',
            'kMDItemUseCount': 'use_count',
            'kMDItemLastUsedDate': 'last_used_date',
        }
        return key_mappings.get(mdls_key, mdls_key)
    
    def format_metadata_for_display(self, metadata: Dict) -> str:
        """Format metadata for human-readable display."""
        if metadata.get('error'):
            return f"Error: {metadata['error']}"
        
        lines = [f"File: {metadata.get('filename', 'Unknown')}"]
        
        # Key metadata items to display
        display_items = [
            ('Duration', metadata.get('duration_seconds')),
            ('Created', metadata.get('creation_date')),
            ('Size', metadata.get('file_size')),
            ('Channels', metadata.get('channels')),
            ('Sample Rate', metadata.get('sample_rate')),
            ('Bit Rate', metadata.get('bit_rate')),
            ('Tags', metadata.get('tags')),
            ('Use Count', metadata.get('use_count')),
        ]
        
        for label, value in display_items:
            if value is not None:
                if label == 'Duration' and isinstance(value, str):
                    try:
                        duration = float(value)
                        minutes = int(duration // 60)
                        seconds = int(duration % 60)
                        value = f"{minutes}:{seconds:02d}"
                    except ValueError:
                        pass
                elif label == 'Size' and isinstance(value, str):
                    try:
                        size_bytes = int(value)
                        size_mb = size_bytes / (1024 * 1024)
                        value = f"{size_mb:.1f} MB"
                    except ValueError:
                        pass
                
                lines.append(f"  {label}: {value}")
        
        return '\n'.join(lines)


def main():
    """Demo function to test audio file discovery."""
    processor = AudioFileProcessor()
    
    print("Discovering audio files...")
    files = processor.discover_audio_files()
    
    print(f"\nFound {len(files)} audio files:")
    for i, file_info in enumerate(files[:5], 1):  # Show first 5
        print(f"\n{i}. {file_info['filename']}")
        print(f"   Path: {file_info['path']}")
        print(f"   Size: {file_info['size']} bytes")
        print(f"   Modified: {file_info['modified_date']}")
    
    if files:
        print(f"\nGetting detailed metadata for: {files[0]['filename']}")
        metadata = processor.get_detailed_metadata(files[0]['path'])
        print("\n" + processor.format_metadata_for_display(metadata))


if __name__ == "__main__":
    main()