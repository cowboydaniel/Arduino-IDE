"""
Snippets manager for loading and managing code snippets
"""

import json
from pathlib import Path
from typing import Dict, List, Optional


class Snippet:
    """Represents a code snippet"""

    def __init__(self, name: str, prefix: str, description: str, body: List[str], category: str = "General"):
        self.name = name
        self.prefix = prefix
        self.description = description
        self.body = body
        self.category = category

    def get_body_text(self) -> str:
        """Get the snippet body as a single string"""
        return '\n'.join(self.body)

    def insert_text(self, cursor_placeholder: str = "$0") -> tuple[str, int]:
        """
        Get the text to insert and cursor position offset

        Returns:
            (text_to_insert, cursor_offset_from_end)
        """
        text = self.get_body_text()

        # Find cursor placeholder position
        if cursor_placeholder in text:
            cursor_pos = text.index(cursor_placeholder)
            # Remove placeholder
            text = text.replace(cursor_placeholder, "")
            # Calculate offset from end
            offset = len(text) - cursor_pos
            return (text, offset)

        return (text, 0)


class SnippetsManager:
    """Manages code snippets for the IDE"""

    def __init__(self):
        self.snippets: Dict[str, List[Snippet]] = {}
        self.load_snippets()

    def load_snippets(self):
        """Load snippets from JSON file"""
        snippets_file = Path(__file__).parent.parent / "resources" / "snippets" / "arduino_snippets.json"

        if not snippets_file.exists():
            print(f"Snippets file not found: {snippets_file}")
            return

        try:
            with open(snippets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for category, snippets_list in data.items():
                self.snippets[category] = []
                for snippet_data in snippets_list:
                    snippet = Snippet(
                        name=snippet_data['name'],
                        prefix=snippet_data.get('prefix', ''),
                        description=snippet_data.get('description', ''),
                        body=snippet_data.get('body', []),
                        category=category
                    )
                    self.snippets[category].append(snippet)

        except Exception as e:
            print(f"Error loading snippets: {e}")

    def get_all_snippets(self) -> List[Snippet]:
        """Get all snippets as a flat list"""
        all_snippets = []
        for category_snippets in self.snippets.values():
            all_snippets.extend(category_snippets)
        return all_snippets

    def get_snippets_by_category(self, category: str) -> List[Snippet]:
        """Get snippets for a specific category"""
        return self.snippets.get(category, [])

    def get_categories(self) -> List[str]:
        """Get list of all categories"""
        return list(self.snippets.keys())

    def search_snippets(self, query: str) -> List[Snippet]:
        """Search snippets by name, prefix, or description"""
        query = query.lower()
        results = []

        for snippet in self.get_all_snippets():
            if (query in snippet.name.lower() or
                query in snippet.prefix.lower() or
                query in snippet.description.lower()):
                results.append(snippet)

        return results

    def get_snippet_by_prefix(self, prefix: str) -> Optional[Snippet]:
        """Get a snippet by its prefix"""
        for snippet in self.get_all_snippets():
            if snippet.prefix == prefix:
                return snippet
        return None

    def get_completion_items(self) -> List[dict]:
        """
        Get snippets formatted for code completion

        Returns:
            List of dicts with 'text', 'description', 'snippet', 'type'
        """
        items = []
        for snippet in self.get_all_snippets():
            items.append({
                'text': snippet.prefix,
                'description': snippet.name,
                'snippet': snippet,
                'type': 'snippet',
                'category': snippet.category
            })
        return items
