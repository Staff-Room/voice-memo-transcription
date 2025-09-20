#!/usr/bin/env python3
"""
Notion Integration Module

This module handles integration with Notion databases using MCP tools.
Note: This module is designed to work with Claude Code's Notion MCP tools,
not direct API calls.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import subprocess


class NotionIntegrator:
    """Handles Notion database operations via MCP tools."""
    
    def __init__(self):
        """Initialize the Notion integrator."""
        self.content_database_id = None
        self.activities_database_id = None
    
    def create_content_page(self, transcription_data: Dict, metadata: Dict) -> Dict:
        """
        Create a new page in the content database for a transcribed Voice Memo.
        
        Args:
            transcription_data: Results from Whisper transcription
            metadata: Audio file metadata
            
        Returns:
            Result of the page creation
        """
        try:
            # Prepare page properties
            page_data = self._prepare_content_page_data(transcription_data, metadata)
            
            # Note: In the actual implementation, this would use Claude Code's
            # Notion MCP tools. For now, we'll prepare the data structure.
            
            print("Creating Notion content page...")
            print(f"Title: {page_data['title']}")
            print(f"Content length: {len(page_data['content'])} characters")
            
            # This is where the MCP tool would be called
            # The actual implementation would use Claude Code's built-in Notion tools
            
            return {
                'success': True,
                'page_id': 'mock_page_id_123',  # This would be returned by MCP
                'page_data': page_data,
                'error': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'page_id': None,
                'page_data': None,
                'error': str(e)
            }
    
    def _prepare_content_page_data(self, transcription_data: Dict, metadata: Dict) -> Dict:
        """Prepare page data for the content database."""
        
        # Generate title from transcription or filename
        title = self._generate_page_title(transcription_data, metadata)
        
        # Prepare content blocks
        content_blocks = self._create_content_blocks(transcription_data, metadata)
        
        # Extract tags from audio file metadata
        tags = self._extract_tags(metadata)
        
        # Prepare page properties for Notion
        page_data = {
            'title': title,
            'content': content_blocks,
            'properties': {
                'Type': 'Voice Memo',
                'Source': 'Audio Transcription',
                'Created': datetime.now().isoformat(),
                'Duration': metadata.get('duration_seconds', ''),
                'File Size': metadata.get('file_size', ''),
                'Audio File': metadata.get('filename', ''),
                'Transcription Model': transcription_data.get('model_used', ''),
                'Language': transcription_data.get('language', ''),
                'Word Count': transcription_data.get('word_count', 0),
                'Tags': tags,
                'Audio Creation Date': metadata.get('creation_date', ''),
                'File Path': metadata.get('file_path', '')
            },
            'metadata': {
                'audio_metadata': metadata,
                'transcription_metadata': transcription_data
            }
        }
        
        return page_data
    
    def _generate_page_title(self, transcription_data: Dict, metadata: Dict) -> str:
        """Generate an appropriate title for the Notion page."""
        
        # Try to use the first sentence or meaningful phrase from transcription
        full_text = transcription_data.get('full_text', '')
        
        if full_text:
            # Take first sentence or first 50 characters
            sentences = full_text.split('.')
            if sentences and len(sentences[0].strip()) > 0:
                title = sentences[0].strip()
                if len(title) > 60:
                    title = title[:57] + "..."
                return title
            
            # Fallback to first 50 characters
            if len(full_text) > 50:
                return full_text[:47] + "..."
            return full_text
        
        # Fallback to filename without extension
        filename = metadata.get('filename', 'Voice Memo')
        if '.' in filename:
            filename = filename.rsplit('.', 1)[0]
        
        return filename
    
    def _create_content_blocks(self, transcription_data: Dict, metadata: Dict) -> List[Dict]:
        """Create content blocks for the Notion page."""
        
        blocks = []
        
        # Add summary block
        blocks.append({
            'type': 'heading_2',
            'content': 'Voice Memo Transcription'
        })
        
        # Add metadata summary
        duration = metadata.get('duration_seconds', '')
        if duration:
            try:
                duration_float = float(duration)
                minutes = int(duration_float // 60)
                seconds = int(duration_float % 60)
                duration_str = f"{minutes}:{seconds:02d}"
            except (ValueError, TypeError):
                duration_str = str(duration)
        else:
            duration_str = "Unknown"
        
        creation_date = metadata.get('creation_date', 'Unknown')
        if creation_date and creation_date != 'Unknown':
            try:
                # Format the date nicely
                dt = datetime.fromisoformat(creation_date.replace('Z', '+00:00'))
                creation_date = dt.strftime('%B %d, %Y at %I:%M %p')
            except:
                pass
        
        metadata_text = (
            f"📱 **File:** {metadata.get('filename', 'Unknown')}\n"
            f"⏱️ **Duration:** {duration_str}\n"
            f"📅 **Recorded:** {creation_date}\n"
            f"🤖 **Model:** {transcription_data.get('model_used', 'Unknown')}\n"
            f"🗣️ **Language:** {transcription_data.get('language', 'Unknown')}\n"
            f"📝 **Words:** {transcription_data.get('word_count', 0)}"
        )
        
        blocks.append({
            'type': 'paragraph',
            'content': metadata_text
        })
        
        # Add main transcription
        blocks.append({
            'type': 'heading_3',
            'content': 'Full Transcription'
        })
        
        full_text = transcription_data.get('full_text', 'No transcription available')
        blocks.append({
            'type': 'paragraph',
            'content': full_text
        })
        
        # Add timestamps if available
        segments = transcription_data.get('segments', [])
        if segments and len(segments) > 1:
            blocks.append({
                'type': 'heading_3',
                'content': 'Timestamped Segments'
            })
            
            for i, segment in enumerate(segments[:10], 1):  # Limit to first 10 segments
                start_time = self._format_timestamp(segment.get('start', 0))
                end_time = self._format_timestamp(segment.get('end', 0))
                text = segment.get('text', '').strip()
                
                if text:
                    blocks.append({
                        'type': 'paragraph',
                        'content': f"**[{start_time} - {end_time}]** {text}"
                    })
            
            if len(segments) > 10:
                blocks.append({
                    'type': 'paragraph',
                    'content': f"*... and {len(segments) - 10} more segments*"
                })
        
        return blocks
    
    def _extract_tags(self, metadata: Dict) -> List[str]:
        """Extract tags from audio file metadata."""
        tags = []
        
        # Get tags from metadata
        user_tags = metadata.get('tags', '')
        if user_tags and isinstance(user_tags, str):
            # Clean up tags (remove parentheses, split by commas)
            user_tags = user_tags.strip('()')
            if user_tags:
                tags.extend([tag.strip() for tag in user_tags.split(',') if tag.strip()])
        
        # Add automatic tags based on file location
        file_path = metadata.get('file_path', '')
        if 'Personal' in file_path:
            tags.append('Personal')
        elif 'ZWC' in file_path:
            tags.append('Work')
        elif 'Content Captures' in file_path:
            tags.append('Content')
        
        # Add tag based on duration
        duration = metadata.get('duration_seconds', '')
        if duration:
            try:
                duration_float = float(duration)
                if duration_float < 60:
                    tags.append('Short')
                elif duration_float < 300:  # 5 minutes
                    tags.append('Medium')
                else:
                    tags.append('Long')
            except (ValueError, TypeError):
                pass
        
        return list(set(tags))  # Remove duplicates
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format timestamp in MM:SS format."""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def analyze_for_activity_linking(self, transcription_data: Dict, metadata: Dict) -> List[Dict]:
        """
        Analyze transcription and metadata to suggest activity database links.
        
        Returns:
            List of linking suggestions with rationale
        """
        suggestions = []
        
        # Date-based linking
        creation_date = metadata.get('creation_date')
        if creation_date:
            suggestions.append({
                'type': 'date_based',
                'title': 'Link by Recording Date',
                'description': f"Find activities from {creation_date[:10]}",
                'confidence': 'high',
                'search_criteria': {
                    'date': creation_date[:10],
                    'type': 'date_range'
                },
                'rationale': 'Voice memo was recorded on this date, likely related to activities from the same day'
            })
        
        # Content-based linking
        full_text = transcription_data.get('full_text', '')
        if full_text:
            # Extract potential keywords
            keywords = self._extract_keywords(full_text)
            if keywords:
                suggestions.append({
                    'type': 'content_based',
                    'title': 'Link by Content Keywords',
                    'description': f"Search for activities containing: {', '.join(keywords[:5])}",
                    'confidence': 'medium',
                    'search_criteria': {
                        'keywords': keywords[:10],  # Top 10 keywords
                        'type': 'keyword_search'
                    },
                    'rationale': 'Voice memo content may reference specific activities, projects, or people'
                })
        
        # Duration-based linking
        duration = metadata.get('duration_seconds')
        if duration:
            try:
                duration_float = float(duration)
                suggestions.append({
                    'type': 'duration_based',
                    'title': 'Link by Similar Duration',
                    'description': f"Find activities with similar duration (~{int(duration_float/60)} minutes)",
                    'confidence': 'low',
                    'search_criteria': {
                        'duration_min': duration_float - 300,  # ±5 minutes
                        'duration_max': duration_float + 300,
                        'type': 'duration_range'
                    },
                    'rationale': 'Voice memo might be a recording of or notes about a meeting/activity of similar length'
                })
            except (ValueError, TypeError):
                pass
        
        # Location-based linking (if location keywords found)
        location_keywords = self._extract_location_keywords(full_text)
        if location_keywords:
            suggestions.append({
                'type': 'location_based',
                'title': 'Link by Location References',
                'description': f"Search for activities at: {', '.join(location_keywords)}",
                'confidence': 'medium',
                'search_criteria': {
                    'locations': location_keywords,
                    'type': 'location_search'
                },
                'rationale': 'Voice memo mentions specific locations that may match activity locations'
            })
        
        # Tag-based linking
        tags = self._extract_tags(metadata)
        if tags:
            suggestions.append({
                'type': 'tag_based',
                'title': 'Link by Tags',
                'description': f"Find activities tagged with: {', '.join(tags)}",
                'confidence': 'medium',
                'search_criteria': {
                    'tags': tags,
                    'type': 'tag_search'
                },
                'rationale': 'Audio file tags may correspond to activity categories or labels'
            })
        
        return suggestions
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from transcription text."""
        import re
        
        # Simple keyword extraction
        words = re.findall(r'\b[A-Za-z]{3,}\b', text.lower())
        
        # Filter out common words
        common_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 
            'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 
            'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use', 'that', 'with', 'have', 
            'this', 'will', 'your', 'from', 'they', 'know', 'want', 'been', 'good', 'much', 'some', 'time', 
            'very', 'when', 'come', 'here', 'just', 'like', 'long', 'make', 'many', 'over', 'such', 'take', 
            'than', 'them', 'well', 'were', 'what', 'yeah', 'okay', 'think', 'going', 'really', 'right', 
            'about', 'would', 'there', 'could', 'other', 'after', 'first', 'never', 'these', 'think', 'where', 
            'being', 'every', 'great', 'might', 'shall', 'still', 'those', 'under', 'while', 'should'
        }
        
        keywords = [word for word in words if word not in common_words and len(word) > 3]
        
        # Count frequency and return most common
        from collections import Counter
        word_counts = Counter(keywords)
        
        return [word for word, count in word_counts.most_common(20)]
    
    def _extract_location_keywords(self, text: str) -> List[str]:
        """Extract potential location references from text."""
        import re
        
        # Simple patterns for locations
        location_patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Two capitalized words (City State)
            r'\b[A-Z][a-z]+ (Street|Ave|Avenue|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)\b',  # Street addresses
            r'\b(Office|Building|Center|Centre|Hospital|School|University|College|Restaurant|Cafe|Store|Shop)\b',  # Places
        ]
        
        locations = []
        for pattern in location_patterns:
            matches = re.findall(pattern, text)
            locations.extend(matches)
        
        return list(set(locations))  # Remove duplicates


def main():
    """Demo function to test Notion integration."""
    
    # Mock data for testing
    mock_transcription = {
        'full_text': 'This is a test transcription of a voice memo about the meeting we had at the office yesterday.',
        'language': 'en',
        'model_used': 'base',
        'word_count': 17,
        'segments': [
            {'start': 0.0, 'end': 5.2, 'text': 'This is a test transcription'},
            {'start': 5.2, 'end': 10.1, 'text': 'of a voice memo about the meeting'},
            {'start': 10.1, 'end': 15.0, 'text': 'we had at the office yesterday.'}
        ]
    }
    
    mock_metadata = {
        'filename': 'Meeting Notes.m4a',
        'duration_seconds': '15.0',
        'creation_date': '2024-09-19T14:30:00Z',
        'file_size': '500000',
        'tags': 'Work, Meeting',
        'file_path': '/Users/test/Voice Memos/Meeting Notes.m4a'
    }
    
    # Test integration
    integrator = NotionIntegrator()
    
    print("Testing Notion integration...")
    
    # Test page creation
    result = integrator.create_content_page(mock_transcription, mock_metadata)
    print(f"Page creation result: {result['success']}")
    
    # Test activity linking analysis
    suggestions = integrator.analyze_for_activity_linking(mock_transcription, mock_metadata)
    print(f"\nFound {len(suggestions)} linking suggestions:")
    
    for i, suggestion in enumerate(suggestions, 1):
        print(f"\n{i}. {suggestion['title']} (Confidence: {suggestion['confidence']})")
        print(f"   Description: {suggestion['description']}")
        print(f"   Rationale: {suggestion['rationale']}")


if __name__ == "__main__":
    main()