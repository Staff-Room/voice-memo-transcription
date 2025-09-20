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
from notion_client import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class NotionIntegrator:
    """Handles Notion database operations via MCP tools."""
    
    def __init__(self):
        """Initialize the Notion integrator."""
        self.notion_token = os.getenv('NOTION_TOKEN')
        self.content_database_id = os.getenv('NOTION_DATABASE_ID')
        self.activities_database_id = None
        self.database_schema = None
        
        if self.notion_token:
            self.notion = Client(auth=self.notion_token)
            # Fetch database schema on initialization
            if self.content_database_id:
                self.database_schema = self._fetch_database_schema()
        else:
            self.notion = None
    
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
            print("Creating Notion content page...")
            
            # Prepare voice memo data for analysis
            voice_memo_data = {
                'title': self._generate_page_title(transcription_data, metadata),
                'transcription': transcription_data.get('full_text', ''),
                'creation_date': metadata.get('creation_date'),
                'duration_seconds': metadata.get('duration_seconds'),
                'word_count': transcription_data.get('word_count', 0),
                'tags': self._extract_tags(metadata),
                'filename': metadata.get('filename', ''),
                'model_used': transcription_data.get('model_used', '')
            }
            
            print(f"Title: {voice_memo_data['title']}")
            
            # Analyze schema and get smart mapping
            if self.database_schema:
                print("🧠 Using smart schema-based mapping")
                mapping = self._analyze_schema_with_llm(voice_memo_data)
                page_result = self._create_page_with_mapping(voice_memo_data, mapping, transcription_data, metadata)
            else:
                print("📝 Using fallback page creation")
                # Fallback to original method
                page_data = self._prepare_content_page_data(transcription_data, metadata)
                page_result = self._create_notion_page_with_mcp(page_data)
            
            if page_result['success']:
                return {
                    'success': True,
                    'page_id': page_result['page_id'],
                    'page_url': page_result.get('page_url'),
                    'page_data': voice_memo_data,
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'page_id': None,
                    'page_url': None,
                    'page_data': voice_memo_data,
                    'error': page_result.get('error', 'Unknown error creating page')
                }
            
        except Exception as e:
            return {
                'success': False,
                'page_id': None,
                'page_url': None,
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
    
    def test_database_connection(self) -> Dict:
        """Test if we can connect to and read the database."""
        try:
            if not self.notion:
                return {'success': False, 'error': 'No Notion client initialized (missing token?)'}
            
            if not self.content_database_id:
                return {'success': False, 'error': 'No database ID provided'}
            
            print(f"🧪 Testing connection to database: {self.content_database_id}")
            
            # Try to fetch database info
            database = self.notion.databases.retrieve(database_id=self.content_database_id)
            
            title = database.get('title', [{}])[0].get('text', {}).get('content', 'Unknown')
            properties = database.get('properties', {})
            
            print(f"✅ Successfully connected to database: '{title}'")
            print(f"📊 Database has {len(properties)} properties:")
            
            for prop_name, prop_data in properties.items():
                prop_type = prop_data.get('type', 'unknown')
                print(f"   🔹 {prop_name}: {prop_type}")
            
            # Try to query some pages (limit to 5)
            pages_response = self.notion.databases.query(
                database_id=self.content_database_id,
                page_size=5
            )
            
            pages = pages_response.get('results', [])
            print(f"📄 Found {len(pages)} existing pages in database")
            
            return {
                'success': True,
                'database_title': title,
                'properties': properties,
                'existing_pages': len(pages),
                'error': None
            }
            
        except Exception as e:
            print(f"❌ Database connection test failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_most_recent_page(self) -> Optional[Dict]:
        """Get the most recently created page from the database."""
        try:
            if not self.notion or not self.content_database_id:
                return None
            
            # Query pages sorted by created time (most recent first)
            pages_response = self.notion.databases.query(
                database_id=self.content_database_id,
                sorts=[{
                    "property": "Created time",
                    "direction": "descending"
                }],
                page_size=1
            )
            
            pages = pages_response.get('results', [])
            if not pages:
                return None
            
            page = pages[0]
            
            # Extract page info
            page_info = {
                'id': page['id'],
                'url': page['url'],
                'created_time': page['created_time'],
                'title': 'Untitled'
            }
            
            # Get title from properties
            properties = page.get('properties', {})
            for prop_name, prop_data in properties.items():
                if prop_data.get('type') == 'title':
                    title_content = prop_data.get('title', [])
                    if title_content:
                        page_info['title'] = title_content[0].get('text', {}).get('content', 'Untitled')
                    break
            
            return page_info
            
        except Exception as e:
            print(f"⚠️  Could not get most recent page: {e}")
            return None
    
    def _fetch_database_schema(self) -> Optional[Dict]:
        """Fetch the database schema to understand its structure."""
        try:
            if not self.notion or not self.content_database_id:
                return None
            
            database = self.notion.databases.retrieve(database_id=self.content_database_id)
            
            # Extract useful schema information
            schema = {
                'title': database.get('title', [{}])[0].get('text', {}).get('content', 'Unknown'),
                'properties': {},
                'raw_schema': database
            }
            
            # Parse properties
            for prop_name, prop_data in database.get('properties', {}).items():
                prop_type = prop_data.get('type')
                schema['properties'][prop_name] = {
                    'type': prop_type,
                    'config': prop_data.get(prop_type, {})
                }
            
            print(f"📊 Fetched schema for database: {schema['title']}")
            print(f"🏗️  Found {len(schema['properties'])} properties")
            
            # Debug: Show all properties
            for prop_name, prop_info in schema['properties'].items():
                print(f"   🔹 {prop_name}: {prop_info['type']}")
            
            return schema
            
        except Exception as e:
            print(f"⚠️  Could not fetch database schema: {e}")
            return None
    
    def _analyze_schema_with_llm(self, voice_memo_data: Dict) -> Dict:
        """Analyze database schema and determine best population strategy."""
        if not self.database_schema:
            return {'error': 'No database schema available'}
        
        # Prepare data for LLM analysis
        schema_summary = {
            'database_title': self.database_schema['title'],
            'properties': {}
        }
        
        for prop_name, prop_info in self.database_schema['properties'].items():
            schema_summary['properties'][prop_name] = prop_info['type']
        
        # This would call an LLM to analyze the schema and voice memo data
        # For now, implement basic mapping logic
        return self._smart_field_mapping(voice_memo_data, schema_summary)
    
    def _smart_field_mapping(self, voice_memo_data: Dict, schema: Dict) -> Dict:
        """Smart mapping of voice memo data to database fields."""
        mapping = {
            'properties': {},
            'strategy': 'auto_mapped'
        }
        
        # Auto-detect common field patterns
        for prop_name, prop_type in schema['properties'].items():
            prop_lower = prop_name.lower()
            
            # Title field - exact match for "Asset Name"
            if prop_type == 'title':
                mapping['properties'][prop_name] = {
                    'value': voice_memo_data.get('title', 'Voice Memo'),
                    'type': 'title'
                }
            
            # Rich text fields - match "AI Summary" specifically
            elif prop_type == 'rich_text':
                if 'summary' in prop_lower or 'ai summary' in prop_lower:
                    # Use transcription for AI Summary field
                    mapping['properties'][prop_name] = {
                        'value': voice_memo_data.get('transcription', ''),
                        'type': 'rich_text'
                    }
                elif 'transcript' in prop_lower or 'content' in prop_lower:
                    mapping['properties'][prop_name] = {
                        'value': voice_memo_data.get('transcription', ''),
                        'type': 'rich_text'
                    }
                elif 'description' in prop_lower:
                    mapping['properties'][prop_name] = {
                        'value': voice_memo_data.get('summary', voice_memo_data.get('title', '')),
                        'type': 'rich_text'
                    }
            
            # Date fields
            elif prop_type == 'date':
                if 'created' in prop_lower or 'recorded' in prop_lower:
                    mapping['properties'][prop_name] = {
                        'value': voice_memo_data.get('creation_date'),
                        'type': 'date'
                    }
            
            # Number fields
            elif prop_type == 'number':
                if 'duration' in prop_lower:
                    mapping['properties'][prop_name] = {
                        'value': voice_memo_data.get('duration_seconds'),
                        'type': 'number'
                    }
                elif 'word' in prop_lower:
                    mapping['properties'][prop_name] = {
                        'value': voice_memo_data.get('word_count'),
                        'type': 'number'
                    }
            
            # Status fields
            elif prop_type == 'status':
                if 'status' in prop_lower:
                    mapping['properties'][prop_name] = {
                        'value': 'Not started',  # Default status
                        'type': 'status'
                    }
            
            # Select fields
            elif prop_type == 'select':
                if 'type' in prop_lower or 'category' in prop_lower:
                    mapping['properties'][prop_name] = {
                        'value': 'Voice Memo',
                        'type': 'select'
                    }
                elif 'source' in prop_lower:
                    mapping['properties'][prop_name] = {
                        'value': 'Audio Transcription',
                        'type': 'select'
                    }
            
            # Multi-select fields (tags)
            elif prop_type == 'multi_select':
                if 'tag' in prop_lower or 'label' in prop_lower:
                    mapping['properties'][prop_name] = {
                        'value': voice_memo_data.get('tags', ['Voice Memo', 'Transcription']),
                        'type': 'multi_select'
                    }
            
            # URL fields
            elif prop_type == 'url':
                if 'url' in prop_lower or 'link' in prop_lower:
                    # Don't populate URL for now
                    pass
        
        return mapping
    
    def _create_page_with_mapping(self, voice_memo_data: Dict, mapping: Dict, transcription_data: Dict, metadata: Dict) -> Dict:
        """Create a Notion page using the smart mapping."""
        try:
            # Build Notion properties from mapping
            properties = {}
            
            for prop_name, prop_info in mapping['properties'].items():
                prop_type = prop_info['type']
                value = prop_info['value']
                
                if not value:  # Skip empty values
                    continue
                
                if prop_type == 'title':
                    properties[prop_name] = {
                        "title": [{"type": "text", "text": {"content": str(value)}}]
                    }
                elif prop_type == 'rich_text':
                    properties[prop_name] = {
                        "rich_text": [{"type": "text", "text": {"content": str(value)}}]
                    }
                elif prop_type == 'date' and value:
                    # Format date for Notion
                    if isinstance(value, str) and value:
                        try:
                            # Convert to ISO format if needed
                            properties[prop_name] = {
                                "date": {"start": value[:10]}  # Just the date part
                            }
                        except:
                            pass
                elif prop_type == 'number' and value:
                    try:
                        properties[prop_name] = {
                            "number": float(value)
                        }
                    except (ValueError, TypeError):
                        pass
                elif prop_type == 'select' and value:
                    properties[prop_name] = {
                        "select": {"name": str(value)}
                    }
                elif prop_type == 'multi_select' and value:
                    if isinstance(value, list):
                        properties[prop_name] = {
                            "multi_select": [{"name": str(tag)} for tag in value[:5]]  # Limit to 5
                        }
                elif prop_type == 'status' and value:
                    properties[prop_name] = {
                        "status": {"name": str(value)}
                    }
            
            # Create content blocks (for page body)
            children = self._create_content_blocks(transcription_data, metadata)
            notion_children = []
            
            for block in children:
                if block['type'] == 'heading_2':
                    notion_children.append({
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": block['content']}}]
                        }
                    })
                elif block['type'] == 'heading_3':
                    notion_children.append({
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [{"type": "text", "text": {"content": block['content']}}]
                        }
                    })
                elif block['type'] == 'paragraph':
                    notion_children.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": block['content']}}]
                        }
                    })
            
            # Create the page
            payload = {
                "parent": {"database_id": self.content_database_id},
                "properties": properties,
                "children": notion_children
            }
            
            print(f"🔧 Creating page with payload: {json.dumps(payload, indent=2)}")
            result = self.notion.pages.create(**payload)
            
            print(f"✅ Page created successfully!")
            print(f"📄 Page ID: {result['id']}")
            print(f"🔗 Page URL: {result['url']}")
            print(f"📊 Database ID used: {self.content_database_id}")
            
            return {
                'success': True,
                'page_id': result['id'],
                'page_url': result['url'],
                'error': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'page_id': None,
                'page_url': None,
                'error': str(e)
            }
    
    def _create_notion_page_with_mcp(self, page_data: Dict) -> Dict:
        """
        Create a Notion page using the Notion SDK.
        
        Args:
            page_data: Prepared page data structure
            
        Returns:
            Result with page_id and page_url if successful
        """
        try:
            if not self.notion:
                return {
                    'success': False,
                    'page_id': None,
                    'page_url': None,
                    'error': 'NOTION_TOKEN environment variable not set'
                }
            
            if not self.content_database_id:
                return {
                    'success': False,
                    'page_id': None,
                    'page_url': None,
                    'error': 'NOTION_DATABASE_ID environment variable not set'
                }
            
            # Create the page using Notion SDK
            payload = self._build_notion_page_payload(page_data)
            
            result = self.notion.pages.create(**payload)
            
            page_id = result['id']
            page_url = result['url']
            
            return {
                'success': True,
                'page_id': page_id,
                'page_url': page_url,
                'error': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'page_id': None,
                'page_url': None,
                'error': str(e)
            }
    
    def _build_notion_page_payload(self, page_data: Dict) -> Dict:
        """Build the Notion API payload for page creation."""
        
        # Build content blocks for Notion
        children = []
        
        for block in page_data['content']:
            if block['type'] == 'heading_2':
                children.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": block['content']}}]
                    }
                })
            elif block['type'] == 'heading_3':
                children.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": block['content']}}]
                    }
                })
            elif block['type'] == 'paragraph':
                children.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": block['content']}}]
                    }
                })
        
        # Build page properties
        properties = {
            "Name": {
                "title": [{"type": "text", "text": {"content": page_data['title']}}]
            }
        }
        
        # Add other properties if the database supports them
        props = page_data.get('properties', {})
        if props.get('Type'):
            properties["Type"] = {"rich_text": [{"type": "text", "text": {"content": props['Type']}}]}
        if props.get('Source'):
            properties["Source"] = {"rich_text": [{"type": "text", "text": {"content": props['Source']}}]}
        if props.get('Duration'):
            properties["Duration"] = {"rich_text": [{"type": "text", "text": {"content": str(props['Duration'])}}]}
        if props.get('Tags') and isinstance(props['Tags'], list):
            properties["Tags"] = {"multi_select": [{"name": tag} for tag in props['Tags'][:5]]}  # Limit to 5 tags
        
        return {
            "parent": {"database_id": self.content_database_id},
            "properties": properties,
            "children": children
        }


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