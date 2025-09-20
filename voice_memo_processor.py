#!/usr/bin/env python3
"""
Voice Memo Processor

Main workflow script for processing Voice Memos:
1. Discover and list available Voice Memo files
2. Allow user to select a recording
3. Extract metadata and transcribe with Whisper
4. Create Notion content page
5. Suggest activity database linking strategies

Usage:
    python voice_memo_processor.py [--model MODEL_NAME] [--auto-select]
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from audio_processor import AudioFileProcessor
from transcriber import WhisperTranscriber
from notion_integration import NotionIntegrator


class VoiceMemoProcessor:
    """Main processor for Voice Memo workflow."""
    
    def __init__(self, whisper_model: str = "base"):
        """Initialize the processor with specified Whisper model."""
        self.audio_processor = AudioFileProcessor()
        self.transcriber = WhisperTranscriber(model_name=whisper_model)
        self.notion_integrator = NotionIntegrator()
        
        print(f"Voice Memo Processor initialized with Whisper model: {whisper_model}")
    
    def run_interactive_workflow(self) -> Dict:
        """Run the complete interactive workflow."""
        print("=" * 60)
        print("🎙️  VOICE MEMO TRANSCRIPTION & NOTION INTEGRATION")
        print("=" * 60)
        
        try:
            # Step 1: Discover audio files
            print("\n📂 Step 1: Discovering Voice Memo files...")
            audio_files = self.audio_processor.discover_audio_files()
            
            if not audio_files:
                print("❌ No Voice Memo files found in expected locations.")
                return {'success': False, 'error': 'No audio files found'}
            
            print(f"✅ Found {len(audio_files)} audio files")
            
            # Step 2: Let user select a file
            print("\n🎯 Step 2: Select a Voice Memo to process")
            selected_file = self._select_audio_file(audio_files)
            
            if not selected_file:
                print("❌ No file selected. Exiting.")
                return {'success': False, 'error': 'No file selected'}
            
            # Step 3: Extract detailed metadata
            print(f"\n📊 Step 3: Extracting metadata for: {selected_file['filename']}")
            metadata = self.audio_processor.get_detailed_metadata(selected_file['path'])
            
            if metadata.get('error'):
                print(f"⚠️  Warning: {metadata['error']}")
            
            self._display_metadata(metadata)
            
            # Step 4: Transcribe the audio
            print(f"\n🤖 Step 4: Transcribing with Whisper...")
            
            # Estimate transcription time
            duration = metadata.get('duration_seconds')
            if duration:
                try:
                    duration_float = float(duration)
                    estimate = self.transcriber.estimate_transcription_time(duration_float)
                    print(f"⏱️  Estimated transcription time: {estimate}")
                except (ValueError, TypeError):
                    pass
            
            transcription_result = self.transcriber.transcribe_audio(selected_file['path'])
            
            if not transcription_result['success']:
                print(f"❌ Transcription failed: {transcription_result['error']}")
                return transcription_result
            
            print("✅ Transcription completed successfully!")
            self._display_transcription_summary(transcription_result['transcription'])
            
            # Step 5: Create Notion content page
            print(f"\n📝 Step 5: Creating Notion content page...")
            notion_result = self.notion_integrator.create_content_page(
                transcription_result['transcription'], 
                metadata
            )
            
            if notion_result['success']:
                print("✅ Notion page created successfully!")
                print(f"📄 Page title: {notion_result['page_data']['title']}")
            else:
                print(f"⚠️  Notion page creation warning: {notion_result['error']}")
            
            # Step 6: Analyze for activity linking
            print(f"\n🔗 Step 6: Analyzing activity linking opportunities...")
            linking_suggestions = self.notion_integrator.analyze_for_activity_linking(
                transcription_result['transcription'], 
                metadata
            )
            
            self._display_linking_suggestions(linking_suggestions)
            
            # Step 7: Summary
            self._display_workflow_summary(selected_file, metadata, transcription_result, notion_result, linking_suggestions)
            
            return {
                'success': True,
                'file_processed': selected_file,
                'metadata': metadata,
                'transcription': transcription_result,
                'notion_page': notion_result,
                'linking_suggestions': linking_suggestions
            }
            
        except KeyboardInterrupt:
            print("\n\n❌ Workflow cancelled by user.")
            return {'success': False, 'error': 'Cancelled by user'}
        except Exception as e:
            print(f"\n❌ Unexpected error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _select_audio_file(self, audio_files: List[Dict]) -> Optional[Dict]:
        """Let user select an audio file from the list."""
        
        print(f"\nAvailable Voice Memo files (showing newest first):")
        print("-" * 80)
        
        for i, file_info in enumerate(audio_files[:20], 1):  # Show up to 20 files
            filename = file_info['filename']
            size_mb = file_info['size'] / (1024 * 1024)
            modified = file_info['modified_date'][:16].replace('T', ' ')
            
            print(f"{i:2d}. {filename[:50]:<50} ({size_mb:.1f}MB) {modified}")
        
        if len(audio_files) > 20:
            print(f"    ... and {len(audio_files) - 20} more files")
        
        print("-" * 80)
        
        while True:
            try:
                choice = input(f"\nSelect a file (1-{min(len(audio_files), 20)}) or 'q' to quit: ").strip()
                
                if choice.lower() in ['q', 'quit', 'exit']:
                    return None
                
                index = int(choice) - 1
                if 0 <= index < min(len(audio_files), 20):
                    selected = audio_files[index]
                    print(f"\n✅ Selected: {selected['filename']}")
                    return selected
                else:
                    print(f"❌ Please enter a number between 1 and {min(len(audio_files), 20)}")
                    
            except ValueError:
                print("❌ Please enter a valid number or 'q' to quit")
            except (EOFError, KeyboardInterrupt):
                return None
    
    def _display_metadata(self, metadata: Dict):
        """Display formatted metadata information."""
        print("\n📊 Audio File Metadata:")
        print("-" * 40)
        
        formatted = self.audio_processor.format_metadata_for_display(metadata)
        for line in formatted.split('\n'):
            if line.strip():
                print(f"   {line}")
    
    def _display_transcription_summary(self, transcription: Dict):
        """Display a summary of transcription results."""
        print("\n🤖 Transcription Summary:")
        print("-" * 40)
        print(f"   Language: {transcription.get('language', 'Unknown')}")
        print(f"   Word Count: {transcription.get('word_count', 0)}")
        print(f"   Segments: {len(transcription.get('segments', []))}")
        print(f"   Model: {transcription.get('model_used', 'Unknown')}")
        
        # Show first few lines of transcription
        full_text = transcription.get('full_text', '')
        if full_text:
            print(f"\n   Preview:")
            preview = full_text[:200]
            if len(full_text) > 200:
                preview += "..."
            print(f"   \"{preview}\"")
    
    def _display_linking_suggestions(self, suggestions: List[Dict]):
        """Display activity linking suggestions."""
        print("\n🔗 Activity Database Linking Suggestions:")
        print("-" * 50)
        
        if not suggestions:
            print("   No automatic linking suggestions found.")
            return
        
        for i, suggestion in enumerate(suggestions, 1):
            confidence_emoji = {
                'high': '🟢',
                'medium': '🟡', 
                'low': '🟠'
            }.get(suggestion['confidence'], '⚪')
            
            print(f"\n{i}. {confidence_emoji} {suggestion['title']} (Confidence: {suggestion['confidence'].title()})")
            print(f"   📋 {suggestion['description']}")
            print(f"   💭 {suggestion['rationale']}")
            
            # Show search criteria
            criteria = suggestion.get('search_criteria', {})
            if criteria:
                print(f"   🔍 Search: {criteria.get('type', 'unknown')}")
    
    def _display_workflow_summary(self, selected_file: Dict, metadata: Dict, 
                                transcription_result: Dict, notion_result: Dict, 
                                linking_suggestions: List[Dict]):
        """Display a complete workflow summary."""
        print("\n" + "=" * 60)
        print("📋 WORKFLOW SUMMARY")
        print("=" * 60)
        
        print(f"📁 File Processed: {selected_file['filename']}")
        print(f"📊 Metadata: {'✅ Success' if not metadata.get('error') else '⚠️  With warnings'}")
        print(f"🤖 Transcription: {'✅ Success' if transcription_result['success'] else '❌ Failed'}")
        print(f"📝 Notion Page: {'✅ Created' if notion_result['success'] else '⚠️  With issues'}")
        print(f"🔗 Link Suggestions: {len(linking_suggestions)} found")
        
        if transcription_result['success']:
            word_count = transcription_result['transcription'].get('word_count', 0)
            print(f"📄 Content: {word_count} words transcribed")
        
        print(f"\n🎯 Next Steps:")
        print(f"   1. Review the Notion page content")
        print(f"   2. Consider the {len(linking_suggestions)} linking suggestions")
        print(f"   3. Connect to relevant activities in your database")
        print(f"   4. Add any additional tags or categorization")
        
        print("\n✨ Workflow completed successfully!")
    
    def run_batch_mode(self, file_path: str) -> Dict:
        """Process a specific file without interaction."""
        print(f"🤖 Processing file in batch mode: {os.path.basename(file_path)}")
        
        if not os.path.exists(file_path):
            return {'success': False, 'error': f'File not found: {file_path}'}
        
        try:
            # Extract metadata
            metadata = self.audio_processor.get_detailed_metadata(file_path)
            
            # Transcribe
            transcription_result = self.transcriber.transcribe_audio(file_path)
            if not transcription_result['success']:
                return transcription_result
            
            # Create Notion page
            notion_result = self.notion_integrator.create_content_page(
                transcription_result['transcription'], metadata
            )
            
            # Get linking suggestions
            linking_suggestions = self.notion_integrator.analyze_for_activity_linking(
                transcription_result['transcription'], metadata
            )
            
            return {
                'success': True,
                'metadata': metadata,
                'transcription': transcription_result,
                'notion_page': notion_result,
                'linking_suggestions': linking_suggestions
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}


def main():
    """Main entry point for the Voice Memo Processor."""
    
    parser = argparse.ArgumentParser(
        description="Process Voice Memos with Whisper transcription and Notion integration"
    )
    parser.add_argument(
        '--model', 
        default='base',
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        help='Whisper model to use (default: base)'
    )
    parser.add_argument(
        '--file',
        help='Process a specific file instead of interactive selection'
    )
    parser.add_argument(
        '--list-only',
        action='store_true',
        help='Only list available files without processing'
    )
    
    args = parser.parse_args()
    
    # Initialize processor
    try:
        processor = VoiceMemoProcessor(whisper_model=args.model)
    except Exception as e:
        print(f"❌ Failed to initialize processor: {e}")
        return 1
    
    # List-only mode
    if args.list_only:
        print("📂 Discovering Voice Memo files...")
        audio_files = processor.audio_processor.discover_audio_files()
        
        if not audio_files:
            print("❌ No Voice Memo files found.")
            return 1
        
        print(f"\n✅ Found {len(audio_files)} files:")
        for i, file_info in enumerate(audio_files, 1):
            size_mb = file_info['size'] / (1024 * 1024)
            print(f"{i:3d}. {file_info['filename']} ({size_mb:.1f}MB)")
        
        return 0
    
    # Batch mode with specific file
    if args.file:
        result = processor.run_batch_mode(args.file)
        if result['success']:
            print(f"✅ Successfully processed: {os.path.basename(args.file)}")
            return 0
        else:
            print(f"❌ Processing failed: {result['error']}")
            return 1
    
    # Interactive mode
    result = processor.run_interactive_workflow()
    
    if result['success']:
        return 0
    else:
        print(f"\n❌ Workflow failed: {result.get('error', 'Unknown error')}")
        return 1


if __name__ == "__main__":
    exit(main())