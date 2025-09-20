#!/usr/bin/env python3
"""
Whisper Transcription Module

This module handles audio transcription using OpenAI Whisper models.
"""

import os
import whisper
import torch
from datetime import datetime
from typing import Dict, Optional, List
import tempfile
import shutil


class WhisperTranscriber:
    """Handles audio transcription using Whisper models."""
    
    def __init__(self, model_name: str = "base"):
        """
        Initialize the transcriber with a Whisper model.
        
        Args:
            model_name: Whisper model to use ("tiny", "base", "small", "medium", "large")
        """
        self.model_name = model_name
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")
    
    def load_model(self):
        """Load the Whisper model if not already loaded."""
        if self.model is None:
            print(f"Loading Whisper model '{self.model_name}'...")
            try:
                self.model = whisper.load_model(self.model_name, device=self.device)
                print(f"Model '{self.model_name}' loaded successfully")
            except Exception as e:
                print(f"Error loading model: {e}")
                raise
    
    def transcribe_audio(self, audio_path: str, **kwargs) -> Dict:
        """
        Transcribe an audio file.
        
        Args:
            audio_path: Path to the audio file
            **kwargs: Additional options for Whisper transcription
            
        Returns:
            Dictionary containing transcription results
        """
        if not os.path.exists(audio_path):
            return {
                'success': False,
                'error': f"Audio file not found: {audio_path}",
                'transcription': None
            }
        
        # Load model if needed
        self.load_model()
        
        try:
            print(f"Transcribing: {os.path.basename(audio_path)}")
            
            # Default transcription options
            transcribe_options = {
                'language': 'en',  # Can be auto-detected by removing this
                'task': 'transcribe',
                'verbose': False,
                **kwargs
            }
            
            # Perform transcription
            result = self.model.transcribe(audio_path, **transcribe_options)
            
            # Process the result
            processed_result = self._process_transcription_result(result, audio_path)
            
            return {
                'success': True,
                'error': None,
                'transcription': processed_result
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Transcription failed: {str(e)}",
                'transcription': None
            }
    
    def _process_transcription_result(self, result: Dict, audio_path: str) -> Dict:
        """Process the raw Whisper result into a structured format."""
        
        # Extract segments with timestamps
        segments = []
        if 'segments' in result:
            for segment in result['segments']:
                segments.append({
                    'start': segment.get('start', 0),
                    'end': segment.get('end', 0),
                    'text': segment.get('text', '').strip(),
                    'confidence': segment.get('avg_logprob', 0)  # Whisper doesn't have direct confidence, use logprob
                })
        
        # Get the full text
        full_text = result.get('text', '').strip()
        
        # Extract language detection info
        language = result.get('language', 'unknown')
        
        return {
            'full_text': full_text,
            'language': language,
            'segments': segments,
            'word_count': len(full_text.split()) if full_text else 0,
            'model_used': self.model_name,
            'transcription_date': datetime.now().isoformat(),
            'audio_file': os.path.basename(audio_path),
            'audio_path': audio_path
        }
    
    def transcribe_with_timestamps(self, audio_path: str) -> Dict:
        """
        Transcribe audio with detailed timestamp information.
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Transcription result with detailed segments
        """
        return self.transcribe_audio(
            audio_path,
            word_timestamps=True,
            prepend_punctuations="\"'([{-",
            append_punctuations="\"'.!?:)]}"
        )
    
    def get_transcription_summary(self, transcription_result: Dict) -> str:
        """Generate a summary of transcription results."""
        if not transcription_result.get('success'):
            return f"Transcription failed: {transcription_result.get('error', 'Unknown error')}"
        
        trans = transcription_result['transcription']
        
        summary_lines = [
            f"Transcription Summary",
            f"─" * 50,
            f"File: {trans['audio_file']}",
            f"Model: {trans['model_used']}",
            f"Language: {trans['language']}",
            f"Word Count: {trans['word_count']}",
            f"Segments: {len(trans['segments'])}",
            f"Date: {trans['transcription_date']}",
            f"",
            f"Full Text:",
            f"─" * 20,
            trans['full_text']
        ]
        
        if trans['segments']:
            summary_lines.extend([
                f"",
                f"Timestamps:",
                f"─" * 20
            ])
            
            for i, segment in enumerate(trans['segments'][:5], 1):  # Show first 5 segments
                start_time = self._format_timestamp(segment['start'])
                end_time = self._format_timestamp(segment['end'])
                summary_lines.append(f"{i}. [{start_time} - {end_time}] {segment['text']}")
            
            if len(trans['segments']) > 5:
                summary_lines.append(f"... and {len(trans['segments']) - 5} more segments")
        
        return '\n'.join(summary_lines)
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format timestamp in MM:SS format."""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def get_available_models(self) -> List[str]:
        """Get list of available Whisper models."""
        return ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]
    
    def estimate_transcription_time(self, audio_duration: float) -> str:
        """Estimate transcription time based on model and audio duration."""
        # Rough estimates based on model complexity (CPU times)
        time_multipliers = {
            "tiny": 0.1,
            "base": 0.2,
            "small": 0.4,
            "medium": 0.8,
            "large": 1.5,
            "large-v2": 1.5,
            "large-v3": 1.5
        }
        
        multiplier = time_multipliers.get(self.model_name, 0.5)
        estimated_seconds = audio_duration * multiplier
        
        if estimated_seconds < 60:
            return f"~{int(estimated_seconds)} seconds"
        else:
            minutes = int(estimated_seconds // 60)
            return f"~{minutes} minute{'s' if minutes != 1 else ''}"


def main():
    """Demo function to test transcription."""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python transcriber.py <audio_file_path>")
        return
    
    audio_path = sys.argv[1]
    
    # Create transcriber
    transcriber = WhisperTranscriber(model_name="base")
    
    print(f"Available models: {transcriber.get_available_models()}")
    print(f"Using model: {transcriber.model_name}")
    
    # Transcribe
    result = transcriber.transcribe_audio(audio_path)
    
    # Display results
    print("\n" + transcriber.get_transcription_summary(result))


if __name__ == "__main__":
    main()