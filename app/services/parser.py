import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class ParsedTrack:
    timestamp: str
    artist: str
    title: str
    remix_info: str = ""

    @classmethod
    def parse_tracklist_line(cls, line: str) -> Optional['ParsedTrack']:
        """Parse a single line from the tracklist

        Supports multiple formats:
        1. With [mm] timestamp: "[01] Artist - Title (Remix Info) [Label]"
        2. With HH:MM:SS timestamp: "00:01:23 Artist - Title (Remix Info)"
        3. Without timestamp: "Artist - Title (Remix Info)"
        4. Simple format: "Artist - Title"

        Returns:
            ParsedTrack object if line is valid, None if line should be skipped
        """
        line = line.strip()
        line = line.replace('\t', ' ')

        # Remove leading numerical list formats
        num_list_match = re.match(r'^(\d{1,3}(?:\.\d{1,3})?)\.?\s*', line)
        if num_list_match:
            line = line[num_list_match.end():].strip()

        # Skip empty lines, comments, or placeholders
        if not line or line == '...' or line == '?' or line.startswith('#') or line.startswith('//'):
            return None

        # Initialize variables
        timestamp = ""
        track_info = line

        # Check for [mm] format: "[01] Artist - Title"
        mm_timestamp_match = re.match(r'^\[(\d{1,3})\]\s*(.*)', line)
        if mm_timestamp_match:
            minutes = int(mm_timestamp_match.group(1))
            # Convert minutes to HH:MM:SS format
            hours = minutes // 60
            mins = minutes % 60
            timestamp = f"{hours:02d}:{mins:02d}:00"
            track_info = mm_timestamp_match.group(2).strip()

            if track_info == '?':
                return None
        # Check for HH:MM:SS or MM:SS format
        else:
            timestamp_match = re.match(r'^(\d{1,2}:\d{2}(?::\d{2})?)\s+', line)
            if timestamp_match:
                timestamp = timestamp_match.group(1)
                track_info = line[timestamp_match.end():].strip()

        # Extract label info if present
        label = ""
        label_match = re.search(r'\s*\[([^\]]+)\]\s*$', track_info)
        if label_match:
            label = label_match.group(1).strip()
            track_info = track_info[:label_match.start()].strip()

        # Extract remix info if present
        remix_info = ""
        remix_match = re.search(r'\s*\(([^)]+)\)\s*$', track_info)
        if remix_match:
            remix_info = remix_match.group(1).strip()
            track_info = track_info[:remix_match.start()].strip()

        # Combine label and remix info
        if label and remix_info:
            remix_info = f"{remix_info} [{label}]"
        elif label:
            remix_info = f"[{label}]"

        # Split artist and title
        dash_split = re.split(r'\s*[-–—]\s*', track_info, maxsplit=1)
        if len(dash_split) == 2:
            artist = dash_split[0].strip()
            title = dash_split[1].strip()
            if not artist and title:
                artist = title
                title = ""
        else:
            artist = track_info.strip()
            title = ""

        # Skip if both artist and title are empty
        if not artist and not title:
            return None

        return cls(
            timestamp=timestamp,
            artist=artist,
            title=title,
            remix_info=remix_info
        )


def parse_tracklist(tracklist_text: str) -> list[ParsedTrack]:
    """Parse a full tracklist text into Track objects"""
    tracks = []
    for line in tracklist_text.split('\n'):
        track = ParsedTrack.parse_tracklist_line(line)
        if track:
            tracks.append(track)
    return tracks
